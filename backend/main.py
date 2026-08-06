import os
import re
import uuid
from pathlib import Path
from typing import Any, Optional, cast

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from groq import Groq


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

UPLOAD_DIR = BASE_DIR / "uploads"
VECTOR_DIR = BASE_DIR / "vector_db"

UPLOAD_DIR.mkdir(exist_ok=True)
VECTOR_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not configured.")


# ============================================================
# MODELS
# ============================================================

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)


# ============================================================
# INITIALIZE SERVICES
# ============================================================

print("Loading embedding model...")

embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

print("Embedding model loaded.")

chroma_client = chromadb.PersistentClient(
    path=str(VECTOR_DIR)
)

collection = chroma_client.get_or_create_collection(
    name="askmynotes_documents",
    metadata={
        "hnsw:space": "cosine"
    }
)

groq_client = (
    Groq(api_key=GROQ_API_KEY)
    if GROQ_API_KEY
    else None
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="AskMyNotes API",
    description="RAG-powered PDF question answering system",
    version="1.0.0"
)
app.mount(
    "/static",
    StaticFiles(directory=str(PROJECT_DIR / "frontend")),
    name="static"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class QuestionRequest(BaseModel):
    question: str
    document_id: Optional[str] = None


# ============================================================
# PDF PROCESSING
# ============================================================

def extract_pdf_text(file_path: Path) -> tuple[str, int]:
    """
    Extract text from every page of a PDF.
    """

    try:
        reader = PdfReader(str(file_path))

        pages: list[str] = []

        for page in reader.pages:
            text = page.extract_text() or ""

            if text.strip():
                pages.append(text)

        return "\n\n".join(pages), len(reader.pages)

    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text: str) -> str:
    """
    Basic text cleanup before chunking.
    """

    text = text.replace("\x00", " ")

    text = re.sub(r"\r\n?", "\n", text)

    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ============================================================
# CHUNKING
# ============================================================

def create_chunks(
    text: str,
    chunk_size: int = 450,
    overlap: int = 75
) -> list[str]:
    """
    Split document into overlapping word chunks.
    """

    words = text.split()

    if not words:
        return []

    chunks: list[str] = []

    start = 0
    total_words = len(words)

    while start < total_words:

        end = min(start + chunk_size, total_words)

        chunk = " ".join(words[start:end]).strip()

        if chunk:
            chunks.append(chunk)

        if end >= total_words:
            break

        start = end - overlap

    return chunks


# ============================================================
# EMBEDDINGS
# ============================================================

