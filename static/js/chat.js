document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    function sendMessage() {
        const message = userInput.value.trim();
        if (message) {
            addMessageToChat('You', message);
            sendToServer(message);
            userInput.value = '';
        }
    }

    function addMessageToChat(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.innerHTML = `<strong>${sender}:</strong> ${message}`;
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
            addMessageToChat('AI', data.response);
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
