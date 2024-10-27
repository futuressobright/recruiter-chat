from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
import json
import os
from openai import OpenAI
from openai import APIError, RateLimitError, APIConnectionError
from dotenv import load_dotenv
import random
import string
from database import Database
from logger import log_session, log_interaction, configure_logging
from image_utils import get_background_image, get_color_scheme, setup_background_image, validate_image
from ai_utils import get_answer_from_openai, get_initial_greeting
from path_config import PathConfig
import logging

# Load environment variables
load_dotenv()

# Validate required environment variables
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY must be set")

logtail_token = os.getenv('LOGTAIL_SOURCE_TOKEN')
if not logtail_token:
    raise ValueError("LOGTAIL_SOURCE_TOKEN must be set")

# Set up other environment variables with defaults
documents_dir = os.getenv('DOCUMENTS_DIR', './documents')
port = int(os.getenv('PORT', '8080'))

# Create documents directory if it doesn't exist
if not os.path.exists(documents_dir):
    os.makedirs(documents_dir)

# Initialize Flask app
app = Flask(__name__, static_url_path='/static')

# Setup logging
configure_logging(logtail_token)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Initialize Database
db = Database()

# Configuration
app.config['UPLOAD_FOLDER'] = PathConfig.UPLOADS_DIR

if not os.path.exists(PathConfig.UPLOADS_DIR):
    os.makedirs(PathConfig.UPLOADS_DIR)

DEFAULT_COLOR_SCHEME = {
    'dominant_color': '#007bff',
    'palette': ['#007bff', '#FFFFFF', '#f0f0f0', '#e0e0e0']
}


# Error handling classes
class ChatError(Exception):
    """Base exception class for chat application errors"""

    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class SessionNotFoundError(ChatError):
    """Raised when a session ID is not found"""

    def __init__(self, session_id):
        super().__init__(f"Session not found: {session_id}", status_code=404)


# Session management
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


def load_config():
    default_config = {
        'employer_name': 'default',
        'company_logo': 'default_background.png'
    }
    try:
        with open('config.json', 'r') as f:
            loaded_config = json.load(f)
            return {**default_config, **loaded_config}
    except FileNotFoundError:
        logger.warning("config.json not found, using default configuration")
        return default_config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config.json: {str(e)}")
        return default_config


def load_candidate_info():
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
        logger.warning("candidate_info.json not found, using default candidate info")
        return default_candidate
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in candidate_info.json: {str(e)}")
        return default_candidate


# Load configurations
config = load_config()
candidate_info = load_candidate_info()
session_manager = SessionManager(config['employer_name'])


@app.errorhandler(ChatError)
def handle_chat_error(error):
    response = jsonify({
        'error': error.message,
        'status_code': error.status_code
    })
    response.status_code = error.status_code
    return response


@app.route('/')
def home():
    try:
        session_id = session_manager.create_session()
        return redirect(url_for('chat_session', session_id=session_id))
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise ChatError("Failed to create chat session")


@app.route('/chat/<session_id>')
def chat_session(session_id):
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise SessionNotFoundError(session_id)

        session_manager.clear_history(session_id)

        # Generate initial AI greeting
        context = db.get_all_content()
        initial_greeting = get_initial_greeting(context)
        session_manager.add_message(session_id, "assistant", initial_greeting)

        try:
            background_image = os.path.basename(config['company_logo'])
            background_image_url = url_for('static', filename=PathConfig.get_static_url(background_image))
            image_path = PathConfig.get_full_path(background_image)
            color_scheme = get_color_scheme(image_path)
        except (ValueError, FileNotFoundError) as e:
            logger.warning(f"Error processing background image, using defaults: {str(e)}")
            background_image_url = url_for('static', filename=PathConfig.get_static_url('default_background.png'))
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
    except SessionNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error in chat session {session_id}: {str(e)}")
        raise ChatError("Failed to load chat session")


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        if not data:
            raise ChatError("No data provided", status_code=400)

        user_message = data.get('message')
        session_id = data.get('session_id')

        if not user_message or not session_id:
            raise ChatError("Missing required fields: message and session_id", status_code=400)

        if not session_manager.get_session(session_id):
            raise SessionNotFoundError(session_id)

        try:
            context = db.get_all_content()
            bot_message = get_answer_from_openai(user_message, context)
        except RateLimitError:
            raise ChatError("Service is temporarily busy. Please try again in a moment.", status_code=429)
        except APIConnectionError:
            raise ChatError("Unable to connect to AI service. Please try again.", status_code=503)
        except APIError as e:
            raise ChatError(f"AI service error: {str(e)}", status_code=500)

        session_manager.add_message(session_id, "user", user_message)
        session_manager.add_message(session_id, "assistant", bot_message)
        log_interaction(session_id, user_message, bot_message)

        return jsonify({'response': bot_message})

    except ChatError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        raise ChatError("An unexpected error occurred")


if __name__ == '__main__':
    print(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)