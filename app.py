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
from ai_utils import get_answer_from_openai, get_initial_greeting

load_dotenv()


class SessionManager:
    def __init__(self, employer_name):
        self.sessions = {}
        self.employer_name = employer_name

    def generate_unique_id(self):
        while True:
            random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            random_integer = random.randint(1000, 9999)
            unique_id = f"{self.employer_name}-{random_string}{random_integer}"
            if unique_id not in self.sessions:
                return unique_id

    def create_session(self):
        session_id = self.generate_unique_id()
        self.sessions[session_id] = {"chat_history": []}
        log_session(session_id)
        return session_id

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def add_message(self, session_id, role, content):
        if session_id in self.sessions:
            self.sessions[session_id]['chat_history'].append({"role": role, "content": content})

    def clear_history(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id]['chat_history'] = []


app = Flask(__name__, static_url_path='/static')
db = Database()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuration
UPLOAD_FOLDER = 'images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DEFAULT_COLOR_SCHEME = {
    'dominant_color': '#000080',  # Navy blue
    'palette': ['#FFD700', '#FFFFFF', '#000080', '#8B4513', '#A52A2A']  # Gold, White, Navy, SaddleBrown, Brown
}


def load_config():
    """Load configuration with consistent defaults for all required settings."""
    default_config = {
        'employer_name': 'default',
        'company_logo': 'default_background.png'
    }
    try:
        with open('config.json', 'r') as f:
            loaded_config = json.load(f)
            return {**default_config, **loaded_config}
    except FileNotFoundError:
        return default_config


def load_candidate_info():
    """Load candidate information with consistent defaults."""
    default_candidate = {
        'first_name': 'Candidate',
        'linkedin_url': '',
        'video_url': '',
        'resume_url': ''
    }
    try:
        with open('candidate_info.json', 'r') as f:
            loaded_info = json.load(f)
            return {**default_candidate, **loaded_info}
    except FileNotFoundError:
        return default_candidate


# Load configurations at startup
config = load_config()
candidate_info = load_candidate_info()
session_manager = SessionManager(config['employer_name'])


@app.route('/')
def home():
    session_id = session_manager.create_session()
    return redirect(url_for('chat_session', session_id=session_id))


app.static_folder = 'static'


@app.route('/chat/<session_id>')
def chat_session(session_id):
    session = session_manager.get_session(session_id)
    if not session:
        return f"Invalid session: {session_id}", 404

    session_manager.clear_history(session_id)

    # Generate initial AI greeting
    context = db.get_all_content()
    initial_greeting = get_initial_greeting(context)
    session_manager.add_message(session_id, "assistant", initial_greeting)

    try:
        background_image = os.path.basename(config['company_logo'])
        background_image_url = url_for('static', filename=f'images/{background_image}')
        image_path = os.path.join(app.static_folder, 'images', background_image)
        color_scheme = get_color_scheme(image_path)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error processing background image: {str(e)}")
        background_image_url = url_for('static', filename='images/default_background.png')
        color_scheme = DEFAULT_COLOR_SCHEME

    return render_template('chat.html',
                           session_id=session_id,
                           background_image_url=background_image_url,
                           color_scheme=color_scheme,
                           first_name=candidate_info['first_name'],
                           linkedin_url=candidate_info['linkedin_url'],
                           video_url=candidate_info['video_url'],
                           resume_url=candidate_info['resume_url'],
                           initial_greeting=initial_greeting)


@app.route('/images/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data['message']
        session_id = data['session_id']

        if not session_manager.get_session(session_id):
            return jsonify({"error": "Invalid session"}), 400

        context = db.get_all_content()
        bot_message = get_answer_from_openai(user_message, context)

        # Add messages to chat history
        session_manager.add_message(session_id, "user", user_message)
        session_manager.add_message(session_id, "assistant", bot_message)

        log_interaction(session_id, user_message, bot_message)

        return jsonify({'response': bot_message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)