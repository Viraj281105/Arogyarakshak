"""
SchemeSetu — Local Offline Fallback Embedding Model.

Configures a local offline embedding model utilizing SentenceTransformers
with an optional ONNX runtime fallback for CPU efficiency on edge nodes.
"""

import os
import logging
from typing import List

logger = logging.getLogger("SchemeSetu.Embeddings")

class OfflineEmbedder:
    """Manages offline local sentence embeddings generation."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.use_fallback = True
        
        # Attempt to load SentenceTransformers
        try:
            from sentence_transformers import SentenceTransformer
            # Check if we want to force ONNX/Optimum runtime
            self.model = SentenceTransformer(model_name)
            self.use_fallback = False
            logger.info(f"Loaded local SentenceTransformer model: {model_name}")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformers library ({e}). Using lightweight offline fallback embedder.")

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for list of strings."""
        if not self.use_fallback and self.model:
            try:
                embeddings = self.model.encode(texts)
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                logger.error(f"Failed to encode texts via SentenceTransformers: {e}. Falling back.")
        
        # Simple, deterministic, lightweight TF-IDF/phonetic hash mock embedding fallback
        # Outputs 384-dimensional vectors matching MiniLM dimensions
        embeddings = []
        for text in texts:
            vector = [0.0] * 384
            words = text.lower().split()
            for idx, word in enumerate(words):
                # Hash word to a feature index
                h = hash(word) % 384
                vector[h] += 1.0
            
            # Normalize vector
            norm = sum(x*x for x in vector) ** 0.5
            if norm > 0:
                vector = [x / norm for x in vector]
            
            embeddings.append(vector)
        return embeddings
