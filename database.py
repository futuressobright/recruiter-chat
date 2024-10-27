import os
from typing import List, Tuple
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
import pickle
from pathlib import Path

load_dotenv()


class Database:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.cache_dir = Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.documents = self.load_documents()
        self.embeddings = self.load_or_create_embeddings()

    def load_documents(self) -> List[Tuple[str, str]]:
        documents = []
        docs_dir = os.getenv('DOCUMENTS_DIR', './documents')
        for filename in os.listdir(docs_dir):
            if filename.endswith('.txt'):
                with open(os.path.join(docs_dir, filename), 'r') as f:
                    content = f.read()
                    documents.append((filename, content))
        return documents

    def load_or_create_embeddings(self):
        embeddings_cache = self.cache_dir / "embeddings.pkl"

        # Try to load cached embeddings
        if embeddings_cache.exists():
            print("Loading embeddings from cache...")
            with open(embeddings_cache, "rb") as f:
                return pickle.load(f)

        # Create new embeddings if cache doesn't exist
        print("Creating new embeddings...")
        embeddings = []
        for _, content in self.documents:
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=content
            )
            embeddings.append(response.data[0].embedding)

        # Cache the embeddings
        print("Caching embeddings for future use...")
        with open(embeddings_cache, "wb") as f:
            pickle.dump(embeddings, f)

        return embeddings

    def search(self, query: str, k: int = 5) -> List[str]:
        query_embedding = self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=query
        ).data[0].embedding

        similarities = cosine_similarity([query_embedding], self.embeddings)[0]
        top_k_indices = np.argsort(similarities)[-k:][::-1]

        results = []
        for i in top_k_indices:
            filename, content = self.documents[i]
            results.append(f"From {filename}: {content[:200]}...")

        return results

    def get_all_content(self) -> str:
        return "\n\n".join([f"From {filename}:\n{content}" for filename, content in self.documents])