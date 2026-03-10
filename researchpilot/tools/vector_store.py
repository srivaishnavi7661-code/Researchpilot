"""
ResearchPilot - Vector Store
FAISS-based semantic similarity search for papers.
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available. Semantic search disabled.")

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logger.warning("sentence-transformers not available. Semantic search disabled.")


class VectorStore:
    """FAISS-based vector store for semantic paper search."""

    def __init__(
        self,
        store_path: str = "./data/vector_store",
        model_name: str = "all-MiniLM-L6-v2",
        dimension: int = 384
    ):
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self.model_name = model_name
        
        self.index_path = self.store_path / "papers.index"
        self.metadata_path = self.store_path / "metadata.json"
        
        # Paper ID -> index mapping
        self.paper_ids: List[str] = []
        self.metadata: Dict[str, dict] = {}
        
        self._model = None
        self._index = None
        
        self._load()

    @property
    def model(self):
        """Lazy-load the embedding model."""
        if self._model is None and ST_AVAILABLE:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def index(self):
        """Lazy-init FAISS index."""
        if self._index is None and FAISS_AVAILABLE:
            self._index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine with normalized vectors)
        return self._index

    def _load(self):
        """Load existing index and metadata from disk."""
        if not FAISS_AVAILABLE:
            return
            
        if self.index_path.exists():
            try:
                self._index = faiss.read_index(str(self.index_path))
                logger.info(f"Loaded FAISS index with {self._index.ntotal} vectors")
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}")
        
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, "r") as f:
                    data = json.load(f)
                    self.paper_ids = data.get("paper_ids", [])
                    self.metadata = data.get("metadata", {})
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")

    def _save(self):
        """Save index and metadata to disk."""
        if not FAISS_AVAILABLE or self._index is None:
            return
        
        try:
            faiss.write_index(self._index, str(self.index_path))
            with open(self.metadata_path, "w") as f:
                json.dump({"paper_ids": self.paper_ids, "metadata": self.metadata}, f)
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")

    def _embed(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text."""
        if not ST_AVAILABLE or self.model is None:
            return None
        try:
            embedding = self.model.encode([text], normalize_embeddings=True)
            return embedding.astype(np.float32)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return None

    def add_paper(self, paper_id: str, title: str, abstract: str, extra_meta: dict = None) -> bool:
        """Add a paper to the vector store."""
        if not FAISS_AVAILABLE or not ST_AVAILABLE:
            return False
        
        if paper_id in self.paper_ids:
            return True  # Already exists
        
        text = f"{title}\n\n{abstract}"
        embedding = self._embed(text)
        
        if embedding is None:
            return False
        
        self.index.add(embedding)
        self.paper_ids.append(paper_id)
        self.metadata[paper_id] = {
            "title": title,
            "index": len(self.paper_ids) - 1,
            **(extra_meta or {})
        }
        
        self._save()
        return True

    def search(self, query: str, k: int = 10) -> List[Tuple[str, float]]:
        """
        Search for similar papers.
        
        Returns:
            List of (paper_id, similarity_score) tuples, sorted by score descending
        """
        if not FAISS_AVAILABLE or not ST_AVAILABLE:
            return []
        
        if self.index is None or self.index.ntotal == 0:
            return []
        
        embedding = self._embed(query)
        if embedding is None:
            return []
        
        k = min(k, self.index.ntotal)
        distances, indices = self.index.search(embedding, k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.paper_ids) and idx >= 0:
                paper_id = self.paper_ids[idx]
                results.append((paper_id, float(dist)))
        
        return sorted(results, key=lambda x: x[1], reverse=True)

    def find_similar(self, paper_id: str, k: int = 10) -> List[Tuple[str, float]]:
        """Find papers similar to a given paper."""
        if paper_id not in self.paper_ids:
            return []
        
        idx = self.paper_ids.index(paper_id)
        
        if not FAISS_AVAILABLE or self.index.ntotal == 0:
            return []
        
        # Reconstruct vector for the paper
        vec = faiss.rev_swig_ptr(self.index.get_xb(), self.index.ntotal * self.dimension)
        vec = np.frombuffer(vec, dtype=np.float32).reshape(self.index.ntotal, self.dimension)
        paper_vec = vec[idx:idx+1]
        
        k = min(k + 1, self.index.ntotal)  # +1 to exclude self
        distances, indices = self.index.search(paper_vec, k)
        
        results = []
        for dist, i in zip(distances[0], indices[0]):
            if i < len(self.paper_ids) and i >= 0 and i != idx:
                results.append((self.paper_ids[i], float(dist)))
        
        return results

    def remove_paper(self, paper_id: str) -> bool:
        """Remove a paper from the vector store (marks as deleted; requires rebuild for full removal)."""
        if paper_id not in self.paper_ids:
            return False
        self.paper_ids.remove(paper_id)
        if paper_id in self.metadata:
            del self.metadata[paper_id]
        self._save()
        return True

    @property
    def total_papers(self) -> int:
        """Total number of papers in the vector store."""
        return len(self.paper_ids)

    @property
    def is_available(self) -> bool:
        return FAISS_AVAILABLE and ST_AVAILABLE
