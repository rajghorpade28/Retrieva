import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
import pickle
import os

class VectorStore:
    def __init__(self, session_id=None):
        # Load the embedding model (small and fast)
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        if session_id:
            self.storage_dir = os.path.join("vector_store_data", session_id)
            os.makedirs(self.storage_dir, exist_ok=True)
            self.index_path = os.path.join(self.storage_dir, "index.faiss")
            self.metadata_path = os.path.join(self.storage_dir, "metadata.pkl")
        else:
            self.index_path = "index.faiss"
            self.metadata_path = "metadata.pkl"
        
        self.index = None
        self.metadata = [] # List of dicts: {"text": str, "source": str}
        
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            self.load()
        else:
            # Embedding dimension for all-MiniLM-L6-v2 is 384
            self.index = faiss.IndexFlatL2(384)

    def add_documents(self, chunks: list[str], source: str):
        """Encodes chunks and adds them to the FAISS index."""
        if not chunks:
            return
            
        embeddings = self.encoder.encode(chunks)
        self.index.add(np.array(embeddings).astype('float32'))
        
        # Add metadata for each chunk
        new_metadata = [{"text": chunk, "source": source} for chunk in chunks]
        self.metadata.extend(new_metadata)
        
        self.save()

    def search(self, query: str, k: int = 3):
        """Searches the index for the most descriptive chunks."""
        query_vec = self.encoder.encode([query])
        distances, indices = self.index.search(np.array(query_vec).astype('float32'), k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                results.append({
                    "chunk": self.metadata[idx]["text"],
                    "source": self.metadata[idx]["source"],
                    "distance": float(distances[0][i])
                })
        return results

    def save(self):
        """Persists the index and metadata to disk."""
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)

    def load(self):
        """Loads the index and metadata from disk."""
        self.index = faiss.read_index(self.index_path)
        with open(self.metadata_path, 'rb') as f:
            self.metadata = pickle.load(f)

    def clear(self):
        """Clears the index and metadata."""
        self.index = faiss.IndexFlatL2(384)
        self.metadata = []
        self.save()
