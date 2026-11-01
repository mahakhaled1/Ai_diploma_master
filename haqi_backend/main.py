from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Haqi Egypt Service Guide - Backend API",
    version="1.0.0"
)

class ChatRequest(BaseModel):
    question: str
    user_id: str = "guest_user"

@app.get("/")
def read_root():
    return {
        "status": "online",
        "developer": "Maha"
    }

@app.post("/api/v1/chat")
def process_chat_query(request: ChatRequest):
    user_query = request.question
    
    if not user_query.strip():
        raise HTTPException(status_code=400, detail="Invalid question")

    return {
        "status": "success",
        "received_question": user_query,
        "answer": "Processing query successfully.",
        "sources": [
            "Digital Egypt Portal"
        ]
    }