from flask import Blueprint, jsonify, request, render_template, redirect, url_for
from errors import ChatError, SessionNotFoundError
from openai import APIError, RateLimitError, APIConnectionError
from ai_utils import get_answer_from_openai, get_initial_greeting
from image_utils import get_color_scheme, DEFAULT_COLOR_SCHEME
from logger import log_interaction
from path_config import PathConfig
import logging
import os

logger = logging.getLogger(__name__)

# Create blueprint
chat_bp = Blueprint('chat', __name__)


def init_chat_routes(session_manager, db, config, candidate_info):
    """Initialize chat routes with required dependencies"""

    @chat_bp.route('/')
    def home():
        try:
            session_id = session_manager.create_session()
            return redirect(url_for('chat.chat_session', session_id=session_id))
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise ChatError("Failed to create chat session")

    @chat_bp.route('/chat/<session_id>')
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

    @chat_bp.route('/api/chat', methods=['POST'])
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

    return chat_bp