from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    subject: str
    num_questions: int

OLLAMA_URL = "http://localhost:11434/api/generate"

@app.post("/generate_questions")
async def generate_questions(request: GenerateRequest):
    subject = request.subject
    num = request.num_questions
    
    prompt = f"Generate {num} short-answer questions on the subject '{subject}' for Btech level students. Each question should require a 1-2 line answer. Make sure the questions are slightly varied but maintain similar difficulty. Format the output as a numbered list of questions."
    
    payload = {
        "model": "mistral:7b",
        "prompt": prompt,
        "stream": False
    }
    
    payload = {
        "model": "mistral:7b",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        generated_text = data.get("response", "")
        
        # Simple parsing: split by numbers and remove numbering
        questions = []
        lines = generated_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and line[0].isdigit():
                # Remove the number and dot
                parts = line.split('.', 1)
                if len(parts) > 1:
                    question = parts[1].strip()
                    questions.append(question)
                else:
                    questions.append(line)
        
        return {"questions": questions}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error calling Ollama: {str(e)}")

@app.get("/")
async def root():
    return {"message": "AI Educational Web App Backend"}
