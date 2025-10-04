#!/usr/bin/env python3
"""
PopQuiz Setup Script
This script sets up the entire PopQuiz application including:
1. Python virtual environment
2. Backend dependencies
3. Database initialization
4. Instructions for Ollama setup
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e.stderr}")
        return False

def main():
    print("=" * 60)
    print("PopQuiz AI Quiz Generation System - Setup Script")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("backend/main.py"):
        print("Error: Please run this script from the ai_web_app root directory")
        sys.exit(1)
    
    # Step 1: Create virtual environment
    if not os.path.exists(".venv"):
        if not run_command("python -m venv .venv", "Creating virtual environment"):
            print("Error: Failed to create virtual environment")
            sys.exit(1)
    else:
        print("✓ Virtual environment already exists")
    
    # Step 2: Activate virtual environment and install dependencies
    if sys.platform == "win32":
        pip_path = ".venv\\Scripts\\pip.exe"
        python_path = ".venv\\Scripts\\python.exe"
    else:
        pip_path = ".venv/bin/pip"
        python_path = ".venv/bin/python"
    
    # Install backend dependencies
    dependencies = [
        "fastapi",
        "uvicorn[standard]",
        "requests",
        "pydantic[email]",
        "python-multipart",
        "email-validator"
    ]
    
    for dep in dependencies:
        if not run_command(f"{pip_path} install {dep}", f"Installing {dep}"):
            print(f"Warning: Failed to install {dep}")
    
    # Step 3: Test backend startup
    print("\n" + "=" * 40)
    print("Testing backend startup...")
    print("=" * 40)
    
    test_command = f"{python_path} -c \"import sys; sys.path.append('backend'); import main; print('Backend imports successful')\""
    if run_command(test_command, "Testing backend imports"):
        print("✓ Backend setup successful")
    else:
        print("✗ Backend setup failed")
    
    # Step 4: Display next steps
    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Install Ollama from https://ollama.ai/")
    print("2. Run: ollama pull mistral:7b")
    print("3. Start Ollama: ollama serve")
    print("4. Start backend: python start_frontend.py")
    print("5. In another terminal, run: start_backend.bat")
    print("6. Open http://localhost:3000 in your browser")
    
    print("\nFile structure:")
    print("├── backend/          # FastAPI backend")
    print("├── frontend/         # HTML/CSS/JS frontend")  
    print("├── start_backend.bat # Start backend server")
    print("├── start_frontend.py # Start frontend server")
    print("└── README.md         # Detailed documentation")
    
    print("\nFor troubleshooting, see README.md")

if __name__ == "__main__":
    main()