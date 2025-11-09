from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import requests
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
import json

app = FastAPI(title="PopQuiz AI Backend", description="AI-Powered Quiz Generation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Pydantic Models
class UserSignup(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = 'teacher'

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GenerateRequest(BaseModel):
    topic: str
    bloom_level: str
    question_type: str
    num_questions: int

class SaveQuizRequest(BaseModel):
    name: str
    questions: List[str]
    topic: str
    bloom_level: str
    question_type: str

class UpdateQuestionRequest(BaseModel):
    quiz_id: int
    question_index: int
    new_question: str

OLLAMA_URL = "http://localhost:11434/api/generate"

# Database setup
def init_db():
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'teacher',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Ensure role column exists for older DBs
    cursor.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'role' not in cols:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'teacher'")
        except Exception:
            pass
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Quizzes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            topic TEXT NOT NULL,
            bloom_level TEXT NOT NULL,
            question_type TEXT NOT NULL,
            questions TEXT NOT NULL,  -- JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hash: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hash

def create_session_token() -> str:
    return secrets.token_urlsafe(32)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.id, u.email FROM users u
        JOIN sessions s ON u.id = s.user_id
        WHERE s.token = ? AND s.expires_at > ?
    ''', (credentials.credentials, datetime.now()))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return {"id": user[0], "email": user[1]}

# Authentication endpoints
@app.post("/auth/signup")
async def signup(user_data: UserSignup):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute('SELECT id FROM users WHERE email = ?', (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        password_hash = hash_password(user_data.password)
        cursor.execute('''
            INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)
        ''', (user_data.email, password_hash, user_data.role or 'teacher'))
        
        conn.commit()
        return {"message": "User created successfully"}
    
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered")
    finally:
        conn.close()

@app.post("/auth/login")
async def login(user_data: UserLogin):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        # Verify user credentials
        cursor.execute('SELECT id, password_hash, role FROM users WHERE email = ?', (user_data.email,))
        user = cursor.fetchone()
        
        if not user or not verify_password(user_data.password, user[1]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Create session token
        token = create_session_token()
        expires_at = datetime.now() + timedelta(days=7)  # Token valid for 7 days
        
        cursor.execute('''
            INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)
        ''', (token, user[0], expires_at))
        
        conn.commit()
        
        return {
            "message": "Login successful",
            "token": token,
            "expires_at": expires_at.isoformat()
        }
    
    finally:
        conn.close()


@app.post('/student/signup')
async def student_signup(user_data: UserSignup):
    """Create a student user. Role is forced to 'student'."""
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM users WHERE email = ?', (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail='Email already registered')
        password_hash = hash_password(user_data.password)
        cursor.execute('''
            INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)
        ''', (user_data.email, password_hash, 'student'))
        conn.commit()
        return { 'message': 'Student account created successfully' }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail='Email already registered')
    finally:
        conn.close()


@app.post('/student/login')
async def student_login(user_data: UserLogin):
    """Login for student users only."""
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, password_hash, role FROM users WHERE email = ?', (user_data.email,))
        user = cursor.fetchone()
        if not user or not verify_password(user_data.password, user[1]):
            raise HTTPException(status_code=401, detail='Invalid email or password')
        if user[2] != 'student':
            raise HTTPException(status_code=403, detail='User is not a student')
        token = create_session_token()
        expires_at = datetime.now() + timedelta(days=7)
        cursor.execute('INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)', (token, user[0], expires_at))
        conn.commit()
        return { 'message': 'Login successful', 'token': token, 'expires_at': expires_at.isoformat() }
    finally:
        conn.close()

@app.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user), 
                credentials: HTTPAuthorizationCredentials = Depends(security)):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM sessions WHERE token = ?', (credentials.credentials,))
    conn.commit()
    conn.close()
    
    return {"message": "Logged out successfully"}
# Quiz generation endpoint
@app.post("/generate_questions")
async def generate_questions(request: GenerateRequest, current_user: dict = Depends(get_current_user)):
    return await _generate_questions_internal(request)

# Test endpoint without authentication
@app.post("/test/generate_questions")
async def test_generate_questions(request: GenerateRequest):
    """Test endpoint for generating questions without authentication"""
    return await _generate_questions_internal(request)

async def _generate_questions_internal(request: GenerateRequest):
    topic = request.topic
    bloom_level = request.bloom_level
    question_type = request.question_type
    num = request.num_questions
    
    # Create detailed prompt based on the parameters
    bloom_descriptions = {
        "Remembering": "recall basic facts, definitions, and concepts",
        "Understanding": "explain ideas, summarize information, and interpret meaning",
        "Applying": "use knowledge in new situations, solve problems, and apply concepts",
        "Analyzing": "break down information, compare and contrast, and examine relationships",
        "Evaluating": "make judgments, critique arguments, and assess validity",
        "Creating": "design solutions, develop new ideas, and synthesize information"
    }
    
    bloom_desc = bloom_descriptions.get(bloom_level, "demonstrate understanding of")
    
    if question_type == "MCQ":
        prompt = f"""Generate {num} multiple-choice questions on the topic '{topic}' at the {bloom_level} cognitive level (students should {bloom_desc}).

Each question should:
- Be appropriate for B.Tech level students
- Have 4 options (A, B, C, D)
- NOT include the correct answer or any answer hints — only provide the question and its options

Format each question as:
Q1. [Question text]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

Generate exactly {num} questions in this format."""

    elif question_type == "True/False":
        prompt = f"""Generate {num} true/false questions on the topic '{topic}' at the {bloom_level} cognitive level (students should {bloom_desc}).

Each question should:
- Be appropriate for B.Tech level students
- Be clearly answerable as True or False
- NOT include the correct answer or any answer hints — only provide the statement

Format each question as:
Q1. [Statement]

Generate exactly {num} questions in this format."""

    else:  # Short Answer
        prompt = f"""Generate {num} short-answer questions on the topic '{topic}' at the {bloom_level} cognitive level (students should {bloom_desc}).

Each question should:
- Be appropriate for B.Tech level students
- Require a 2-3 sentence answer
- Be specific and focused
- NOT include answers or model responses — only provide the question text

Format each question as:
Q1. [Question text]

Generate exactly {num} questions in this format."""
    
    payload = {
        "model": "mistral:7b",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        generated_text = data.get("response", "")
        
        # Parse questions based on type (LLM no longer provides answers)
        questions = []
        lines = generated_text.strip().split('\n')
        # normalize and trim
        lines = [l.rstrip() for l in lines]

        if question_type == 'MCQ':
            current_question = None
            for line in lines:
                s = line.strip()
                if not s: 
                    continue
                # Start of a new question like 'Q1.' or 'Q1)'
                if s.lower().startswith('q') and len(s) > 1 and s[1].isdigit():
                    # push previous
                    if current_question:
                        questions.append(current_question.strip())
                    current_question = s
                else:
                    # append options or continuation lines
                    if current_question is None:
                        # sometimes generators omit Q numbering; start new
                        current_question = s
                    else:
                        current_question += '\n' + s
            if current_question:
                questions.append(current_question.strip())
        else:
            # Short Answer and True/False: each 'Qn.' line is a question
            for line in lines:
                s = line.strip()
                if not s: continue
                if s.lower().startswith('q') and len(s) > 1 and s[1].isdigit():
                    parts = s.split('.', 1)
                    if len(parts) > 1:
                        questions.append(parts[1].strip())
                else:
                    # fallback: treat any non-empty line as a question if none collected
                    if not questions:
                        questions.append(s)
        
        # If parsing failed, fallback to simple line splitting
        if not questions:
            lines = generated_text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:  # Filter out very short lines
                    questions.append(line)
        
        # Ensure we don't exceed requested number
        questions = questions[:num]
        
        return {"questions": questions}
    except requests.RequestException as e:
        # Fallback to demo questions if Ollama is not available
        print(f"Ollama not available: {str(e)}")
        print("Using fallback demo questions...")
        
        # Generate fallback questions based on topic and type
        fallback_questions = generate_fallback_questions(topic, question_type, bloom_level, num)
        return {"questions": fallback_questions}


def generate_fallback_questions(topic: str, question_type: str, bloom_level: str, num: int) -> list:
    """Generate fallback questions when Ollama is not available"""
    
    base_questions = {
        "Short Answer": [
            f"Define {topic} and explain its key characteristics.",
            f"What are the main components of {topic}?",
            f"How does {topic} impact modern computing systems?",
            f"Compare and contrast different approaches to {topic}.",
            f"Explain the advantages and disadvantages of {topic}.",
            f"What are the practical applications of {topic}?",
            f"How has {topic} evolved over time?",
            f"What challenges are associated with implementing {topic}?",
            f"Describe the relationship between {topic} and system performance.",
            f"What future developments do you expect in {topic}?"
        ],
        "MCQ": [
            f"Q1. Which of the following best describes {topic}?\nA) Option A related to {topic}\nB) Option B related to {topic}\nC) Option C related to {topic}\nD) Option D related to {topic}",
            f"Q2. What is a key feature of {topic}?\nA) Feature A\nB) Feature B\nC) Feature C\nD) Feature D",
            f"Q3. In the context of {topic}, which statement is most accurate?\nA) Statement A\nB) Statement B\nC) Statement C\nD) Statement D"
        ],
        "True/False": [
            f"Q1. {topic} is essential for modern computer systems.",
            f"Q2. {topic} has no impact on system performance.",
            f"Q3. Understanding {topic} is important for B.Tech students.",
            f"Q4. {topic} concepts are only theoretical and have no practical applications.",
            f"Q5. {topic} has remained unchanged since its inception."
        ]
    }
    
    questions = base_questions.get(question_type, base_questions["Short Answer"])
    
    # Add bloom level context
    if bloom_level == "Analyzing":
        if question_type == "Short Answer":
            questions = [q.replace("Define", "Analyze").replace("What are", "Compare") for q in questions[:3]]
    elif bloom_level == "Evaluating":
        if question_type == "Short Answer":
            questions = [q.replace("Define", "Evaluate").replace("Explain", "Critically assess") for q in questions[:3]]
    
    # Return requested number of questions, cycling if needed
    result = []
    for i in range(num):
        result.append(questions[i % len(questions)])
    
    return result

# Quiz management endpoints
@app.post("/quizzes")
async def save_quiz(request: SaveQuizRequest, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        questions_json = json.dumps(request.questions)
        cursor.execute('''
            INSERT INTO quizzes (user_id, name, topic, bloom_level, question_type, questions)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (current_user["id"], request.name, request.topic, request.bloom_level, 
              request.question_type, questions_json))
        
        quiz_id = cursor.lastrowid
        conn.commit()
        
        return {"message": "Quiz saved successfully", "quiz_id": quiz_id}
    
    finally:
        conn.close()

