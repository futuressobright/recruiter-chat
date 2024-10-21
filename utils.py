# utils.py

import random
import string
import json

def chunk_text(text, chunk_size=1000, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if end < len(text):
            last_space = chunk.rfind(' ')
            if last_space != -1:
                end = start + last_space
                chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks

def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'employer_name': 'default'}

def generate_unique_url(employer_name):
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    random_integer = random.randint(1000, 9999)
    return f"{employer_name}-{random_string}{random_integer}"

# Add any other utility functions here
