# path_config.py
import os

class PathConfig:
    STATIC_DIR = 'static'
    UPLOADS_DIR = os.path.join(STATIC_DIR, 'uploads')
    ASSETS_DIR = os.path.join(STATIC_DIR, 'assets')
    
    @classmethod
    def get_upload_path(cls, filename):
        return os.path.join(cls.UPLOADS_DIR, filename)
    
    @classmethod
    def get_static_url(cls, filename):
        return f'uploads/{filename}'
    
    @classmethod
    def get_full_path(cls, filename):
        return os.path.join(cls.STATIC_DIR, 'uploads', filename)