@app.get("/quizzes")
async def get_user_quizzes(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, topic, bloom_level, question_type, created_at, updated_at
        FROM quizzes 
        WHERE user_id = ?
        ORDER BY updated_at DESC
    ''', (current_user["id"],))
    
    quizzes = []
    for row in cursor.fetchall():
        quiz = {
            "id": row[0],
            "name": row[1],
            "topic": row[2],
            "bloom_level": row[3],
            "question_type": row[4],
            "created_at": row[5],
            "updated_at": row[6]
        }
        quizzes.append(quiz)
    
    conn.close()
    return {"quizzes": quizzes}


@app.get("/quizzes/assigned")
async def get_assigned_quizzes(current_user: dict = Depends(get_current_user)):
    """Return all quizzes in the system (assigned by teachers).
    Students will use this to see available quizzes. This endpoint returns
    basic metadata about each quiz and the creator's email.
    """
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT q.id, q.name, q.topic, q.bloom_level, q.question_type, q.created_at, q.updated_at, u.email
        FROM quizzes q
        JOIN users u ON q.user_id = u.id
        ORDER BY q.updated_at DESC
    ''')

    quizzes = []
    for row in cursor.fetchall():
        quiz = {
            "id": row[0],
            "name": row[1],
            "topic": row[2],
            "bloom_level": row[3],
            "question_type": row[4],
            "created_at": row[5],
            "updated_at": row[6],
            "creator_email": row[7]
        }
        quizzes.append(quiz)

    conn.close()
    return {"quizzes": quizzes}

