from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import random
import string
from database import Database
from logger import log_session, log_interaction
from image_utils import get_background_image, get_color_scheme, setup_background_image, validate_image

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

DEFAULT_COLOR_SCHEME = {
    'dominant_color': '#000080',  # Navy blue
    'palette': ['#FFD700', '#FFFFFF', '#000080', '#8B4513', '#A52A2A']  # Gold, White, Navy, SaddleBrown, Brown
}

def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'employer_name': 'default'}

config = load_config()
EMPLOYER_NAME = config.get('employer_name', 'default')

def generate_unique_url():
    while True:
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        random_integer = random.randint(1000, 9999)
        unique_id = f"{EMPLOYER_NAME}-{random_string}{random_integer}"
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

    # Clear chat history for new sessions
    active_sessions[session_id]['chat_history'] = []

    log_session(session_id)

    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        background_image = config.get('company_logo', 'static/default_background.png')
        validate_image(background_image)
        background_image_filename = setup_background_image(app, background_image)
        background_image_url = url_for('uploaded_file', filename=background_image_filename)
        color_scheme = get_color_scheme(background_image)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(f"Error processing background image: {str(e)}")
        background_image_url = url_for('static', filename='default_background.png')
        color_scheme = DEFAULT_COLOR_SCHEME

    # Load candidate info
    try:
        with open('candidate_info.json', 'r') as f:
            candidate_info = json.load(f)
    except FileNotFoundError:
        candidate_info = {
            'linkedin_url': '',
            'video_url': '',
            'resume_url': ''
        }

    return render_template('chat.html',
                           session_id=session_id,
                           background_image_url=background_image_url,
                           color_scheme=color_scheme,
                           linkedin_url=candidate_info['linkedin_url'],
                           video_url=candidate_info['video_url'],
                           resume_url=candidate_info['resume_url'])

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
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)