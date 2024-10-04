import os
import logging
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'
DOCUMENTS_DIR = 'documents'
TOP_K_CHUNKS = 3

# OpenAI client setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

# Load documents
def load_documents(directory):
    documents = []
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            with open(os.path.join(directory, filename), 'r') as file:
                documents.append(file.read())
    return documents

documents = load_documents(DOCUMENTS_DIR)
logger.info(f"Loaded {len(documents)} documents")

def get_relevant_context(query, documents, top_k=3):
    # Simple relevance scoring based on word overlap
    relevant_docs = sorted(documents, key=lambda doc: len(set(query.lower().split()) & set(doc.lower().split())), reverse=True)
    return " ".join(relevant_docs[:top_k])

def get_answer_from_openai(question, context):
    try:
        logger.debug(f"Calling OpenAI API with question: {question} and context: {context[:100]}...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant answering questions based on the given context."},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}\n\nAnswer:"}
            ],
            max_tokens=150
        )
        answer = response.choices[0].message.content.strip()
        logger.debug(f"Received answer from OpenAI: {answer[:100]}...")
        return answer
    except Exception as e:
        logger.error(f"Error in OpenAI API call: {e}")
        return f"I'm sorry, I encountered an error while processing your question: {str(e)}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json['message']
        logger.info(f"Received message: {user_message}")

        # Get relevant context
        context = get_relevant_context(user_message, documents, TOP_K_CHUNKS)
        logger.debug(f"Selected context: {context[:200]}...")

        # Get answer using OpenAI API
        answer = get_answer_from_openai(user_message, context)
        logger.info(f"Generated answer: {answer}")

        return jsonify({'response': answer})
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Server starting on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)
