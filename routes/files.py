from flask import Blueprint, send_from_directory

files_bp = Blueprint('files', __name__)

def init_file_routes(upload_folder):
    """Initialize file-related routes"""
    
    @files_bp.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(upload_folder, filename)
        
    return files_bp
