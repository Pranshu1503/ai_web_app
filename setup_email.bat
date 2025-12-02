@echo off
REM Email Verification Setup Script for Windows
REM This script helps you set environment variables for email verification

echo ========================================
echo PopQuiz Email Verification Setup
echo ========================================
echo.

echo This script will help you configure email verification for PopQuiz.
echo You'll need:
echo   1. Your email address
echo   2. Your email provider's SMTP settings
echo   3. An app password (for Gmail) or regular password
echo.

set /p SMTP_USER="Enter your email address: "
echo.

echo Select your email provider:
echo   1. Gmail (smtp.gmail.com)
echo   2. Outlook/Hotmail (smtp-mail.outlook.com)
echo   3. Yahoo (smtp.mail.yahoo.com)
echo   4. Custom
echo.

set /p PROVIDER_CHOICE="Enter choice (1-4): "

if "%PROVIDER_CHOICE%"=="1" (
    set SMTP_HOST=smtp.gmail.com
    set SMTP_PORT=587
    echo.
    echo NOTE: For Gmail, you need to:
    echo   1. Enable 2-Step Verification in your Google Account
    echo   2. Generate an App Password at: https://myaccount.google.com/apppasswords
    echo   3. Use the 16-character app password below
    echo.
) else if "%PROVIDER_CHOICE%"=="2" (
    set SMTP_HOST=smtp-mail.outlook.com
    set SMTP_PORT=587
) else if "%PROVIDER_CHOICE%"=="3" (
    set SMTP_HOST=smtp.mail.yahoo.com
    set SMTP_PORT=587
) else (
    set /p SMTP_HOST="Enter SMTP host: "
    set /p SMTP_PORT="Enter SMTP port (usually 587): "
)

echo.
set /p SMTP_PASS="kvqi womf kese vira"
echo.

set /p FRONTEND_PORT="Enter frontend port (press Enter for default 8001): "
if "%FRONTEND_PORT%"=="" set FRONTEND_PORT=8001

REM Set environment variables
set SMTP_HOST=%SMTP_HOST%
set SMTP_PORT=%SMTP_PORT%
set SMTP_USERNAME=%SMTP_USER%
set SMTP_PASSWORD=%SMTP_PASS%
set FRONTEND_URL=http://localhost:%FRONTEND_PORT%

echo.
echo ========================================
echo Configuration Complete!
echo ========================================
echo.
echo Environment variables have been set for this session:
echo   SMTP_HOST = %SMTP_HOST%
echo   SMTP_PORT = %SMTP_PORT%
echo   SMTP_USERNAME = %SMTP_USERNAME%
echo   SMTP_PASSWORD = [hidden]
echo   FRONTEND_URL = %FRONTEND_URL%
echo.
echo These variables are only set for this command prompt window.
echo To make them permanent, add them to your System Environment Variables.
echo.
echo Now starting the backend server...
echo.

cd backend
python -m uvicorn main:app --reload --port 8000
