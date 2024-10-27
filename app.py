from flask import Flask, jsonify
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from database import Database
from logger import configure_logging
from path_config import PathConfig
from errors import ChatError
from session_manager import SessionManager
from routes.chat import init_chat_routes
from routes.files import init_file_routes
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

# Initialize core services
client = OpenAI(api_key=api_key)
db = Database()

# Configuration
app.config['UPLOAD_FOLDER'] = PathConfig.UPLOADS_DIR

if not os.path.exists(PathConfig.UPLOADS_DIR):
    os.makedirs(PathConfig.UPLOADS_DIR)

def load_config():
    default_config = {
        'employer_name': 'default',
        'company_logo': 'default_background.png'
    }
    try:
        with open('config.json', 'r') as f:
            return {**default_config, **json.load(f)}
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
            return {**default_candidate, **json.load(f)}
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

# Register blueprints
app.register_blueprint(init_chat_routes(session_manager, db, config, candidate_info))
app.register_blueprint(init_file_routes(app.config['UPLOAD_FOLDER']))

if __name__ == '__main__':
    print(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)