from txtai.embeddings import Embeddings
import os
from typing import List

class Database:
    def __init__(self):
        self.embeddings = Embeddings({"path": "sentence-transformers/all-MiniLM-L6-v2"})
        self.document_chunks = self.load_documents()
        self.index = self.create_index()

    def load_documents(self) -> List[str]:
        documents = []
        docs_dir = os.getenv('DOCUMENTS_DIR', './documents')
        for filename in os.listdir(docs_dir):
            if filename.endswith('.txt'):
                with open(os.path.join(docs_dir, filename), 'r') as f:
                    documents.extend(f.read().split('\n\n'))
        return documents

    def create_index(self):
        return self.embeddings.index([(str(i), text, None) for i, text in enumerate(self.document_chunks)])

    def search(self, query: str, k: int = 3) -> List[str]:
        results = self.embeddings.search(query, k)
        return [self.document_chunks[int(uid)] for uid, _ in results]
