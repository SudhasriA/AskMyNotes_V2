from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Feedback(BaseModel):
    student_name: str
    topic: str
    rating: int
    comment: str

feedback_store = []

@app.post("/feedback")
def submit_feedback(feedback: Feedback):
    feedback_store.append(feedback)
    return {
        "message": f"Thank you, {feedback.student_name}! Your feedback on '{feedback.topic}' has been received.",
        "rating": feedback.rating,
        "comment": feedback.comment
    }

@app.get("/feedback")
def get_feedback():
    return feedback_store
