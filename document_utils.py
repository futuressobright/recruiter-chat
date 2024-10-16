import os
from typing import List
import nltk
nltk.download('punkt', quiet=True)  # Download the punkt tokenizer data

def chunk_document(text: str, chunk_size: int = 5, overlap: int = 1) -> List[str]:
    sentences = sent_tokenize(text)
    chunks = []
    for i in range(0, len(sentences), chunk_size - overlap):
        chunk = ' '.join(sentences[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def load_and_chunk_documents(directory: str, chunk_size: int = 5, overlap: int = 1) -> List[dict]:
    all_chunks = []
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            with open(os.path.join(directory, filename), 'r') as f:
                text = f.read()
                chunks = chunk_document(text, chunk_size, overlap)
                for i, chunk in enumerate(chunks):
                    all_chunks.append({
                        'text': chunk,
                        'source': filename,
                        'chunk_index': i
                    })
    return all_chunks