@app.get("/quizzes/{quiz_id}")
async def get_quiz(quiz_id: int, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, topic, bloom_level, question_type, questions, created_at, updated_at
        FROM quizzes 
        WHERE id = ? AND user_id = ?
    ''', (quiz_id, current_user["id"]))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz = {
        "id": row[0],
        "name": row[1],
        "topic": row[2],
        "bloom_level": row[3],
        "question_type": row[4],
        "questions": json.loads(row[5]),
        "created_at": row[6],
        "updated_at": row[7]
    }
    
    return quiz


@app.get("/quizzes/public/{quiz_id}")
async def get_public_quiz(quiz_id: int, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Public view of a quiz by id. Allows students to retrieve quizzes created by teachers.
    If a token is provided it is ignored for ownership checks; this endpoint is intended for read-only access.
    """
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, name, topic, bloom_level, question_type, questions, created_at, updated_at
        FROM quizzes
        WHERE id = ?
    ''', (quiz_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")

    quiz = {
        "id": row[0],
        "name": row[1],
        "topic": row[2],
        "bloom_level": row[3],
        "question_type": row[4],
        "questions": json.loads(row[5]),
        "created_at": row[6],
        "updated_at": row[7]
    }

    return quiz

@app.put("/quizzes/{quiz_id}")
async def update_quiz(quiz_id: int, request: SaveQuizRequest, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        questions_json = json.dumps(request.questions)
        cursor.execute('''
            UPDATE quizzes 
            SET name = ?, topic = ?, bloom_level = ?, question_type = ?, questions = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
        ''', (request.name, request.topic, request.bloom_level, request.question_type, 
              questions_json, datetime.now(), quiz_id, current_user["id"]))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        conn.commit()
        return {"message": "Quiz updated successfully"}
    
    finally:
        conn.close()

@app.delete("/quizzes/{quiz_id}")
async def delete_quiz(quiz_id: int, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM quizzes WHERE id = ? AND user_id = ?', (quiz_id, current_user["id"]))
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Quiz deleted successfully"}

@app.put("/quizzes/{quiz_id}/questions")
async def update_question(quiz_id: int, request: UpdateQuestionRequest, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        # Get current quiz
        cursor.execute('SELECT questions FROM quizzes WHERE id = ? AND user_id = ?', 
                      (quiz_id, current_user["id"]))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        questions = json.loads(row[0])
        
        if request.question_index < 0 or request.question_index >= len(questions):
            raise HTTPException(status_code=400, detail="Invalid question index")
        
        # Update the specific question
        questions[request.question_index] = request.new_question
        
        # Save back to database
        questions_json = json.dumps(questions)
        cursor.execute('''
            UPDATE quizzes 
            SET questions = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
        ''', (questions_json, datetime.now(), quiz_id, current_user["id"]))
        
        conn.commit()
        return {"message": "Question updated successfully"}
    
    finally:
        conn.close()

@app.post("/quizzes/{quiz_id}/duplicate")
async def duplicate_quiz(quiz_id: int, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        # Get original quiz
        cursor.execute('''
            SELECT name, topic, bloom_level, question_type, questions
            FROM quizzes WHERE id = ? AND user_id = ?
        ''', (quiz_id, current_user["id"]))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        # Create duplicate with "(Copy)" suffix
        new_name = f"{row[0]} (Copy)"
        cursor.execute('''
            INSERT INTO quizzes (user_id, name, topic, bloom_level, question_type, questions)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (current_user["id"], new_name, row[1], row[2], row[3], row[4]))
        
        new_quiz_id = cursor.lastrowid
        conn.commit()
        
        return {"message": "Quiz duplicated successfully", "quiz_id": new_quiz_id}
    
    finally:
        conn.close()

@app.get("/")
async def root():
    return {"message": "PopQuiz AI Backend - Educational Quiz Generation System"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
