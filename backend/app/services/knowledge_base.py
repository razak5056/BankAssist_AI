"""
Banking Knowledge Base Facade for BankAssist AI.
Connects the AI Banking Agent to the master 40-scenario knowledge dataset
and ChromaDB Vector Database.
"""

from typing import Any, Optional
from backend.app.services.knowledge_data import BANKING_SCENARIOS
from backend.app.services.vector_db import search_vector_knowledge

# Master knowledge source across all 5 banking categories
BANKING_KNOWLEDGE_BASE: list[dict[str, Any]] = [
    {
        "id": s["id"],
        "category": s["category"],
        "title": s["title"],
        "is_dispute": s.get("is_dispute", False),
        "policy": s.get("policy", ""),
        "answer": s["content"],
        "keywords": s.get("tags", []),
        "dispute_triggers": [t for t in s.get("tags", []) if any(k in t for k in ["fail", "debit", "stuck", "fraud", "freeze", "loss"])],
    }
    for s in BANKING_SCENARIOS
]


def is_greeting(query: str) -> bool:
    """Detects simple greetings to avoid unnecessary searches."""
    q = query.strip().lower()
    return q in {
        "hi", "hello", "hey", "hola", "namaste", "good morning",
        "good afternoon", "good evening", "greetings", "help",
    }


def is_dispute_or_complaint(query: str, category: Optional[str] = None) -> bool:
    """Checks if query expresses an active problem or dispute."""
    dispute_keywords = {
        "failed", "fail", "failure", "debited", "deducted", "lost", "stolen",
        "fraud", "scam", "unauthorized", "dispute", "complaint", "not received",
        "not credited", "not working", "stuck", "frozen", "blocked", "freeze",
    }
    words = set(query.lower().split())
    return bool(words & dispute_keywords)


def detect_category(query: str) -> str:
    """Detects high-level category if present."""
    q = query.lower()
    if any(k in q for k in ["upi", "bhim", "gpay", "phonepe", "vpa", "qr"]):
        return "UPI"
    if any(k in q for k in ["atm", "cash", "dispense", "cdm"]):
        return "ATM"
    if any(k in q for k in ["card", "credit card", "debit card", "pos", "cvv", "pin"]):
        return "Cards"
    if any(k in q for k in ["kyc", "aadhaar", "pan", "re-kyc", "dormant", "nominee"]):
        return "KYC"
    if any(k in q for k in ["account", "balance", "statement", "cheque", "neft", "rtgs", "imps"]):
        return "Account"
    return "General"


def find_knowledge_topic(query: str, category: Optional[str] = None) -> Optional[dict[str, Any]]:
    """
    Finds best matching knowledge topic using the ChromaDB vector database.
    """
    results = search_vector_knowledge(query, category=category, top_k=1)
    if results:
        top = results[0]
        return {
            "id": top["id"],
            "title": top["title"],
            "category": top["category"],
            "is_dispute": top.get("is_dispute", False),
            "policy": top.get("policy", ""),
            "answer": top["content"],
        }
    return None
