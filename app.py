from flask import Flask, jsonify, g, request, session, Response
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass
import os
from openai import OpenAI
from dotenv import load_dotenv
from logger import configure_logging
from path_config import PathConfig
from errors import ChatError, ConfigurationError
import logging
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db, User, JobApplication, ApplicationDocument
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from functools import wraps

# Type definitions
JSONType = Dict[str, Any]
RouteResponse = Tuple[Union[Response, JSONType], int]


class ApplicationError(ChatError):
    """Application-specific errors"""
    pass


class AuthenticationError(ChatError):
    """Authentication-related errors"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class AuthorizationError(ChatError):
    """Authorization-related errors"""

    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, status_code=403)


class ValidationError(ChatError):
    """Input validation errors"""

    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, status_code=400)


@dataclass
class AppConfig:
    """Application configuration container"""
    api_key: str
    logtail_token: str
    database_url: str
    upload_folder: str
    secret_key: str
    port: int
    allowed_extensions: set
    max_content_length: int


def load_configuration() -> AppConfig:
    """Load and validate all application configuration"""
    load_dotenv()

    required_vars = {
        'OPENAI_API_KEY': 'API key is required for OpenAI integration',
        'LOGTAIL_SOURCE_TOKEN': 'Logtail token is required for logging',
        'DATABASE_URL': 'Database URL is required'
    }

    missing_vars = [var for var, msg in required_vars.items() if not os.getenv(var)]
    if missing_vars:
        raise ConfigurationError(f"Missing required environment variables: {', '.join(missing_vars)}")

    return AppConfig(
        api_key=os.getenv('OPENAI_API_KEY'),
        logtail_token=os.getenv('LOGTAIL_SOURCE_TOKEN'),
        database_url=os.getenv('DATABASE_URL'),
        upload_folder=PathConfig.UPLOADS_DIR,
        secret_key=os.getenv('FLASK_SECRET_KEY', 'default-dev-key'),
        port=int(os.getenv('PORT', '8080')),
        allowed_extensions={'txt', 'pdf', 'doc', 'docx'},
        max_content_length=10 * 1024 * 1024  # 10MB
    )


class ChatService:
    """Handle chat-related operations"""

    def __init__(self, client: OpenAI):
        self.client = client
        self.logger = logging.getLogger(__name__)

    def create_embeddings(self, text: str) -> List[float]:
        """Create embeddings for text using OpenAI API"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"Error creating embedding: {str(e)}")
            raise ChatError(f"Failed to create embedding: {str(e)}")

    def get_chat_response(self, company_name: str, context: str, message: str) -> str:
        """Get chat completion from OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system",
                     "content": f"You are a chat assistant for {company_name}. Use the following context for your responses: {context}"},
                    {"role": "user", "content": message}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Chat completion error: {str(e)}")
            raise ChatError(f"Failed to get chat response: {str(e)}")


def create_app(test_config: Optional[AppConfig] = None) -> Flask:
    """Application factory function"""
    config = test_config or load_configuration()

    app = Flask(__name__, static_url_path='/static')

    # Configure app
    app.config.update(
        SQLALCHEMY_DATABASE_URI=config.database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=config.upload_folder,
        SECRET_KEY=config.secret_key,
        MAX_CONTENT_LENGTH=config.max_content_length
    )

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)

    # Setup logging
    configure_logging(config.logtail_token)
    logger = logging.getLogger(__name__)

    # Initialize OpenAI client
    client = OpenAI(api_key=config.api_key)
    chat_service = ChatService(client)

    # Ensure upload directory exists
    os.makedirs(config.upload_folder, exist_ok=True)

    def get_current_user() -> Optional[User]:
        """Get currently logged in user from session"""
        if 'user_id' not in session:
            return None
        return User.query.get(session['user_id'])

    def verify_application_owner(application_id: int) -> JobApplication:
        """Verify application ownership and return application"""
        application = JobApplication.query.get_or_404(application_id)
        if application.user_id != g.user.id:
            raise AuthorizationError("Not authorized to access this application")
        return application

    def login_required(f):
        """Decorator to require authentication"""

        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            if not g.user:
                raise AuthenticationError()
            return f(*args, **kwargs)

        return decorated_function

    def validate_file(file) -> None:
        """Validate uploaded file"""
        if not file:
            raise ValidationError("No file provided")
        if file.filename == '':
            raise ValidationError("No file selected")
        if not allowed_file(file.filename, config.allowed_extensions):
            raise ValidationError("File type not allowed")

    def allowed_file(filename: str, allowed_extensions: set) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in allowed_extensions

    # Request hooks
    @app.before_request
    def before_request() -> None:
        g.user = get_current_user()

    # Error handlers
    @app.errorhandler(ChatError)
    def handle_chat_error(error: ChatError) -> RouteResponse:
        logger.error(f"Chat error: {error.message}")
        return jsonify({'error': error.message}), error.status_code

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error: SQLAlchemyError) -> RouteResponse:
        logger.error(f"Database error: {str(error)}")
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> RouteResponse:
        logger.error(f"HTTP error: {str(error)}")
        return jsonify({'error': str(error)}), error.code

    @app.errorhandler(Exception)
    def handle_generic_error(error: Exception) -> RouteResponse:
        logger.error(f"Unexpected error: {str(error)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

    # Routes
    @app.route('/api/applications', methods=['GET'])
    @login_required
    def list_applications() -> RouteResponse:
        """List all applications for current user"""
        applications = JobApplication.query.filter_by(user_id=g.user.id).all()
        return jsonify([{
            'id': app.id,
            'company_name': app.company_name,
            'created_at': app.created_at.isoformat()
        } for app in applications]), 200

    @app.route('/api/applications', methods=['POST'])
    @login_required
    def create_application() -> RouteResponse:
        """Create a new job application"""
        data = request.get_json()
        if not data or 'company_name' not in data:
            raise ValidationError("Company name is required")

        app_instance = JobApplication(
            user_id=g.user.id,
            company_name=data['company_name'],
            config=data.get('config', {})
        )

        try:
            db.session.add(app_instance)
            db.session.commit()
            return jsonify({
                'id': app_instance.id,
                'company_name': app_instance.company_name
            }), 201
        except IntegrityError:
            db.session.rollback()
            raise ValidationError("Application already exists for this company")

    @app.route('/api/applications/<int:application_id>', methods=['GET'])
    @login_required
    def get_application_details(application_id: int) -> RouteResponse:
        """Get details of a specific application"""
        app_instance = verify_application_owner(application_id)
        return jsonify({
            'id': app_instance.id,
            'company_name': app_instance.company_name,
            'company_logo_path': app_instance.company_logo_path,
            'candidate_video_url': app_instance.candidate_video_url,
            'resume_url': app_instance.resume_url,
            'config': app_instance.config
        }), 200

    @app.route('/api/applications/<int:application_id>/documents', methods=['POST'])
    @login_required
    def upload_document(application_id: int) -> RouteResponse:
        """Upload a document for a specific application"""
        app_instance = verify_application_owner(application_id)

        if 'file' not in request.files:
            raise ValidationError("No file part in request")

        file = request.files['file']
        validate_file(file)

        filename = secure_filename(file.filename)
        content = file.read().decode('utf-8')

        try:
            embedding = chat_service.create_embeddings(content)

            document = ApplicationDocument(
                application_id=application_id,
                file_name=filename,
                content=content,
                embedding=embedding
            )

            db.session.add(document)
            db.session.commit()

            return jsonify({
                'id': document.id,
                'file_name': document.file_name
            }), 201
        except UnicodeDecodeError:
            raise ValidationError("File must be a valid text document")

    @app.route('/api/chat', methods=['POST'])
    @login_required
    def chat() -> RouteResponse:
        """Handle chat interactions"""
        data = request.get_json()
        if not data or not all(k in data for k in ['application_id', 'message']):
            raise ValidationError("Missing required fields")

        app_instance = verify_application_owner(data['application_id'])

        documents = ApplicationDocument.query.filter_by(
            application_id=app_instance.id
        ).all()

        if not documents:
            raise ValidationError("No documents available for this application")

        context = "\n\n".join(doc.content for doc in documents)

        try:
            response = chat_service.get_chat_response(
                app_instance.company_name,
                context,
                data['message']
            )
            return jsonify({'response': response}), 200
        except ChatError as e:
            logger.error(f"Chat error: {str(e)}")
            return jsonify({'error': str(e)}), 500

    return app


def run_app() -> None:
    """Run the application"""
    config = load_configuration()
    app = create_app(config)
    print(f"Starting application on port {config.port}")
    app.run(host='0.0.0.0', port=config.port, debug=True, use_reloader=False)


if __name__ == '__main__':
    run_app()