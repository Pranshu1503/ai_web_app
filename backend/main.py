from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
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
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import io

app = FastAPI(title="PopQuiz AI Backend", description="AI-Powered Quiz Generation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Email Configuration (Use environment variables in production)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "sharmapranshu15@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "kvqiwomfkesevira")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Pydantic Models
class UserSignup(BaseModel):
    name: str
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

class QuizSubmissionRequest(BaseModel):
    quiz_id: int
    answers: dict
    score: Optional[float] = None

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
            name TEXT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'teacher',
            is_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Ensure role, is_verified, and name columns exist for older DBs
    cursor.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'role' not in cols:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'teacher'")
        except Exception:
            pass
    if 'is_verified' not in cols:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")
        except Exception:
            pass
    if 'name' not in cols:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN name TEXT")
        except Exception:
            pass
    
    # Verification tokens table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verification_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
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
    
    # Quiz submissions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            answers TEXT NOT NULL,  -- JSON string with student answers
            score REAL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quiz_id) REFERENCES quizzes (id),
            FOREIGN KEY (student_id) REFERENCES users (id)
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

def create_verification_token() -> str:
    return secrets.token_urlsafe(32)

async def send_verification_email(email: str, token: str):
    """Send verification email to user"""
    try:
        verification_link = f"{FRONTEND_URL}/verify-email.html?token={token}"
        
        message = MIMEMultipart("alternative")
        message["Subject"] = "Verify Your PopQuiz Account"
        message["From"] = SMTP_USERNAME
        message["To"] = email
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 10px;">
                    <h2 style="color: #4CAF50; text-align: center;">Welcome to PopQuiz!</h2>
                    <p>Thank you for signing up. Please verify your email address to complete your registration.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_link}" 
                           style="display: inline-block; padding: 12px 30px; background-color: #4CAF50; color: white; 
                                  text-decoration: none; border-radius: 5px; font-weight: bold;">
                            Verify Email Address
                        </a>
                    </div>
                    <p style="color: #666; font-size: 14px;">
                        Or copy and paste this link into your browser:<br>
                        <a href="{verification_link}" style="color: #4CAF50;">{verification_link}</a>
                    </p>
                    <p style="color: #666; font-size: 14px;">
                        This link will expire in 24 hours.
                    </p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        If you didn't create an account, please ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            start_tls=True
        )
        print(f"✅ Verification email sent successfully to {email}")
        return True
    except Exception as e:
        print(f"❌ Error sending email to {email}: {str(e)}")
        print(f"SMTP Config: {SMTP_HOST}:{SMTP_PORT}, Username: {SMTP_USERNAME}")
        return False

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.id, u.email, u.role FROM users u
        JOIN sessions s ON u.id = s.user_id
        WHERE s.token = ? AND s.expires_at > ?
    ''', (credentials.credentials, datetime.now()))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return {"id": user[0], "email": user[1], "role": user[2]}

# Authentication endpoints
@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user's information including name"""
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, email, role FROM users WHERE id = ?
    ''', (current_user["id"],))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user[0],
        "name": user[1],
        "email": user[2],
        "role": user[3]
    }

