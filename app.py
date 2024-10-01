import os
import logging
from flask import Flask, render_template, request, jsonify
from sentence_transformers import SentenceTransformer
import faiss
from openai import OpenAI
from document_utils import load_and_chunk_documents

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
PORT = int(os.environ.get('PORT', 5001))
HOST = '0.0.0.0'
DOCUMENTS_DIR = 'documents'
EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
CHUNK_SIZE = 200
CHUNK_OVERLAP = 50
TOP_K_CHUNKS = 3

# OpenAI client setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

# Load embedding model
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

# Load and chunk documents
document_chunks = load_and_chunk_documents(DOCUMENTS_DIR, CHUNK_SIZE, CHUNK_OVERLAP)
logger.info(f"Loaded {len(document_chunks)} chunks")

chunk_embeddings = embedding_model.encode(document_chunks)

# Create FAISS index
index = faiss.IndexFlatL2(chunk_embeddings.shape[1])
index.add(chunk_embeddings)

def get_answer_from_openai(question, context):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant answering questions based on the given context."},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}\n\nAnswer:"}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error in OpenAI API call: {e}")
        return "I'm sorry, I encountered an error while processing your question."

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json['message']
        logger.info(f"Received message: {user_message}")

        # Retrieve relevant document chunks
        query_embedding = embedding_model.encode([user_message])
        distances, indices = index.search(query_embedding, k=TOP_K_CHUNKS)
        logger.debug(f"Retrieved chunks: {indices[0]}, distances: {distances[0]}")
        
        relevant_chunks = [document_chunks[i] for i in indices[0]]
        logger.info(f"Found {len(relevant_chunks)} relevant chunks")

        if not relevant_chunks:
            return jsonify({'response': "I'm sorry, I couldn't find any relevant information to answer your question."})

        # Combine relevant chunks into a single context
        context = " ".join(relevant_chunks)
        logger.debug(f"Combined context: {context[:200]}...")

        # Get answer using OpenAI API
        answer = get_answer_from_openai(user_message, context)
        logger.info(f"Generated answer: {answer}")

        return jsonify({'response': answer})
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Server starting on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=True)
