import os
from typing import List
import nltk
nltk.download('punkt', quiet=True)  # Download the punkt tokenizer data

def chunk_document(text: str, chunk_size: int = 100, overlap: int = 20) -> List[str]:
    """
    Split a document into overlapping chunks of approximately equal size.
    
    :param text: The input text to be chunked
    :param chunk_size: The target size of each chunk (in words)
    :param overlap: The number of words to overlap between chunks
    :return: A list of text chunks
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def load_and_chunk_documents(directory: str, chunk_size: int = 100, overlap: int = 20) -> List[str]:
    """
    Load documents from a directory, chunk them, and return a list of all chunks.
    
    :param directory: The directory containing the documents
    :param chunk_size: The target size of each chunk (in words)
    :param overlap: The number of words to overlap between chunks
    :return: A list of all document chunks
    """
    all_chunks = []
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            with open(os.path.join(directory, filename), 'r') as f:
                text = f.read()
                chunks = chunk_document(text, chunk_size, overlap)
                all_chunks.extend(chunks)
    return all_chunks
