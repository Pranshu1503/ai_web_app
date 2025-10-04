@echo off
echo Starting PopQuiz Backend Server...
echo.
echo Make sure you have:
echo 1. Installed Python 3.8+ 
echo 2. Installed Ollama and pulled mistral:7b model
echo 3. Started Ollama server (ollama serve)
echo.
echo Starting server on http://localhost:8000
cd backend
"..\\.venv\\Scripts\\python.exe" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause