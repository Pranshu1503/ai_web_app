// Simple JavaScript for testing the EduAI backend API

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('questionForm');
    const generateBtn = document.getElementById('generateBtn');
    const questionsList = document.getElementById('questionsList');
    const statusMessage = document.getElementById('statusMessage');

    // Update status message
    function updateStatus(message, isError = false) {
        statusMessage.textContent = message;
        statusMessage.style.color = isError ? '#e53e3e' : '#2b6cb0';
    }

    // Show loading state
    function setLoading(loading) {
        generateBtn.disabled = loading;
        if (loading) {
            generateBtn.innerHTML = '<div class="loading"></div>Generating...';
            updateStatus('Generating questions...');
        } else {
            generateBtn.innerHTML = 'Generate Questions';
        }
    }

    // Display questions
    function displayQuestions(questions) {
        questionsList.innerHTML = '';

        if (questions.length === 0) {
            questionsList.innerHTML = '<p>No questions generated.</p>';
            return;
        }

        questions.forEach((question, index) => {
            const questionDiv = document.createElement('div');
            questionDiv.className = 'question-item';

            questionDiv.innerHTML = `
                <div class="question-number">${index + 1}.</div>
                <div class="question-text">${question}</div>
            `;

            questionsList.appendChild(questionDiv);
        });
    }

    // Handle form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const subject = document.getElementById('subject').value;
        const numQuestions = parseInt(document.getElementById('numQuestions').value);

        setLoading(true);

        try {
            const response = await fetch('http://localhost:8000/generate_questions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    subject: subject,
                    num_questions: numQuestions
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.questions && Array.isArray(data.questions)) {
                displayQuestions(data.questions);
                updateStatus(`Successfully generated ${data.questions.length} questions!`);
            } else {
                throw new Error('Invalid response format');
            }

        } catch (error) {
            console.error('Error:', error);
            updateStatus(`Error: ${error.message}`, true);
            questionsList.innerHTML = '<p style="color: #e53e3e;">Failed to generate questions. Make sure the backend server is running.</p>';
        } finally {
            setLoading(false);
        }
    });

    // Initial status
    updateStatus('Ready to test the EduAI backend!');
});