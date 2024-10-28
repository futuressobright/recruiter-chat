from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())
    applications = db.relationship('JobApplication', back_populates='user', cascade='all, delete-orphan')

class JobApplication(db.Model):
    __tablename__ = 'job_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_name = db.Column(db.String(255), nullable=False)
    company_logo_path = db.Column(db.String(255))
    candidate_video_url = db.Column(db.String(255))
    resume_url = db.Column(db.String(255))
    config = db.Column(JSONB)  # Stores the current config.json content
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())
    
    user = db.relationship('User', back_populates='applications')
    documents = db.relationship('ApplicationDocument', back_populates='application', cascade='all, delete-orphan')

class ApplicationDocument(db.Model):
    __tablename__ = 'application_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('job_applications.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.JSON)  # Store OpenAI embeddings
    created_at = db.Column(db.DateTime, server_default=func.now())
    
    application = db.relationship('JobApplication', back_populates='documents')
