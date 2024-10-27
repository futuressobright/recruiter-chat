import os
from typing import List, Tuple, Dict
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
import pickle
from pathlib import Path
import hashlib
import json

load_dotenv()


class Database:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.cache_dir = Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.documents = {}  # Changed to dict for easier lookup
        self.load_documents()
        self.embeddings = self.load_or_create_embeddings()

    def load_documents(self) -> None:
        docs_dir = os.getenv('DOCUMENTS_DIR', './documents')
        for filename in os.listdir(docs_dir):
            if filename.endswith('.txt'):
                with open(os.path.join(docs_dir, filename), 'r') as f:
                    content = f.read()
                    self.documents[filename] = content

    def _get_document_hash(self, content: str) -> str:
        """Create a hash of a single document's content"""
        return hashlib.md5(content.encode()).hexdigest()

    def _get_documents_hashes(self) -> Dict[str, str]:
        """Create hashes for all documents"""
        return {
            filename: self._get_document_hash(content)
            for filename, content in self.documents.items()
        }

    def load_or_create_embeddings(self):
        embeddings_cache = self.cache_dir / "embeddings.pkl"
        hashes_cache = self.cache_dir / "document_hashes.json"
        embeddings_map_cache = self.cache_dir / "embeddings_map.json"

        current_hashes = self._get_documents_hashes()
        cached_hashes = {}
        embeddings_map = {}
        cached_embeddings = []

        # Load cached data if it exists
        if all(f.exists() for f in [embeddings_cache, hashes_cache, embeddings_map_cache]):
            print("Loading cached data...")
            with open(hashes_cache, "r") as f:
                cached_hashes = json.load(f)
            with open(embeddings_map_cache, "r") as f:
                embeddings_map = json.load(f)
            with open(embeddings_cache, "rb") as f:
                cached_embeddings = pickle.load(f)

        # Determine which documents need updating
        files_to_update = []
        files_to_keep = []

        for filename, current_hash in current_hashes.items():
            if filename not in cached_hashes or cached_hashes[filename] != current_hash:
                print(f"Document changed or new: {filename}")
                files_to_update.append(filename)
            else:
                files_to_keep.append(filename)

        # Remove deleted files from tracking
        deleted_files = set(cached_hashes.keys()) - set(current_hashes.keys())
        if deleted_files:
            print(f"Deleted files: {deleted_files}")

        if not files_to_update and not deleted_files:
            print("No documents changed, using cached embeddings")
            return cached_embeddings

        # Keep existing embeddings for unchanged files
        updated_embeddings = []
        updated_map = {}
        current_idx = 0

        # Keep embeddings for unchanged files
        for filename in files_to_keep:
            if filename in embeddings_map:
                old_idx = embeddings_map[filename]
                updated_embeddings.append(cached_embeddings[old_idx])
                updated_map[filename] = current_idx
                current_idx += 1

        # Create new embeddings only for changed/new files
        print(f"Creating embeddings for {len(files_to_update)} documents")
        for filename in files_to_update:
            print(f"Processing: {filename}")
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=self.documents[filename]
            )
            updated_embeddings.append(response.data[0].embedding)
            updated_map[filename] = current_idx
            current_idx += 1

        # Save updated caches
        print("Saving updated caches...")
        with open(embeddings_cache, "wb") as f:
            pickle.dump(updated_embeddings, f)
        with open(hashes_cache, "w") as f:
            json.dump(current_hashes, f)
        with open(embeddings_map_cache, "w") as f:
            json.dump(updated_map, f)

        return updated_embeddings

    def search(self, query: str, k: int = 5) -> List[str]:
        query_embedding = self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=query
        ).data[0].embedding

        similarities = cosine_similarity([query_embedding], self.embeddings)[0]
        top_k_indices = np.argsort(similarities)[-k:][::-1]

        # Convert documents dict back to list format for search results
        doc_items = list(self.documents.items())
        results = []
        for i in top_k_indices:
            filename, content = doc_items[i]
            results.append(f"From {filename}: {content[:200]}...")

        return results

    def get_all_content(self) -> str:
        return "\n\n".join([f"From {filename}:\n{content}"
                            for filename, content in self.documents.items()])