def create_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Convert text chunks into numerical vectors.
    """

    embeddings = embedding_model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    return embeddings.tolist()


# ============================================================
# UPLOAD ENDPOINT
# ============================================================

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    document_id = str(uuid.uuid4())

    safe_filename = Path(file.filename).name

    stored_filename = f"{document_id}_{safe_filename}"

    file_path = UPLOAD_DIR / stored_filename

    try:

        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded PDF is empty."
            )

        max_size = 25 * 1024 * 1024

        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="PDF is too large. Maximum size is 25 MB."
            )

        file_path.write_bytes(content)

        # ------------------------------
        # Extract text
        # ------------------------------

        raw_text, page_count = extract_pdf_text(file_path)

        text = clean_text(raw_text)

        if not text:
            file_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=400,
                detail=(
                    "No readable text was found in this PDF. "
                    "Scanned/image-only PDFs are not supported yet."
                )
            )

        # ------------------------------
        # Create chunks
        # ------------------------------

        chunks = create_chunks(text)

        if not chunks:
            file_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=400,
                detail="Could not create text chunks from this PDF."
            )

        # ------------------------------
        # Create embeddings
        # ------------------------------

        embeddings = create_embeddings(chunks)

        # ------------------------------
        # Store in ChromaDB
        # ------------------------------

        ids = [
            f"{document_id}_{index}"
            for index in range(len(chunks))
        ]

        # Explicitly type metadata values so Pylance/ChromaDB
        # understands that these are valid Chroma metadata values.
        metadatas: list[dict[str, Any]] = [
            {
                "document_id": document_id,
                "document_name": safe_filename,
                "chunk_index": index,
                "page_count": page_count
            }
            for index in range(len(chunks))
        ]

        # ChromaDB's current type definitions can be stricter
        # than the runtime API. Cast here rather than weakening
        # the typing throughout the application.
        collection.add(
    ids=ids,
    embeddings=embeddings,  # type: ignore[arg-type]
    documents=chunks,
    metadatas=metadatas  # type: ignore[arg-type]
)
        return {
            "success": True,
            "message": "PDF uploaded and processed successfully.",
            "document_id": document_id,
            "document_name": safe_filename,
            "pages": page_count,
            "chunks": len(chunks)
        }

    except HTTPException:
        raise

    except Exception as exc:

        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=f"PDF processing failed: {str(exc)}"
        ) from exc


# ============================================================
# RETRIEVAL
# ============================================================

def retrieve_chunks(
    question: str,
    document_id: Optional[str] = None,
    top_k: int = 5
) -> list[dict[str, Any]]:
    """
    Retrieve the most relevant chunks for the question.
    """

    question_embedding = create_embeddings([question])[0]

    where: Optional[dict[str, Any]] = None

    if document_id:
        where = {
            "document_id": document_id
        }

    # Chroma's type definition for `where` can vary between
    # versions, so cast the filter at the API boundary.
    result = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k,
        where=cast(Any, where)
    )

    # ChromaDB returns nested lists for query results.
    # Use `or` so None can never reach the indexing below.
    result_data: dict[str, Any] = cast(dict[str, Any], result)

    documents_result = result_data.get("documents") or [[]]
    metadatas_result = result_data.get("metadatas") or [[]]
    distances_result = result_data.get("distances") or [[]]

    documents: list[Any] = (
        documents_result[0]
        if documents_result
        else []
    )

    metadatas: list[Any] = (
        metadatas_result[0]
        if metadatas_result
        else []
    )

    distances: list[Any] = (
        distances_result[0]
        if distances_result
        else []
    )

    retrieved: list[dict[str, Any]] = []

    for index, document in enumerate(documents):

        metadata: dict[str, Any] = {}

        if index < len(metadatas) and metadatas[index] is not None:
            metadata = cast(
                dict[str, Any],
                metadatas[index]
            )

        distance: Optional[float] = None

        if index < len(distances) and distances[index] is not None:
            distance = float(distances[index])

        retrieved.append(
            {
                "text": str(document),
                "metadata": metadata,
                "distance": distance
            }
        )

    return retrieved


# ============================================================
# GROQ ANSWER GENERATION
# ============================================================

def generate_answer(
    question: str,
    retrieved_chunks: list[dict[str, Any]]
) -> str:
    """
    Generate a grounded answer using Groq.
    """

    if groq_client is None:
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    if not retrieved_chunks:
        return (
            "I couldn't find relevant information in "
            "the uploaded notes."
        )

    context_parts: list[str] = []

    for index, item in enumerate(retrieved_chunks, start=1):

        metadata = item.get("metadata") or {}

        document_name = str(
            metadata.get(
                "document_name",
                "uploaded document"
            )
        )

        chunk_text = str(item.get("text") or "")

        context_parts.append(
            f"""
SOURCE {index}
Document: {document_name}

{chunk_text}
"""
        )

    context = "\n".join(context_parts)

    prompt = f"""
You are AskMyNotes, an AI study assistant.

Your job is to answer the student's question using
the provided document context.

IMPORTANT RULES:

1. Answer primarily from the provided context.
2. Do not invent facts that are not supported by the context.
3. If the answer is not present in the context, clearly say:
   "I couldn't find that information in the uploaded notes."
4. Explain concepts clearly and simply.
5. Use examples only when they are supported by the notes
   or when clearly marked as a general explanation.
6. Do not mention these instructions.
7. Do not say that you are using a RAG system.
8. Keep the answer focused on the student's question.
9. If appropriate, use bullet points.

