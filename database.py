import os
from typing import List, Tuple
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.documents = self.load_documents()
        self.embeddings = self.create_embeddings()

    def load_documents(self) -> List[Tuple[str, str]]:
        documents = []
        docs_dir = os.getenv('DOCUMENTS_DIR', './documents')
        for filename in os.listdir(docs_dir):
            if filename.endswith('.txt'):
                with open(os.path.join(docs_dir, filename), 'r') as f:
                    content = f.read()
                    # Store whole document content with filename as context
                    documents.append((filename, content))
        return documents

    def create_embeddings(self):
        embeddings = []
        for _, content in self.documents:
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=content
            )
            embeddings.append(response.data[0].embedding)
        return embeddings

    def search(self, query: str, k: int = 5) -> List[str]:
        query_embedding = self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=query
        ).data[0].embedding

        # Use cosine similarity
        similarities = cosine_similarity([query_embedding], self.embeddings)[0]
        top_k_indices = np.argsort(similarities)[-k:][::-1]
        
        results = []
        for i in top_k_indices:
            filename, content = self.documents[i]
            results.append(f"From {filename}: {content[:200]}...")  # Include filename and truncate long contents
        
        # Fallback: keyword matching
        if not any(query.lower() in result.lower() for result in results):
            for filename, content in self.documents:
                if query.lower() in content.lower():
                    results.append(f"Keyword match from {filename}: {content[:200]}...")
                    break

        return results

    def get_all_content(self) -> str:
        return "\n\n".join([f"From {filename}:\n{content}" for filename, content in self.documents])
