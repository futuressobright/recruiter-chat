from flask import Flask, request, jsonify, render_template
from database import Database
import os
from openai import OpenAI
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
db = Database()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json['message']
        app.logger.info(f"Received message: {user_message}")

        relevant_chunks = db.search(user_message)
        app.logger.info(f"Found {len(relevant_chunks)} relevant chunks")

        if not relevant_chunks:
            return jsonify({'response': "I couldn't find relevant information for your question."})

        context = db.get_all_content()  # Provide full context
        app.logger.info(f"Context length: {len(context)}")

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4" if you have access
            messages=[
                {"role": "system", "content": f"You are an AI assistant answering questions based on the following context. Only use information from this context to answer questions: {context}"},
                {"role": "user", "content": user_message}
            ]
        )
        return jsonify({'response': response.choices[0].message.content})
    except Exception as e:
        app.logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
