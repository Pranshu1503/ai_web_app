# Quick Start Guide - Email Verification

## 🚀 Quick Setup (Gmail)

### Step 1: Get Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. Sign in to your Gmail account
3. Click "Select app" → Choose "Mail"
4. Click "Select device" → Choose "Other" → Type "PopQuiz"
5. Click "Generate"
6. **Copy the 16-character password** (shown without spaces)    kvqi womf kese vira

### Step 2: Set Environment Variables

**Option A: Using the Setup Script (Recommended)**

```bash
# Double-click setup_email.bat and follow the prompts
```

**Option B: Manual Setup**

```cmd
set SMTP_HOST=smtp.gmail.com
set SMTP_PORT=587
set SMTP_USERNAME=your-email@gmail.com
set SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx
set FRONTEND_URL=http://localhost:8001
```

### Step 3: Start the Application

```bash
# Terminal 1 - Start Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 - Start Frontend
python start_frontend.py
```

## 📧 How Users Will Experience It

### Teacher Signup

1. Go to `/teacher/signup.html`
2. Enter email and password
3. Click "Sign Up"
4. **Alert: "Please check your email to verify your account"**
5. Open email inbox
6. Click verification link in email
7. **Redirected to success page**
8. Now can log in at `/teacher/faculty-login.html`

### Student Signup

1. Go to `/student/student-signup.html`
2. Enter email and password
3. Click "Sign Up"
4. **Alert: "Please check your email to verify your account"**
5. Open email inbox
6. Click verification link in email
7. **Redirected to success page**
8. Now can log in at `/student/student-login.html`

## 🔒 Security Features

✅ **Email must be verified before login**
✅ **Verification links expire after 24 hours**
✅ **Each verification token is single-use**
✅ **Passwords are hashed (never stored in plain text)**
✅ **Session tokens expire after 7 days**
✅ **SMTP connection uses TLS encryption**

## 📝 Test Without Email (Development Only)

If you want to skip email verification for testing:

```bash
# 1. Start backend
# 2. Manually verify in database
sqlite3 backend/popquiz.db
UPDATE users SET is_verified = 1 WHERE email = 'test@example.com';
.exit
```

## 🐛 Common Issues

### "Email verification failed"

- Check your email credentials are correct
- Ensure you're using an app password (not regular password for Gmail)
- Check environment variables are set: `echo %SMTP_USERNAME%`

### "Please verify your email before logging in"

- Check your email inbox (and spam folder)
- Click the verification link in the email
- Link expires after 24 hours - request a new one if needed

### Email not received

- Check spam/junk folder
- Verify sender email is valid and has SMTP access
- Check backend console for error messages
- Firewall might be blocking port 587

## 📂 Files Changed

### Backend

- `backend/main.py` - Added email verification logic
- `backend/requirements.txt` - Added aiosmtplib, email-validator

### Frontend

- `frontend/verify-email.html` - NEW: Verification success page
- `frontend/student/student-signup.html` - Updated with verification message
- `frontend/student/student-login.html` - Added verification error handling
- `frontend/teacher/signup.html` - Updated with verification message
- `frontend/teacher/faculty-login.html` - Added verification error handling

### Database

- `users` table - Added `is_verified` column
- `verification_tokens` table - NEW: Stores verification tokens

## 🔗 API Endpoints

```
POST   /auth/signup              - Teacher signup (sends verification email)
POST   /student/signup           - Student signup (sends verification email)
GET    /auth/verify-email        - Verify email with token
POST   /auth/resend-verification - Resend verification email
POST   /auth/login               - Teacher login (requires verification)
POST   /student/login            - Student login (requires verification)
```

## 📞 Need Help?

1. Read `EMAIL_VERIFICATION_SETUP.md` for detailed instructions
2. Check backend console for error messages
3. Check browser console (F12) for frontend errors
4. Verify environment variables: `set` (Windows) or `printenv` (Linux/Mac)
