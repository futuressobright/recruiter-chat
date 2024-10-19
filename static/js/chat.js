document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    // Display initial greeting if it exists
    if (initialGreeting && initialGreeting.trim() !== "") {
        addMessageToChat('AI', initialGreeting, 'bot-message');
    }

    function sendMessage() {
        const message = userInput.value.trim();
        if (message) {
            addMessageToChat('You', message, 'user-message');
            sendToServer(message);
            userInput.value = '';
        }
    }

    function addMessageToChat(sender, message, className) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${className}`;
        if (sender === 'AI') {
            messageElement.innerHTML = `<strong>${sender}:</strong> ${message}`;
        } else {
            messageElement.textContent = message;  // No "You:" prefix for user messages
        }
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function sendToServer(message) {
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: window.location.pathname.split('/').pop()
            }),
        })
        .then(response => response.json())
        .then(data => {
            addMessageToChat('AI', data.response, 'bot-message');
        })
        .catch((error) => {
            console.error('Error:', error);
            addMessageToChat('System', 'An error occurred while processing your request.', 'error-message');
        });
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});