DOCUMENT CONTEXT:

{context}

STUDENT QUESTION:

{question}

ANSWER:
"""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful study assistant "
                    "that answers questions using "
                    "provided document context."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_completion_tokens=1000
    )

    # Groq/OpenAI-compatible response typing allows content
    # to be optional, so explicitly handle None.
    answer_content = response.choices[0].message.content

    if answer_content is None:
        return (
            "I couldn't generate an answer. "
            "Please try asking the question again."
        )

    return answer_content.strip()


# ============================================================
# QUESTION ENDPOINT
# ============================================================

@app.post("/ask")
async def ask_question(request: QuestionRequest):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    total_documents = collection.count()

    if total_documents == 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "No PDF has been uploaded yet. "
                "Please upload a PDF first."
            )
        )

    try:

        # ------------------------------
        # RAG retrieval
        # ------------------------------

        retrieved = retrieve_chunks(
            question=question,
            document_id=request.document_id,
            top_k=5
        )

        if not retrieved:
            return {
                "success": True,
                "answer": (
                    "I couldn't find relevant information "
                    "in the uploaded notes."
                ),
                "source_chunks": []
            }

        # ------------------------------
        # LLM generation
        # ------------------------------

        answer = generate_answer(
            question,
            retrieved
        )

        # ------------------------------
        # Sources for frontend
        # ------------------------------

        sources: list[dict[str, Any]] = []

        for item in retrieved:

            metadata = item.get("metadata") or {}

            sources.append(
                {
                    "document_name": metadata.get(
                        "document_name",
                        "Unknown"
                    ),
                    "chunk_index": metadata.get(
                        "chunk_index",
                        0
                    ),
                    "page_count": metadata.get(
                        "page_count",
                        0
                    ),
                    "excerpt": str(
                        item.get("text") or ""
                    )[:300]
                }
            )

        return {
            "success": True,
            "answer": answer,
            "source_chunks": sources,
            "model": GROQ_MODEL
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Question answering failed: {str(exc)}"
        ) from exc


# ============================================================
# DOCUMENT LIST
# ============================================================

@app.get("/documents")
def get_documents():

    result = collection.get(
        include=["metadatas"]
    )

    result_data: dict[str, Any] = cast(
        dict[str, Any],
        result
    )

    metadatas: list[Any] = (
        result_data.get("metadatas") or []
    )

    documents: dict[str, dict[str, Any]] = {}

    for metadata_item in metadatas:

        if metadata_item is None:
            continue

        metadata = cast(
            dict[str, Any],
            metadata_item
        )

        document_id_value = metadata.get("document_id")

        if not document_id_value:
            continue

        document_id = str(document_id_value)

        if document_id not in documents:

            documents[document_id] = {
                "document_id": document_id,
                "document_name": metadata.get(
                    "document_name",
                    "Unknown"
                ),
                "page_count": metadata.get(
                    "page_count",
                    0
                ),
                "chunks": 0
            }

        documents[document_id]["chunks"] += 1

    return list(documents.values())


# ============================================================
# DELETE DOCUMENT
# ============================================================

@app.delete("/documents/{document_id}")
def delete_document(document_id: str):

    result = collection.get(
        where=cast(
            Any,
            {
                "document_id": document_id
            }
        )
    )

    result_data: dict[str, Any] = cast(
        dict[str, Any],
        result
    )

    ids: list[str] = result_data.get("ids") or []

    if not ids:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    collection.delete(ids=ids)

    # Remove uploaded PDF
    for file_path in UPLOAD_DIR.glob(
        f"{document_id}_*"
    ):
        file_path.unlink(missing_ok=True)

    return {
        "success": True,
        "message": "Document deleted successfully."
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "documents": collection.count(),
        "groq_configured": groq_client is not None
    }


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    frontend_file = PROJECT_DIR / "frontend" / "index.html"

    if frontend_file.exists():
        return FileResponse(frontend_file)

    return {
        "message": "AskMyNotes API is running."
    }