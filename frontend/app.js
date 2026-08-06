document.addEventListener("DOMContentLoaded", () => {

  // ============================================================
  // CONFIG
  // ============================================================

  const API_BASE_URL = "http://127.0.0.1:8000";

  // ============================================================
  // ELEMENTS
  // ============================================================

  const fileInput = document.getElementById("pdf-input");
  const uploadStatus = document.getElementById("upload-status");

  const questionEl = document.getElementById("question");
  const askBtn = document.getElementById("ask-btn");
  const statusEl = document.getElementById("status");

  const answerEl = document.getElementById("answer");
  const answerTextEl = document.getElementById("answer-text");

  const qtypePill = document.getElementById("qtype-pill");
  const toolPill = document.getElementById("tool-pill");

  const sourcesEl = document.getElementById("sources");
  const sourcesListEl = document.getElementById("sources-list");

  const copyBtn = document.getElementById("copy-btn");

  const thumbUp = document.getElementById("thumb-up");
  const thumbDown = document.getElementById("thumb-down");


  // ============================================================
  // STATE
  // ============================================================

  let currentDocumentId = null;


  // ============================================================
  // HELPERS
  // ============================================================

  function setStatus(message, type = "") {

    statusEl.textContent = message;

    statusEl.className = "";

    if (type) {
      statusEl.classList.add(`status-${type}`);
    }
  }


  function setUploadStatus(message, type = "") {

    uploadStatus.textContent = message;

    uploadStatus.className = "";

    if (type) {
      uploadStatus.classList.add(`status-${type}`);
    }
  }


  function resetAnswer() {

    answerEl.hidden = true;

    qtypePill.hidden = true;
    toolPill.hidden = true;

    sourcesEl.hidden = true;

    answerTextEl.textContent = "";

    sourcesListEl.replaceChildren();
  }


  function inferQuestionType(question) {

    const q = question.toLowerCase();

    if (
      q.startsWith("what is") ||
      q.startsWith("define") ||
      q.includes("meaning of")
    ) {
      return "definition";
    }

    if (
      q.includes("difference") ||
      q.includes("compare") ||
      q.includes("versus") ||
      q.includes(" vs ")
    ) {
      return "comparison";
    }

    if (
      q.includes("example") ||
      q.startsWith("give")
    ) {
      return "example";
    }

    return "question";
  }


  function displaySources(sources) {

    sourcesListEl.replaceChildren();

    if (!sources || sources.length === 0) {
      sourcesEl.hidden = true;
      return;
    }

    sources.forEach((source) => {

      const li = document.createElement("li");

      const documentName =
        source.document_name || "Uploaded PDF";

      const chunk =
        source.chunk_index !== undefined
          ? `Chunk ${source.chunk_index + 1}`
          : "";

      li.textContent =
        `${documentName} — ${chunk}\n${source.excerpt || ""}`;

      sourcesListEl.appendChild(li);
    });

    sourcesEl.hidden = false;
  }


  // ============================================================
  // PDF UPLOAD
  // ============================================================

  fileInput.addEventListener("change", async () => {

    const file = fileInput.files[0];

    if (!file) {
      return;
    }

    if (file.type !== "application/pdf") {

      setUploadStatus(
        "Please select a PDF file.",
        "error"
      );

      return;
    }

    setUploadStatus(
      `Uploading "${file.name}"...`,
      "loading"
    );

    const formData = new FormData();

    formData.append("file", file);

    try {

      const response = await fetch(
        `${API_BASE_URL}/upload`,
        {
          method: "POST",
          body: formData
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "PDF upload failed."
        );
      }

      currentDocumentId = data.document_id;

      setUploadStatus(
        `✓ ${data.document_name} processed successfully — ${data.pages} pages, ${data.chunks} chunks.`,
        "success"
      );

      resetAnswer();

      setStatus("");

    } catch (error) {

      console.error(error);

      currentDocumentId = null;

      setUploadStatus(
        `Upload failed: ${error.message}`,
        "error"
      );
    }
  });


  // ============================================================
  // ASK QUESTION
  // ============================================================

  askBtn.addEventListener("click", async () => {

    const question = questionEl.value.trim();

    if (!question) {

      setStatus(
        "Please type a question first.",
        "error"
      );

      return;
    }

    if (!currentDocumentId) {

      setStatus(
        "Please upload a PDF first.",
        "warning"
      );

      return;
    }

    askBtn.disabled = true;

    resetAnswer();

    setStatus(
      "Searching your notes and generating an answer...",
      "loading"
    );

    try {

      const response = await fetch(
        `${API_BASE_URL}/ask`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json"
          },

          body: JSON.stringify({
            question: question,
            document_id: currentDocumentId
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to generate answer."
        );
      }

      // ------------------------------
      // Answer
      // ------------------------------

      answerTextEl.textContent =
        data.answer || "No answer was generated.";

      // ------------------------------
      // Question type
      // ------------------------------

      qtypePill.textContent =
        `type: ${inferQuestionType(question)}`;

      qtypePill.hidden = false;

      // ------------------------------
      // Tool
      // ------------------------------

      toolPill.textContent =
        `tool: RAG + ${data.model || "Groq"}`;

      toolPill.hidden = false;

      // ------------------------------
      // Sources
      // ------------------------------

      displaySources(data.source_chunks);

      // ------------------------------
      // Reveal answer
      // ------------------------------

      answerEl.hidden = false;

      setStatus(
        "Answer generated successfully.",
        "success"
      );

    } catch (error) {

      console.error(error);

      setStatus(
        `Error: ${error.message}`,
        "error"
      );

    } finally {

      askBtn.disabled = false;
    }
  });


  // ============================================================
  // COPY ANSWER
  // ============================================================

  copyBtn.addEventListener("click", async () => {

    const answer = answerTextEl.textContent.trim();

    if (!answer) {
      return;
    }

    try {

      await navigator.clipboard.writeText(answer);

      const originalText = copyBtn.textContent;

      copyBtn.textContent = "✓ Copied";

      setTimeout(() => {
        copyBtn.textContent = originalText;
      }, 1500);

    } catch (error) {

      console.error(error);

      setStatus(
        "Could not copy the answer.",
        "error"
      );
    }
  });


  // ============================================================
  // FEEDBACK
  // ============================================================

  thumbUp.addEventListener("click", () => {

    thumbUp.style.transform = "scale(1.15)";

    setTimeout(() => {
      thumbUp.style.transform = "";
    }, 200);
  });


  thumbDown.addEventListener("click", () => {

    thumbDown.style.transform = "scale(1.15)";

    setTimeout(() => {
      thumbDown.style.transform = "";
    }, 200);
  });

});