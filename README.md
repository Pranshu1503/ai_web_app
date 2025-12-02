# PopQuiz - AI-Powered Quiz Generation System

A comprehensive web application for faculty to generate, manage, and export educational quizzes using AI technology.

## Current Status

- **Fully Functional**: All core features working
- **AI Integration**: Ollama/Mistral 7B for question generation
- **User Authentication**: Secure login and session management
- **Quiz Management**: Create, edit, save, and export quizzes
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Active Development**: Regular updates and improvements

## Features

### Authentication System

- **Email Verification**: 2-factor authentication with email confirmation
- Faculty and student signup with email verification
- Secure session management with JWT-like tokens
- Protected routes for all quiz operations
- Users must verify email before logging in
- Verification tokens expire after 24 hours

### AI-Powered Quiz Generation

- Generate questions based on specific topics
- Support for different cognitive levels (Bloom's Taxonomy)
- Multiple question types: Short Answer, MCQ, True/False
- Customizable number of questions
- Uses Ollama with Mistral 7B model for question generation

### Quiz Management

- Save generated quizzes with custom names
- View and edit existing quizzes
- Delete quizzes with confirmation
- Duplicate quizzes for reuse
- Real-time question editing
- Individual question regeneration

### Dashboard

- View all saved quizzes
- Search functionality across quiz names and topics
- Sort by creation/modification date
- Quick access to quiz actions (view, edit, duplicate, delete)

### Export Features

- Copy questions to clipboard
- Future support for PDF and Word export

## Technology Stack

### Backend

- **FastAPI**: Modern Python web framework
- **SQLite**: Lightweight database for user and quiz data
- **Ollama**: Local AI model integration for question generation
- **Pydantic**: Data validation and serialization
- **Uvicorn**: ASGI server

### Frontend

- **Vanilla HTML/CSS/JavaScript**: No framework dependencies
- **Modern CSS Grid/Flexbox**: Responsive design
- **Fetch API**: For backend communication
- **LocalStorage**: Client-side data management

## Prerequisites

1. **Python 3.8+**
2. **Ollama** with Mistral 7B model
   ```bash
   # Install Ollama first, then:
   ollama pull mistral:7b
   ```

## Quick Start

### Option 1: Automatic Setup (Recommended)

```bash
# Clone or download the project
cd ai_web_app

# Run the automated setup script
python setup.py

# Follow the on-screen instructions
```

### Option 2: Manual Setup

1. **Prerequisites**

   - Python 3.8+ installed
   - [Ollama](https://ollama.ai/) installed

2. **Install Ollama AI Model**

   ```bash
   ollama pull mistral:7b
   ollama serve  # Keep this running in background
   ```

3. **Setup Python Environment**

   ```bash
   # Create and activate virtual environment
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac

   # Install dependencies
   pip install -r backend/requirements.txt
   ```

4. **Configure Email Verification** (Required for signups)

   Set up environment variables for email verification:

   ```bash
   # For Gmail (recommended for testing)
   set SMTP_HOST=smtp.gmail.com
   set SMTP_PORT=587
   set SMTP_USERNAME=your-email@gmail.com
   set SMTP_PASSWORD=your-app-password
   set FRONTEND_URL=http://localhost:8001
   ```

   **Quick Setup**: Run `setup_email.bat` and follow the prompts

   📖 **Detailed instructions**: See [QUICK_START_EMAIL.md](QUICK_START_EMAIL.md)

5. **Run the Application**

   ```bash
   # Start backend (Terminal 1)
   start_backend.bat

   # Start frontend (Terminal 2)
   python start_frontend.py
   ```

6. **Access the App**
   - Open browser: `http://localhost:3000`
   - Click "FACULTY" to start using the system

## Usage

### Getting Started

1. Open the application and click "FACULTY" to access the system
2. Sign up for a new account or login with existing credentials
3. You'll be redirected to the dashboard

### Creating a Quiz

1. Click "CREATE NEW QUIZ" from the dashboard
2. Fill in the quiz parameters:
   - **Topic**: Subject matter (e.g., "Operating Systems", "Database Management")
   - **Cognitive Level**: Choose from Bloom's taxonomy levels
   - **Question Type**: Short Answer, MCQ, or True/False
   - **Number of Questions**: 1-20 questions
3. Click "GENERATE QUESTIONS" and wait for AI processing
4. Review and edit questions in the Quiz Editor

### Managing Questions

- **Edit**: Click the edit icon to modify question text
- **Regenerate**: Click the refresh icon to generate a new question
- **Add**: Use the "ADD QUESTION" button to manually add questions
- **Save**: Give your quiz a name and save it to the dashboard

### Dashboard Features

- **Search**: Use the search bar to find quizzes by name or topic
- **View/Edit**: Click to open a quiz in the editor
- **Duplicate**: Create a copy of an existing quiz
- **Delete**: Remove a quiz permanently (with confirmation)

## API Endpoints

### Authentication

- `POST /auth/signup` - Create new faculty account
- `POST /auth/login` - Login and get access token
- `POST /auth/logout` - Logout and invalidate token

### Quiz Generation

- `POST /generate_questions` - Generate questions using AI

### Quiz Management

- `GET /quizzes` - Get all user's quizzes
- `POST /quizzes` - Save a new quiz
- `GET /quizzes/{id}` - Get specific quiz details
- `PUT /quizzes/{id}` - Update existing quiz
- `DELETE /quizzes/{id}` - Delete a quiz
- `PUT /quizzes/{id}/questions` - Update individual question
- `POST /quizzes/{id}/duplicate` - Duplicate a quiz

## Database Schema

### Users Table

- `id`: Primary key
- `email`: Unique email address
- `password_hash`: Hashed password
- `created_at`: Account creation timestamp

### Sessions Table

- `token`: Session token (primary key)
- `user_id`: Reference to user
- `expires_at`: Token expiration

### Quizzes Table

- `id`: Primary key
- `user_id`: Reference to user
- `name`: Quiz name
- `topic`: Subject topic
- `bloom_level`: Cognitive level
- `question_type`: Type of questions
- `questions`: JSON array of questions
- `created_at`: Creation timestamp
- `updated_at`: Last modification timestamp

## Security Features

- Password hashing using SHA-256
- Session-based authentication with expiration
- CORS configuration for cross-origin requests
- Input validation using Pydantic models
- SQL injection protection via parameterized queries

## Error Handling

- Comprehensive error responses for API failures
- User-friendly error messages in the frontend
- Automatic session expiration handling
- Network error detection and reporting

## Future Enhancements

1. **Advanced Export Options**

   - PDF generation with custom formatting
   - Word document export
   - Bulk quiz export

2. **Question Bank**

   - Reusable question library
   - Question categorization and tagging
   - Import/export question banks

3. **Advanced AI Features**

   - Question difficulty scoring
   - Automatic answer key generation
   - Multiple AI model support

4. **Collaboration Features**

   - Quiz sharing between faculty
   - Team quiz creation
   - Quiz templates

5. **Analytics**
   - Quiz usage statistics
   - Question difficulty analytics
   - Export frequency tracking

## Troubleshooting

### Common Issues

1. **"Network error" when generating questions**

   - Ensure Ollama is running (`ollama serve`)
   - Verify Mistral 7B model is installed (`ollama pull mistral:7b`)
   - Check if backend server is running on port 8000

2. **"Session expired" errors**

   - Login again to get a new session token
   - Sessions expire after 7 days of inactivity

3. **Database errors**

   - The SQLite database (`popquiz.db`) is created automatically
   - Ensure the backend has write permissions in the directory

4. **CORS errors in browser**
   - Make sure the backend is running on the correct port (8000)
   - Try using a local server for the frontend instead of file:// protocol

## License

This project is open source and available under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the error messages in browser console
3. Ensure all prerequisites are properly installed
4. Verify Ollama and the backend server are running
