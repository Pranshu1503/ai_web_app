# Email Verification Setup Guide

## Overview

This system implements 2-factor authentication with email verification for user signups. Users must verify their email addresses before they can log in.

## Email Configuration

### For Gmail Users (Recommended for Testing)

1. **Enable 2-Step Verification**

   - Go to your Google Account settings
   - Navigate to Security > 2-Step Verification
   - Follow the prompts to enable it

2. **Generate App Password**

   - Go to Security > 2-Step Verification > App passwords
   - Select "Mail" and "Other (Custom name)"
   - Enter "PopQuiz" as the name
   - Click "Generate"
   - Copy the 16-character password

3. **Set Environment Variables**

   **Windows (Command Prompt):**

   ```cmd
   set SMTP_HOST=smtp.gmail.com
   set SMTP_PORT=587
   set SMTP_USERNAME=your-email@gmail.com
   set SMTP_PASSWORD=your-16-char-app-password
   set FRONTEND_URL=http://localhost:8001
   ```

   **Windows (PowerShell):**

   ```powershell
   $env:SMTP_HOST="smtp.gmail.com"
   $env:SMTP_PORT="587"
   $env:SMTP_USERNAME="your-email@gmail.com"
   $env:SMTP_PASSWORD="your-16-char-app-password"
   $env:FRONTEND_URL="http://localhost:8001"
   ```

   **Linux/Mac:**

   ```bash
   export SMTP_HOST=smtp.gmail.com
   export SMTP_PORT=587
   export SMTP_USERNAME=your-email@gmail.com
   export SMTP_PASSWORD=your-16-char-app-password
   export FRONTEND_URL=http://localhost:8001
   ```

### For Other Email Providers

#### Outlook/Hotmail

```
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
```

#### Yahoo Mail

```
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USERNAME=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

## Installation Steps

1. **Install Required Python Packages**

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure Email Settings**

   - Set the environment variables as shown above
   - OR edit `backend/main.py` lines 23-27 to hardcode your settings (not recommended for production)

3. **Start the Backend**

   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

4. **Start the Frontend**
   ```bash
   python start_frontend.py
   ```

## How It Works

### User Signup Flow

1. User fills out signup form (student or teacher)
2. Backend creates user account with `is_verified=0`
3. Backend generates a unique verification token (valid for 24 hours)
4. Backend sends verification email with link
5. User receives email and clicks verification link
6. Verification page validates token and marks user as verified
7. User can now log in with their credentials

### Email Verification

- Verification tokens expire after 24 hours
- Each token can only be used once
- Users cannot log in until email is verified
- Verification link format: `http://localhost:8001/verify-email.html?token=<token>`

### Security Features

- Passwords are hashed using SHA-256
- Session tokens expire after 7 days
- Verification tokens are cryptographically secure (32 bytes)
- SMTP connection uses TLS encryption

## Database Schema Changes

The system adds two new elements to the database:

### Users Table - New Column

- `is_verified` (INTEGER): 0 = unverified, 1 = verified

### New Table: verification_tokens

- `id` (INTEGER PRIMARY KEY)
- `user_id` (INTEGER FOREIGN KEY)
- `token` (TEXT UNIQUE)
- `expires_at` (TIMESTAMP)
- `created_at` (TIMESTAMP)

## API Endpoints

### POST /auth/signup

Creates a teacher account and sends verification email.

### POST /student/signup

Creates a student account and sends verification email.

### GET /auth/verify-email?token={token}

Verifies user email with the provided token.

### POST /auth/resend-verification

Resends verification email to user.

### POST /auth/login

Login for teachers (requires verified email).

### POST /student/login

Login for students (requires verified email).

## Testing Without Email

If you want to test without setting up email:

1. Comment out lines 259-261 and 333-335 in `backend/main.py` (the email sending part)
2. Manually verify users in database:
   ```bash
   sqlite3 popquiz.db
   UPDATE users SET is_verified = 1 WHERE email = 'test@example.com';
   .exit
   ```

## Troubleshooting

### Email Not Sending

- Check environment variables are set correctly
- Verify SMTP credentials are correct
- Check firewall isn't blocking port 587
- Look at backend console for error messages

### Verification Link Not Working

- Ensure frontend is running on correct port (default: 8001)
- Check FRONTEND_URL environment variable
- Verify token hasn't expired (24 hours)

### Login Fails After Verification

- Check database: `SELECT is_verified FROM users WHERE email = 'your@email.com';`
- Should return 1 (verified)
- If 0, click verification link again

## Production Considerations

1. **Use Environment Variables** - Never hardcode credentials
2. **Use HTTPS** - Encrypt all traffic in production
3. **Use Proper Email Service** - Consider SendGrid, AWS SES, or similar
4. **Stronger Password Hashing** - Consider bcrypt instead of SHA-256
5. **Rate Limiting** - Prevent spam signups and verification requests
6. **Email Templates** - Use professional HTML email templates
7. **Domain Verification** - Set up SPF, DKIM, and DMARC records

## Support

If you encounter issues:

1. Check backend console logs
2. Check browser console (F12)
3. Verify email credentials are correct
4. Ensure all environment variables are set
5. Check spam folder for verification emails
