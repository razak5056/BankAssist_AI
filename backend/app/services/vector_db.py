"""
Vector Database Service for BankAssist AI.
Implements semantic vector storage and retrieval for banking knowledge base (RAG).
Supports:
1. ChromaDB (persistent vector database at data/chroma_db).
2. High-performance Numpy Dense Vector Store with cosine similarity and TF-IDF
   semantic projections as an automatic resilient fallback.

Indexes all 40 scenarios across the 5 banking categories:
- UPI & Digital Payments (8)
- ATM & Cash Withdrawal (8)
- Debit & Credit Cards (8)
- Account & Balance (8)
- Account Access & KYC (8)
"""

import sys
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

from collections import Counter
import math
import os
from pathlib import Path
import re
from typing import Any, Optional

import numpy as np

from backend.app.services.knowledge_data import BANKING_SCENARIOS

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
VECTOR_INDEX_FILE = DATA_DIR / "vector_store.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class DenseSemanticVectorStore:
    """
    Self-contained, persistent dense vector engine with cosine similarity search.
    Provides zero-dependency, ultra-fast vector retrieval.
    """

    def __init__(self):
        self.documents: list[dict[str, Any]] = []
        self.vocab: dict[str, int] = {}
        self.idf: np.ndarray = np.array([])
        self.embeddings: np.ndarray = np.array([])
        self.build_index()

    def _tokenize(self, text: str) -> list[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
        # Filter basic stop words
        stopwords = {
            "the", "is", "at", "which", "on", "a", "an", "and", "or", "to",
            "in", "for", "with", "by", "from", "of", "it", "this", "that",
            "your", "my", "you", "are", "can", "have", "has", "do", "does",
        }
        return [w for w in words if w not in stopwords]

    def _compute_vector(self, tokens: list[str]) -> np.ndarray:
        if len(self.vocab) == 0:
            return np.zeros(1)
        tf = Counter(tokens)
        vec = np.zeros(len(self.vocab), dtype=np.float32)
        for word, count in tf.items():
            if word in self.vocab:
                idx = self.vocab[word]
                vec[idx] = (1.0 + math.log(count)) * self.idf[idx]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def build_index(self):
        """Indexes all 40 banking scenarios into dense normalized vector embeddings."""
        self.documents = list(BANKING_SCENARIOS)

        # Build vocabulary across all documents (including titles, content, and tags)
        all_doc_tokens = []
        word_doc_freq = Counter()

        for doc in self.documents:
            text = f"{doc['title']} {doc['content']} {' '.join(doc.get('tags', []))}"
            tokens = self._tokenize(text)
            all_doc_tokens.append(tokens)
            unique_words = set(tokens)
            for w in unique_words:
                word_doc_freq[w] += 1

        # Vocabulary of words appearing in documents
        vocab_words = sorted(word_doc_freq.keys())
        self.vocab = {w: idx for idx, w in enumerate(vocab_words)}

        num_docs = len(self.documents)
        idf_vals = np.zeros(len(vocab_words), dtype=np.float32)
        for w, idx in self.vocab.items():
            df = word_doc_freq[w]
            idf_vals[idx] = math.log((1.0 + num_docs) / (1.0 + df)) + 1.0
        self.idf = idf_vals

        # Compute dense embeddings for all documents
        doc_vectors = []
        for tokens in all_doc_tokens:
            vec = self._compute_vector(tokens)
            doc_vectors.append(vec)

        self.embeddings = np.array(doc_vectors, dtype=np.float32)

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        is_dispute: Optional[bool] = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Calculates cosine similarity between query vector and knowledge vectors,
        filters by category/dispute status, and returns the top-k most relevant documents.
        """
        query_tokens = self._tokenize(query)
        query_vec = self._compute_vector(query_tokens)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0 or len(self.documents) == 0:
            # Fallback to category filtering
            candidates = [
                d for d in self.documents
                if (category is None or d["category"].lower() == category.lower())
            ]
            return candidates[:top_k]

        # Cosine similarity (dot product of L2 normalized vectors)
        scores = np.dot(self.embeddings, query_vec)

        # Apply category and dispute boosts/filters
        results = []
        for idx, doc in enumerate(self.documents):
            score = float(scores[idx])

            # Exact tag bonus
            doc_tags = [t.lower() for t in doc.get("tags", [])]
            for tag in doc_tags:
                if tag in query.lower():
                    score += 0.35

            # Category filter/boost
            if category:
                if doc["category"].lower() == category.lower():
                    score += 0.25
                else:
                    score -= 0.30

            # Dispute indicator filter
            if is_dispute is not None:
                if doc.get("is_dispute", False) == is_dispute:
                    score += 0.20
                else:
                    score -= 0.25

            results.append((score, doc))

        # Sort descending by score
        results.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "score": round(score, 4),
                "id": doc["id"],
                "category": doc["category"],
                "title": doc["title"],
                "is_dispute": doc.get("is_dispute", False),
                "policy": doc.get("policy", ""),
                "content": doc["content"],
                "tags": doc.get("tags", []),
            }
            for score, doc in results[:top_k]
        ]


# Singleton instance of vector database
_vector_store_instance: Optional[Any] = None


def get_vector_store():
    """Returns initialized persistent vector database instance."""
    global _vector_store_instance
    if _vector_store_instance is None:
        try:
            # Check if chromadb is available
            import chromadb
            from chromadb.config import Settings

            client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            collection = client.get_or_create_collection(
                name="bankassist_banking_knowledge",
                metadata={"description": "RBI & NPCI banking dispute and resolution guidelines"},
            )

            # Check if collection needs seeding
            if collection.count() < len(BANKING_SCENARIOS):
                ids = [doc["id"] for doc in BANKING_SCENARIOS]
                documents = [f"{doc['title']}\n{doc['content']}" for doc in BANKING_SCENARIOS]
                metadatas = [
                    {
                        "category": doc["category"],
                        "title": doc["title"],
                        "is_dispute": str(doc.get("is_dispute", False)),
                        "policy": doc.get("policy", ""),
                    }
                    for doc in BANKING_SCENARIOS
                ]
                collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

            _vector_store_instance = ("chroma", collection)
        except Exception:
            # Fallback to high-speed dense vector store
            _vector_store_instance = ("dense", DenseSemanticVectorStore())

    return _vector_store_instance


def search_vector_knowledge(
    query: str,
    category: Optional[str] = None,
    is_dispute: Optional[bool] = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """
    Unified vector search interface for the AI Banking Agent.
    Searches across all 40 banking scenarios and returns top semantic matches.
    """
    store_type, store = get_vector_store()

    if store_type == "chroma":
        where_filter = {}
        if category:
            where_filter["category"] = category

        try:
            results = store.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter if where_filter else None,
            )
            hits = []
            if results and results["documents"]:
                for i in range(len(results["documents"][0])):
                    meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                    hits.append({
                        "id": results["ids"][0][i],
                        "category": meta.get("category", "General"),
                        "title": meta.get("title", ""),
                        "is_dispute": meta.get("is_dispute") == "True",
                        "policy": meta.get("policy", ""),
                        "content": results["documents"][0][i],
                        "score": 1.0 - (results["distances"][0][i] if results.get("distances") else 0.0),
                    })
            if hits:
                return hits
        except Exception:
            pass

    # Dense vector engine
    if isinstance(store, DenseSemanticVectorStore):
        return store.search(query=query, category=category, is_dispute=is_dispute, top_k=top_k)

    dense_store = DenseSemanticVectorStore()
    return dense_store.search(query=query, category=category, is_dispute=is_dispute, top_k=top_k)
