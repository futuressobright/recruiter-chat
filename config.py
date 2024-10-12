import os

PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'
DOCUMENTS_DIR = 'documents'
EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
TOP_K_CHUNKS = 5
FAISS_INDEX_PATH = 'faiss_index.joblib'
DOCUMENT_CHUNKS_PATH = 'document_chunks.joblib'