@app.post("/auth/signup")
async def signup(user_data: UserSignup):
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute('SELECT id FROM users WHERE email = ?', (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user (unverified)
        password_hash = hash_password(user_data.password)
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, is_verified) VALUES (?, ?, ?, ?, 0)
        ''', (user_data.name, user_data.email, password_hash, user_data.role or 'teacher'))
        
        user_id = cursor.lastrowid
        
        # Generate verification token
        verification_token = create_verification_token()
        expires_at = datetime.now() + timedelta(hours=24)
        
        cursor.execute('''
            INSERT INTO verification_tokens (user_id, token, expires_at) VALUES (?, ?, ?)
        ''', (user_id, verification_token, expires_at))
        
        conn.commit()
        
        # Send verification email
        email_sent = await send_verification_email(user_data.email, verification_token)
        
        if not email_sent:
            return {"message": "User created but email verification failed. Please contact support.", "email_sent": False}
        
        return {"message": "User created successfully. Please check your email to verify your account.", "email_sent": True}
    
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
        cursor.execute('SELECT id, password_hash, role, is_verified FROM users WHERE email = ?', (user_data.email,))
        user = cursor.fetchone()
        
        if not user or not verify_password(user_data.password, user[1]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Check if email is verified
        if not user[3]:  # is_verified column
            raise HTTPException(status_code=403, detail="Please verify your email before logging in")
        
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
            INSERT INTO users (name, email, password_hash, role, is_verified) VALUES (?, ?, ?, ?, 0)
        ''', (user_data.name, user_data.email, password_hash, 'student'))
        
        user_id = cursor.lastrowid
        
        # Generate verification token
        verification_token = create_verification_token()
        expires_at = datetime.now() + timedelta(hours=24)
        
        cursor.execute('''
            INSERT INTO verification_tokens (user_id, token, expires_at) VALUES (?, ?, ?)
        ''', (user_id, verification_token, expires_at))
        
        conn.commit()
        
        # Send verification email
        email_sent = await send_verification_email(user_data.email, verification_token)
        
        if not email_sent:
            return {'message': 'Student account created but email verification failed. Please contact support.', 'email_sent': False}
        
        return {'message': 'Student account created successfully. Please check your email to verify your account.', 'email_sent': True}
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
        cursor.execute('SELECT id, password_hash, role, is_verified FROM users WHERE email = ?', (user_data.email,))
        user = cursor.fetchone()
        if not user or not verify_password(user_data.password, user[1]):
            raise HTTPException(status_code=401, detail='Invalid email or password')
        if user[2] != 'student':
            raise HTTPException(status_code=403, detail='User is not a student')
        # Check if email is verified
        if not user[3]:  # is_verified column
            raise HTTPException(status_code=403, detail='Please verify your email before logging in')
        token = create_session_token()
        expires_at = datetime.now() + timedelta(days=7)
        cursor.execute('INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)', (token, user[0], expires_at))
        conn.commit()
        return { 'message': 'Login successful', 'token': token, 'expires_at': expires_at.isoformat() }
    finally:
        conn.close()

