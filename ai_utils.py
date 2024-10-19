from openai import OpenAI
from timing_utils import timed_operation
import os
import logging

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

@timed_operation("OpenAI API call")
def get_answer_from_openai(question, context, is_initial_greeting=False):
    try:
        if is_initial_greeting:
            system_content = "You are an AI assistant for a recruiter. Start with a brief, friendly greeting and ask how you can help. Use the provided context for information if needed."
            user_content = "Start the conversation"
        else:
            system_content = "You are a helpful assistant answering questions based on the given context."
            user_content = f"Context: {context}\n\nQuestion: {question}\n\nAnswer:"

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error in OpenAI API call: {e}")
        return "I'm sorry, I encountered an error while processing your request."

def get_initial_greeting(context):
    return get_answer_from_openai("", context, is_initial_greeting=True)