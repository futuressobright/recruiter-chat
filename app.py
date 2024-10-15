from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
from database import Database
import os
from openai import OpenAI
from dotenv import load_dotenv
import random
import string
from logger import log_session, log_interaction
from image_utils import get_background_image, get_color_scheme, setup_background_image, validate_image

DEFAULT_COLOR_SCHEME = {
    'dominant_color': '#FFFFFF',
    'palette': ['#000000', '#333333', '#666666', '#999999', '#CCCCCC']
}

load_dotenv()

app = Flask(__name__)
db = Database()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Dictionary to store active sessions
active_sessions = {}

# Configuration
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def generate_unique_url():
    while True:
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        random_integer = random.randint(1000, 9999)
        unique_id = f"{random_string}-{random_integer}"
        if unique_id not in active_sessions:
            return unique_id


@app.route('/')
def home():
    unique_id = generate_unique_url()
    active_sessions[unique_id] = {"chat_history": []}
    return redirect(url_for('chat_session', session_id=unique_id))


@app.route('/chat/<session_id>')
def chat_session(session_id):
    if session_id not in active_sessions:
        return f"Invalid session: {session_id}", 404

    log_session(session_id)

    try:
        background_image = get_background_image()
        validate_image(background_image)  # Additional validation
        background_image_filename = setup_background_image(app, background_image)
        background_image_url = url_for('uploaded_file', filename=background_image_filename)
        color_scheme = get_color_scheme(background_image)
    except ValueError as e:
        # Log the error
        print(f"Error processing background image: {str(e)}")
        # Use a default background and color scheme
        background_image_url = url_for('static', filename='default_background.jpg')
        color_scheme = {
            'dominant_color': '#FFFFFF',
            'palette': ['#000000', '#333333', '#666666', '#999999', '#CCCCCC']
        }

    return render_template('chat.html',
                           session_id=session_id,
                           background_image_url=background_image_url,
                           color_scheme=color_scheme)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data['message']
        session_id = data['session_id']

        if session_id not in active_sessions:
            return jsonify({"error": "Invalid session"}), 400

        relevant_chunks = db.search(user_message)

        if not relevant_chunks:
            return jsonify({'response': "I couldn't find relevant information for your question."})

        context = db.get_all_content()

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": f"You are an AI assistant answering questions based on the following context. Only use information from this context to answer questions: {context}"},
                {"role": "user", "content": user_message}
            ]
        )

        bot_message = response.choices[0].message.content

        # Add messages to chat history
        active_sessions[session_id]['chat_history'].append({"role": "user", "content": user_message})
        active_sessions[session_id]['chat_history'].append({"role": "assistant", "content": bot_message})

        log_interaction(session_id, user_message, bot_message)

        return jsonify({'response': bot_message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=True)