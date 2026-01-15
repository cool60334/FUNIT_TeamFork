"""
Custom Embedding Function for ChromaDB using EmbeddingGemma-300m
https://huggingface.co/google/embeddinggemma-300m
"""

from typing import List
import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except Exception:
    pass  # dotenv not installed or load failure; rely on system env vars

# Load HuggingFace token from environment
HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")


class EmbeddingGemmaFunction:
    """
    Custom embedding function using Google's EmbeddingGemma-300m model.
    This model produces 768-dimensional embeddings optimized for retrieval tasks.
    
    Compatible with both ChromaDB and LanceDB.
    """
    
    def __init__(self, model_name: str = "google/embeddinggemma-300m"):
        """
        Initialize the embedding function.
        
        Args:
            model_name: HuggingFace model identifier
        """
        from sentence_transformers import SentenceTransformer
        
        self._model_name = model_name
        
        # Load model with HuggingFace token if available
        print(f"Loading embedding model: {model_name}")
        
        if HF_TOKEN:
            self.model = SentenceTransformer(model_name, token=HF_TOKEN, device='cpu')
        else:
            self.model = SentenceTransformer(model_name, device='cpu')
        
        print(f"✅ EmbeddingGemma loaded successfully (dim: {self.model.get_sentence_embedding_dimension()}) on CPU")
    
    def name(self) -> str:
        """Return the name of this embedding function (required by ChromaDB)."""
        return "embedding_gemma_300m"
    
    def dimension(self) -> int:
        """Return the embedding dimension (required by ChromaDB)."""
        return self.model.get_sentence_embedding_dimension()
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of documents.
        ChromaDB expects this signature.
        
        Args:
            input: List of text strings to embed
            
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        embeddings = self.model.encode(input)
        return embeddings.tolist()
    
    def embed_query(self, input: List[str]) -> List[List[float]]:
        """
        Embed query texts (used by ChromaDB for querying).
        EmbeddingGemma uses encode_query for queries.
        """
        # EmbeddingGemma has special query encoding
        try:
            embeddings = self.model.encode_query(input)
        except:
            embeddings = self.model.encode(input)
        return embeddings.tolist() if hasattr(embeddings, 'tolist') else [embeddings.tolist()]
    
    def embed_document(self, input: List[str]) -> List[List[float]]:
        """
        Embed document texts (used by ChromaDB for adding documents).
        EmbeddingGemma uses encode_document for documents.
        """
        # EmbeddingGemma has special document encoding
        try:
            embeddings = self.model.encode_document(input)
        except:
            embeddings = self.model.encode(input)
        return embeddings.tolist()


class FallbackEmbeddingFunction:
    """
    Fallback embedding function using deterministic hashing.
    Used when sophisticated models are not available.
    """
    def __init__(self, dim: int = 768):
        self._dim = dim

    def name(self) -> str:
        return "fallback_hash_768"

    def dimension(self) -> int:
        return self._dim

    def _hash_text(self, text: str) -> List[float]:
        """Generate a pseudo-random deterministic vector from text."""
        import hashlib
        import random
        
        # Use SHA256 of text as seed
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        seed_int = int(hash_obj.hexdigest(), 16)
        
        # Seeding random generator for determinism
        rng = random.Random(seed_int)
        
        # Generate vector
        return [rng.uniform(-1.0, 1.0) for _ in range(self._dim)]

    def __call__(self, input: List[str]) -> List[List[float]]:
        return [self._hash_text(t) for t in input]
        
    def embed_query(self, input: List[str]) -> List[List[float]]:
        return self.__call__(input)
        
    def embed_document(self, input: List[str]) -> List[List[float]]:
        return self.__call__(input)


def get_embedding_function():
    """
    Factory function to get the embedding function.
    Returns EmbeddingGemma if available, otherwise falls back to default.
    """
    try:
        return EmbeddingGemmaFunction()
    except Exception as e:
        print(f"⚠ Failed to load EmbeddingGemma: {e}")
        print("  Using FallbackEmbeddingFunction (Hash-based)")
        return FallbackEmbeddingFunction()


# Singleton instance
_embedding_function = None

def get_shared_embedding_function():
    """Get or create a shared embedding function instance."""
    global _embedding_function
    if _embedding_function is None:
        _embedding_function = get_embedding_function()
    return _embedding_function