async def grade_answers_with_ollama(questions: list, answers: dict) -> int:
    """Grade student answers using Ollama Mistral 7B."""
    try:
        # Prepare grading prompt
        qa_pairs = []
        for i, question in enumerate(questions):
            answer_key = f"question_{i}"
            student_answer = answers.get(answer_key, "No answer provided")
            
            # Extract question text
            if isinstance(question, dict):
                q_text = question.get('question', str(question))
            else:
                q_text = str(question)
            
            qa_pairs.append(f"Question {i+1}: {q_text}\nStudent Answer: {student_answer}")
        
        qa_text = "\n\n".join(qa_pairs)
        
        prompt = f"""You are a grading assistant for B.Tech level quizzes. Grade the following student answers on a scale of 0-100.

{qa_text}

Evaluate each answer based on:
1. Correctness and accuracy of information
2. Completeness of the response
3. Clarity and coherence
4. Technical accuracy

Provide ONLY a single number between 0 and 100 representing the overall score percentage. Do not include any explanations, just the number."""

        payload = {
            "model": "mistral:7b",
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(OLLAMA_URL, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        generated_text = data.get("response", "").strip()
        
        # Extract numeric score
        import re
        numbers = re.findall(r'\d+', generated_text)
        if numbers:
            score = int(numbers[0])
            # Ensure score is within 0-100 range
            score = max(0, min(100, score))
            return score
        else:
            # Default score if parsing fails
            return 50
            
    except Exception as e:
        print(f"Error grading with Ollama: {str(e)}")
        # Return a default score if grading fails
        return 50

@app.post('/student/submit-quiz')
async def submit_quiz(submission: QuizSubmissionRequest, current_user: dict = Depends(get_current_user)):
    """Submit student quiz answers and grade them using Ollama."""
    print(f"DEBUG: Current user role: {current_user.get('role')}, expected: 'student'")
    if current_user.get('role') != 'student':
        raise HTTPException(status_code=403, detail=f'Only students can submit quizzes. Your role: {current_user.get("role")}')
    
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        # Check if student already submitted this quiz
        cursor.execute('''
            SELECT id FROM quiz_submissions 
            WHERE quiz_id = ? AND student_id = ?
        ''', (submission.quiz_id, current_user['id']))
        
        existing_submission = cursor.fetchone()
        if existing_submission:
            raise HTTPException(status_code=400, detail='You have already submitted this quiz')
        
        # Get quiz questions
        cursor.execute('SELECT questions FROM quizzes WHERE id = ?', (submission.quiz_id,))
        quiz_row = cursor.fetchone()
        if not quiz_row:
            raise HTTPException(status_code=404, detail='Quiz not found')
        
        questions = json.loads(quiz_row[0]) if quiz_row[0] else []
        
        # Grade the answers using Ollama
        print(f"Grading quiz submission for student {current_user['id']}...")
        score = await grade_answers_with_ollama(questions, submission.answers)
        print(f"Graded score: {score}%")
        
        # Insert submission with graded score
        cursor.execute('''
            INSERT INTO quiz_submissions (quiz_id, student_id, answers, score)
            VALUES (?, ?, ?, ?)
        ''', (submission.quiz_id, current_user['id'], json.dumps(submission.answers), score))
        
        conn.commit()
        return {
            'message': 'Quiz submitted and graded successfully', 
            'submission_id': cursor.lastrowid,
            'score': score
        }
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if 'UNIQUE constraint failed' in str(e) or 'idx_unique_submission' in str(e):
            raise HTTPException(status_code=400, detail='You have already submitted this quiz')
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        conn.rollback()
        print(f"Error in submit_quiz: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post('/student/regrade-submissions')
async def regrade_submissions(current_user: dict = Depends(get_current_user)):
    """Regrade all ungraded submissions for the current student."""
    if current_user.get('role') != 'student':
        raise HTTPException(status_code=403, detail='Only students can regrade their submissions')
    
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        # Get all submissions with NULL scores for this student
        cursor.execute('''
            SELECT qs.id, qs.quiz_id, qs.answers, q.questions
            FROM quiz_submissions qs
            JOIN quizzes q ON qs.quiz_id = q.id
            WHERE qs.student_id = ? AND (qs.score IS NULL OR qs.score = 0)
        ''', (current_user['id'],))
        
        submissions = cursor.fetchall()
        graded_count = 0
        
        for sub_id, quiz_id, answers_json, questions_json in submissions:
            try:
                questions = json.loads(questions_json) if questions_json else []
                answers = json.loads(answers_json) if answers_json else {}
                
                # Grade the answers
                score = await grade_answers_with_ollama(questions, answers)
                
                # Update the score
                cursor.execute('''
                    UPDATE quiz_submissions SET score = ? WHERE id = ?
                ''', (score, sub_id))
                
                graded_count += 1
                print(f"Regraded submission {sub_id}: {score}%")
            except Exception as e:
                print(f"Error regrading submission {sub_id}: {str(e)}")
                continue
        
        conn.commit()
        return {
            'message': f'Successfully regraded {graded_count} submissions',
            'graded_count': graded_count
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/auth/verify-email")
async def verify_email(token: str):
    """Verify user email with token"""
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        # Check if token exists and is valid
        cursor.execute('''
            SELECT user_id, expires_at FROM verification_tokens 
            WHERE token = ?
        ''', (token,))
        
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=400, detail="Invalid verification token")
        
        user_id, expires_at = result
        expires_at_dt = datetime.fromisoformat(expires_at)
        
        if datetime.now() > expires_at_dt:
            raise HTTPException(status_code=400, detail="Verification token has expired")
        
        # Check if user is already verified
        cursor.execute('SELECT is_verified FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if user and user[0]:
            return {"message": "Email already verified", "already_verified": True}
        
        # Mark user as verified
        cursor.execute('UPDATE users SET is_verified = 1 WHERE id = ?', (user_id,))
        
        # Delete used token
        cursor.execute('DELETE FROM verification_tokens WHERE token = ?', (token,))
        
        conn.commit()
        
        return {"message": "Email verified successfully", "verified": True}
    
    finally:
        conn.close()

@app.post("/auth/resend-verification")
async def resend_verification(user_data: UserLogin):
    """Resend verification email"""
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute('SELECT id, is_verified FROM users WHERE email = ?', (user_data.email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id, is_verified = user
        
        if is_verified:
            raise HTTPException(status_code=400, detail="Email already verified")
        
        # Delete old tokens
        cursor.execute('DELETE FROM verification_tokens WHERE user_id = ?', (user_id,))
        
        # Generate new verification token
        verification_token = create_verification_token()
        expires_at = datetime.now() + timedelta(hours=24)
        
        cursor.execute('''
            INSERT INTO verification_tokens (user_id, token, expires_at) VALUES (?, ?, ?)
        ''', (user_id, verification_token, expires_at))
        
        conn.commit()
        
        # Send verification email
        email_sent = await send_verification_email(user_data.email, verification_token)
        
        if not email_sent:
            raise HTTPException(status_code=500, detail="Failed to send verification email")
        
        return {"message": "Verification email sent successfully"}
    
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

# Test endpoint without authentication - with file upload support
@app.post("/test/generate_questions")
async def test_generate_questions(
    topic: str = Form(...),
    bloom_level: str = Form(...),
    question_type: str = Form(...),
    num_questions: int = Form(...),
    handout: Optional[UploadFile] = File(None)
):
    """Test endpoint for generating questions without authentication, supports optional file upload"""
    handout_content = None
    
    if handout:
        try:
            # Read file content
            content = await handout.read()
            
            # Extract text based on file type
            if handout.filename.endswith('.txt'):
                handout_content = content.decode('utf-8')
            elif handout.filename.endswith('.pdf'):
                try:
                    import PyPDF2
                    pdf_file = io.BytesIO(content)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    handout_content = ""
                    for page in pdf_reader.pages:
                        handout_content += page.extract_text()
                except ImportError:
                    print("PyPDF2 not installed, skipping PDF extraction")
                except Exception as e:
                    print(f"Error extracting PDF: {e}")
            
            # Limit content length to avoid token overflow
            if handout_content and len(handout_content) > 5000:
                handout_content = handout_content[:5000] + "..."
                
        except Exception as e:
            print(f"Error processing handout: {e}")
    
    return await _generate_questions_internal(topic, bloom_level, question_type, num_questions, handout_content)

async def _generate_questions_internal(topic: str, bloom_level: str, question_type: str, num: int, handout_content: Optional[str] = None):
    """Internal function to generate questions with optional handout context"""
    
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
    
    # Add handout context if provided
    context_prefix = ""
    if handout_content:
        context_prefix = f"""Based on the following course material:

---
{handout_content}
---

"""
    
    if question_type == "MCQ":
        prompt = f"""{context_prefix}Generate {num} multiple-choice questions on the topic '{topic}' at the {bloom_level} cognitive level (students should {bloom_desc}).

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
        prompt = f"""{context_prefix}Generate {num} true/false questions on the topic '{topic}' at the {bloom_level} cognitive level (students should {bloom_desc}).

Each question should:
- Be appropriate for B.Tech level students
- Be clearly answerable as True or False
- NOT include the correct answer or any answer hints — only provide the statement

Format each question as:
Q1. [Statement]

Generate exactly {num} questions in this format."""

    else:  # Short Answer
        prompt = f"""{context_prefix}Generate {num} short-answer questions on the topic '{topic}' at the {bloom_level} cognitive level (students should {bloom_desc}).

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
    """Return all quizzes that the student hasn't completed yet.
    Students will use this to see available quizzes.
    """
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT q.id, q.name, q.topic, q.bloom_level, q.question_type, q.created_at, q.updated_at, u.name, u.email
        FROM quizzes q
        JOIN users u ON q.user_id = u.id
        LEFT JOIN quiz_submissions qs ON q.id = qs.quiz_id AND qs.student_id = ?
        WHERE qs.id IS NULL
        ORDER BY q.updated_at DESC
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
            "updated_at": row[6],
            "creator_name": row[7] or row[8],
            "creator_email": row[8]
        }
        quizzes.append(quiz)

    conn.close()
    return {"quizzes": quizzes}

@app.get("/quizzes/completed")
async def get_completed_quizzes(current_user: dict = Depends(get_current_user)):
    """Return all quizzes that the student has completed.
    """
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT q.id, q.name, q.topic, q.bloom_level, q.question_type, q.created_at, q.updated_at, u.name, u.email, qs.submitted_at, qs.score
        FROM quizzes q
        JOIN users u ON q.user_id = u.id
        JOIN quiz_submissions qs ON q.id = qs.quiz_id AND qs.student_id = ?
        ORDER BY qs.submitted_at DESC
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
            "updated_at": row[6],
            "creator_name": row[7] or row[8],
            "creator_email": row[8],
            "submitted_at": row[9],
            "score": row[10]
        }
        quizzes.append(quiz)

    conn.close()
    return {"quizzes": quizzes}

@app.get("/teacher/quiz-submissions")
async def get_teacher_quiz_submissions(current_user: dict = Depends(get_current_user)):
    """Get all quiz submissions for quizzes created by the logged-in teacher."""
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            qs.id, qs.quiz_id, qs.student_id, qs.answers, qs.score, qs.submitted_at,
            q.name as quiz_name, q.topic, q.questions,
            u.name as student_name, u.email as student_email
        FROM quiz_submissions qs
        JOIN quizzes q ON qs.quiz_id = q.id
        JOIN users u ON qs.student_id = u.id
        WHERE q.user_id = ?
        ORDER BY qs.submitted_at DESC
    ''', (current_user["id"],))
    
    submissions = []
    for row in cursor.fetchall():
        submission = {
            "id": row[0],
            "quiz_id": row[1],
            "student_id": row[2],
            "answers": json.loads(row[3]) if row[3] else {},
            "score": row[4],
            "submitted_at": row[5],
            "quiz_name": row[6],
            "quiz_topic": row[7],
            "questions": json.loads(row[8]) if row[8] else [],
            "student_name": row[9],
            "student_email": row[10]
        }
        submissions.append(submission)
    
    conn.close()
    return {"submissions": submissions}

@app.get("/student/my-submissions")
async def get_student_submissions(current_user: dict = Depends(get_current_user)):
    """Get all quiz submissions for the logged-in student with full details."""
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            qs.id, qs.quiz_id, qs.student_id, qs.answers, qs.score, qs.submitted_at,
            q.name as quiz_name, q.topic, q.questions,
            u.name as creator_name, u.email as creator_email
        FROM quiz_submissions qs
        JOIN quizzes q ON qs.quiz_id = q.id
        JOIN users u ON q.user_id = u.id
        WHERE qs.student_id = ?
        ORDER BY qs.submitted_at DESC
    ''', (current_user["id"],))
    
    submissions = []
    for row in cursor.fetchall():
        submission = {
            "id": row[0],
            "quiz_id": row[1],
            "student_id": row[2],
            "answers": json.loads(row[3]) if row[3] else {},
            "score": row[4],
            "submitted_at": row[5],
            "quiz_name": row[6],
            "quiz_topic": row[7],
            "questions": json.loads(row[8]) if row[8] else [],
            "creator_name": row[9],
            "creator_email": row[10]
        }
        submissions.append(submission)
    
    conn.close()
    return {"submissions": submissions}

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
