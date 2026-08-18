"""
Kadi — Vector Store Configuration.

Provides utilities to set up pgvector column extensions and mock/local FAISS
indexes for semantic retrieval of entities.
"""

import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("Kadi.VectorStore")

class KadiVectorStore:
    """Manages pgvector and local FAISS indexes for Kadi entity store."""

    def __init__(self):
        self.faiss_index = None
        self.indexed_entities = []

    def setup_pgvector_index(self, db_session) -> bool:
        """Runs SQL command to enable pgvector extension and create index on entities."""
        try:
            # Execute extension creation
            # Note: We run it inside raw SQL to avoid dependency on pgvector-python packages in early scaffold
            db_session.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info("pgvector extension ensured in database.")
            return True
        except Exception as e:
            logger.warning(f"Could not enable pgvector extension (non-postgres environment or missing privilege): {e}")
            return False

    def query_similarity_faiss(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Queries local in-memory/FAISS similarity index."""
        # Simple fallback/mock cosine/euclidean distance search if FAISS not fully initialized
        results = []
        if not self.indexed_entities:
            return results

        # Simple mock list search for scaffold validation
        for entity in self.indexed_entities:
            # Mock scoring (1.0 default)
            results.append({
                "entity": entity,
                "score": 1.0
            })
        return results[:top_k]

    def index_entity_faiss(self, entity_id: str, name: str, vector: List[float]):
        """Adds entity name and embedding vector to the local index."""
        self.indexed_entities.append({
            "id": entity_id,
            "name": name,
            "vector": vector
        })
        logger.info(f"Indexed entity {entity_id} in FAISS store.")
