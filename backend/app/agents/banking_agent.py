"""
AI Banking Agent for BankAssist AI.
Analyzes customer queries, retrieves verified banking knowledge, decides whether
to answer directly or create a support ticket, and manages automatic routing to L1 support.
"""

from datetime import datetime, timezone
import json
import os
import re
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.services.intent_classifier import classify_intent
from backend.app.services.knowledge_base import (
    detect_category,
    is_dispute_or_complaint,
    find_knowledge_topic,
    is_greeting,
    BANKING_KNOWLEDGE_BASE,
)
from backend.app.services.routing_engine import create_and_route_ticket
from backend.app.services.vector_db import search_vector_knowledge


def _call_ai_provider(
    question: str,
    context: str,
    is_ticket_response: bool = False,
    ticket_info: Optional[dict[str, Any]] = None,
) -> str:
    """Calls OpenAI-compatible chat-completions API if configured."""
    api_key = os.getenv("BANKING_AI_API_KEY")
    if not api_key:
        raise RuntimeError("BANKING_AI_API_KEY is not configured")

    base_url = os.getenv("BANKING_AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("BANKING_AI_MODEL", "gpt-4o-mini")
    if not base_url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        raise RuntimeError("BANKING_AI_BASE_URL must use HTTPS")

    if is_ticket_response and ticket_info:
        system_instruction = (
            "You are the BankAssist AI Banking Agent. The customer has reported a banking dispute/problem. "
            f"An automatic ticket has already been created with details: Ticket #{ticket_info['ticket_number']}, "
            f"Category: {ticket_info['category']}, Priority: {ticket_info['priority']}, Assigned Tier: {ticket_info['assigned_tier']}, "
            f"SLA Target: {ticket_info['sla_hours']} hours.\n\n"
            "Respond politely and empathetically. Summarize the immediate banking turnaround guidelines (e.g. RBI/NPCI rules from context), "
            "provide any immediate safety precautions (such as blocking card if unauthorized), and confirm the ticket reference number. "
            "Never ask for PINs, passwords, or OTPs. Keep the response concise, professional, and structured."
        )
    else:
        system_instruction = (
            "You are the BankAssist AI Banking Agent, a customer-support assistant. "
            "Answer using the verified BankAssist guidance provided below. If it does not answer the question, "
            "explain clearly and advise the customer to contact support. Never request passwords, card numbers, PINs, or OTPs. "
            "Keep the answer concise, informative, and professional.\n\n"
            f"Verified Guidance:\n{context}"
        )

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": question},
        ],
    }
    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BankAssistAI/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
        answer = result["choices"][0]["message"]["content"]
        return answer.strip()
    except Exception as exc:
        raise RuntimeError("AI provider request failed") from exc


def format_ticket_dict(ticket) -> dict[str, Any]:
    """Formats a SQLAlchemy Ticket object into a dictionary for response serialization."""
    return {
        "id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_tier": ticket.assigned_tier,
        "sla_hours": ticket.sla_hours,
        "sla_deadline": ticket.sla_deadline.isoformat() if ticket.sla_deadline else None,
        "ai_summary": ticket.ai_summary,
        "resolution_notes": ticket.resolution_notes,
        "evidence_filename": getattr(ticket, "evidence_filename", None),
        "evidence_url": getattr(ticket, "evidence_url", None),
        "customer_id": ticket.customer_id,
        "customer_name": ticket.customer.username if ticket.customer else None,
        "customer_email": ticket.customer.email if ticket.customer else None,
        "assigned_to_id": ticket.assigned_to_id,
        "assigned_to_name": ticket.assigned_to.username if ticket.assigned_to else "L1 Queue",
        "created_at": ticket.created_at.isoformat() if ticket.created_at else datetime.now(timezone.utc).isoformat(),
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else datetime.now(timezone.utc).isoformat(),
        "history": [
            {
                "id": h.id,
                "action": h.action,
                "details": h.details,
                "actor_name": h.actor.username if h.actor else "System",
                "created_at": h.created_at.isoformat(),
            }
            for h in (ticket.history or [])
        ],
    }


INTENT_TOPIC_MAP = {
    "ACCOUNT_PROFILE_INQUIRY": "account_profile_info",
    "UPI_TRANSACTION_LIMIT": "upi_limits",
    "ATM_WITHDRAWAL_LIMIT": "atm_limits",
    "CARD_USAGE_LIMIT": "card_online_usage",
    "PIN_RESET_GUIDANCE": "upi_pin_reset",
    "BALANCE_STATEMENT_INQUIRY": "account_balance_statement",
    "CARD_MANAGEMENT_INQUIRY": "card_online_usage",
    "KYC_PROCESS_INQUIRY": "kyc_verification_update",
    "TRANSFER_MODES_INQUIRY": "account_transfer_modes",
}


def process_customer_query(
    db: Session,
    customer: User,
    question: str,
) -> dict[str, Any]:
    """
    Core AI Agent entrypoint for customer queries.
    1. Understands customer query and detects category & intent.
    2. Uses banking knowledge base.
    3. If query is ambiguous (e.g. daily limits without payment type), asks for clarification.
    4. Decides whether to answer directly or automatically create a support ticket.
    5. Summarizes and responds.
    """
    cleaned_query = question.strip()

    # Step 1: Classify Customer Intent & Category
    intent_res = classify_intent(cleaned_query)

    # -------------------------------------------------------------
    # CASE 0: Greetings & Friendly Inquiries (e.g. "hi", "hello")
    # -------------------------------------------------------------
    if intent_res.intent_name == "GREETING" or is_greeting(cleaned_query):
        customer_name = customer.username.split()[0] if customer and customer.username else "there"
        greeting_msg = (
            f"Hello {customer_name}! 👋 Welcome to the BankAssist Support Help Desk.\n\n"
            "I am your AI Banking Agent. How can I assist you today? You can ask me about:\n"
            "• 💳 **Debit & Credit Cards** (block card, report unauthorized charges)\n"
            "• 💸 **UPI & Digital Payments** (failed transfers, limits, PIN reset)\n"
            "• 🏧 **ATM Withdrawals** (cash not dispensed, swallowed cards)\n"
            "• 📄 **Account & Balance** (statements, balance hold, transfer timings)\n"
            "• 📑 **Account Access & KYC** (re-KYC verification, dormant accounts)\n\n"
            "If you are facing an issue with any banking service or transaction, please describe it and I will either provide verified guidance or automatically open and route a support ticket for you!"
        )
        return {
            "answer": greeting_msg,
            "mode": "banking_agent",
            "source": "greeting",
            "category": "General",
            "intent": "GREETING",
            "clarification_options": [],
            "ticket_created": False,
            "ticket": None,
        }

    # -------------------------------------------------------------
    # CASE 1: Category Overviews (e.g. from Dashboard Category Cards)
    # -------------------------------------------------------------
    if intent_res.intent_name == "ACCOUNT_CATEGORY_OVERVIEW":
        overview_msg = (
            "You are asking about **Account & Balance** services.\n\n"
            "Here is how you can manage your account and balance:\n\n"
            "• 💰 **Check Balance & Mini-Statement:** View your real-time available balance and recent transactions anytime on your **Overview** tab, or via mobile banking / missed-call banking.\n"
            "• 📄 **Download Bank Statements:** Download official 3, 6, or 12-month e-Statements (PDF) from Net Banking > Accounts > e-Statement.\n"
            "• ⚡ **Fund Transfers (IMPS, NEFT, RTGS):** IMPS is instant 24x7 up to ₹5 Lakh; NEFT operates 24x7 in half-hourly batches; RTGS is available for high-value transfers (₹2 Lakh and above).\n"
            "• 👤 **Profile Details:** Review your registered email, customer ID, and account status from your profile.\n\n"
            "Could you please confirm what specific account assistance you need?\n\n"
            "You can select an option below or type your question."
        )
        return {
            "answer": overview_msg,
            "mode": "banking_agent",
            "source": "Account & Balance Services",
            "category": "Account",
            "intent": "ACCOUNT_CATEGORY_OVERVIEW",
            "clarification_options": [
                "Check Balance & Statement",
                "Fund Transfer Timings",
                "My Profile Details",
            ],
            "ticket_created": False,
            "ticket": None,
        }

    if intent_res.intent_name == "UPI_CATEGORY_OVERVIEW":
        overview_msg = (
            "You are asking about **UPI & Digital Payments**.\n\n"
            "Here are the key UPI services and guidelines:\n\n"
            "• 💸 **Failed UPI Transfer with Money Debited:** Standard auto-reversal is completed within **T+1 business days**. If it has exceeded 24 hours, we can open a dispute ticket with your UTR number.\n"
            "• 📊 **Daily Transaction Limits:** Standard NPCI limit allows up to **20 transactions** or **₹1,00,000 per day**.\n"
            "• 🔑 **Reset UPI PIN:** Go to your UPI app, select the bank account, and verify using the last 6 digits of your debit card and OTP.\n\n"
            "Could you please confirm what UPI assistance you need?"
        )
        return {
            "answer": overview_msg,
            "mode": "banking_agent",
            "source": "UPI & Digital Payments",
            "category": "UPI",
            "intent": "UPI_CATEGORY_OVERVIEW",
            "clarification_options": [
                "Failed UPI Transfer",
                "Daily Transaction Limit",
                "Reset UPI PIN",
            ],
            "ticket_created": False,
            "ticket": None,
        }

    if intent_res.intent_name == "ATM_CATEGORY_OVERVIEW":
        overview_msg = (
            "You are asking about **ATM Cash Withdrawals**.\n\n"
            "Here is the key guidance for ATM services:\n\n"
            "• 🏧 **Cash Not Dispensed but Debited:** Under RBI mandate, banks must resolve failed ATM cash dispense within **T+5 business days**, failing which compensation of **₹100 per day** of delay is payable.\n"
            "• 💳 **Daily Cash Limits:** Standard debit cards allow **₹20,000 to ₹50,000** in daily ATM cash withdrawals (typically 3 to 5 financial withdrawals per day).\n"
            "• 🛑 **Card Swallowed by ATM:** If the ATM machine retained your debit card, the card is destroyed securely for safety and a replacement is dispatched within 3-5 business days.\n\n"
            "Could you please confirm what ATM assistance you need?"
        )
        return {
            "answer": overview_msg,
            "mode": "banking_agent",
            "source": "ATM Withdrawals",
            "category": "ATM",
            "intent": "ATM_CATEGORY_OVERVIEW",
            "clarification_options": [
                "Cash Not Dispensed",
                "ATM Withdrawal Limits",
                "Card Retained in ATM",
            ],
            "ticket_created": False,
            "ticket": None,
        }

    if intent_res.intent_name == "CARD_CATEGORY_OVERVIEW":
        overview_msg = (
            "You are asking about **Debit & Credit Cards**.\n\n"
            "Here are the key card safety and usage guidelines:\n\n"
            "• 🛡️ **Lost / Stolen Card (Instant Block):** You can block your card instantly via your mobile banking app or by contacting our 24/7 hotline to prevent unauthorized transactions.\n"
            "• ⚠️ **Report Unauthorized Charges:** Under RBI's zero-liability policy, reporting fraud within **3 business days** ensures zero customer liability.\n"
            "• 🌐 **Online & International Usage:** Enable or disable domestic online, contactless (tap & pay), or international spending anytime in your app.\n\n"
            "Could you please confirm what card assistance you need?"
        )
        return {
            "answer": overview_msg,
            "mode": "banking_agent",
            "source": "Debit & Credit Cards",
            "category": "Cards",
            "intent": "CARD_CATEGORY_OVERVIEW",
            "clarification_options": [
                "Block Card Immediately",
                "Report Unauthorized Charge",
                "Card Online Usage",
            ],
            "ticket_created": False,
            "ticket": None,
        }

    if intent_res.intent_name == "KYC_CATEGORY_OVERVIEW":
        overview_msg = (
            "You are asking about **Account Access & KYC Verification**.\n\n"
            "Here is the verified guidance for account access and KYC:\n\n"
            "• 📑 **Periodic Re-KYC Update:** Low-risk customers require re-KYC every 10 years, medium-risk every 8 years, and high-risk every 2 years. If no details changed, submit a self-declaration online.\n"
            "• 🔒 **Dormant / Inoperative Account:** If no customer-induced transaction occurred in 2 years, your account is marked dormant. Reactivate by visiting your branch with original KYC documents.\n"
            "• 🪪 **Officially Valid Documents:** Passport, Driving License, Proof of possession of Aadhaar, Voter's Identity Card, or NREGA Job Card.\n\n"
            "Could you please confirm what KYC or account access help you need?"
        )
        return {
            "answer": overview_msg,
            "mode": "banking_agent",
            "source": "Account Access & KYC",
            "category": "KYC",
            "intent": "KYC_CATEGORY_OVERVIEW",
            "clarification_options": [
                "Periodic Re-KYC Steps",
                "Dormant Account Activation",
                "Acceptable Documents",
            ],
            "ticket_created": False,
            "ticket": None,
        }

    # -------------------------------------------------------------
    # CASE 1B: Ambiguous Limit Query requiring Clarification
    # -------------------------------------------------------------
    if intent_res.intent_name in ("DAILY_TRANSACTION_LIMIT", "GENERAL_TRANSACTION_LIMIT"):
        clarification_answer = (
            "You are asking about the number of transactions you can make per day.\n\n"
            "The daily transaction limit depends on your bank and the type of transaction. For UPI, banks may also have limits on the number of transactions allowed in a day:\n\n"
            "• 💸 **UPI & Digital Payments:** Under standard NPCI guidelines, you can make up to **20 transactions** or up to **₹1,00,000 (1 Lakh)** per day (newly linked accounts or reset devices have an initial 24-hour security limit of ₹5,000).\n"
            "• 🏧 **ATM Cash Withdrawals:** Most debit cards allow **₹20,000 to ₹50,000** in daily cash withdrawals (typically 3 to 5 financial withdrawals per day).\n"
            "• 💳 **Debit/Credit Cards:** POS and online spending limits are configured by customized limits set in your mobile banking app.\n\n"
            "Could you please confirm whether you are asking about **UPI transactions**, **ATM withdrawals**, or **Debit/Credit card usage**?\n\n"
            "I can provide the relevant guidance based on your selection."
        )
        return {
            "answer": clarification_answer,
            "mode": "banking_agent",
            "source": "Daily Transaction Limits",
            "category": "UPI",
            "intent": "DAILY_TRANSACTION_LIMIT",
            "clarification_options": ["UPI Transactions", "ATM Withdrawals", "Debit/Credit Cards"],
            "ticket_created": False,
            "ticket": None,
        }

    # -------------------------------------------------------------
    # CASE 1B: Account Profile / Information Request
    # -------------------------------------------------------------
    if intent_res.intent_name == "ACCOUNT_PROFILE_INQUIRY":
        status_label = "Active" if customer and customer.is_active else "Inactive"
        cust_name = customer.username if customer else "Customer"
        cust_email = customer.email if customer else "Not available"
        cust_id = customer.id if customer else "—"

        profile_answer = (
            f"Here is your registered BankAssist account profile information:\n\n"
            f"• 👤 **Full Name:** {cust_name}\n"
            f"• 📧 **Registered Email:** {cust_email}\n"
            f"• 🆔 **Customer ID:** #{cust_id}\n"
            f"• 🛡️ **Account Status:** {status_label}\n"
            f"• 🔒 **Security Session:** Protected & encrypted (JWT authenticated)\n\n"
            "You can also review your full account profile, open disputes, and available services anytime on your **Overview** dashboard."
        )
        return {
            "answer": profile_answer,
            "mode": "banking_agent",
            "source": "Account Profile",
            "category": "Account",
            "intent": "ACCOUNT_PROFILE_INQUIRY",
            "clarification_options": [],
            "ticket_created": False,
            "ticket": None,
        }

    category = intent_res.category
    priority = intent_res.suggested_priority

    # Knowledge retrieval via Vector Database semantic search across 40 scenarios
    vector_matches = search_vector_knowledge(
        cleaned_query,
        category=category if category != "General" else None,
        is_dispute=intent_res.is_dispute,
        top_k=3,
    )
    top_vector = vector_matches[0] if vector_matches else None

    # Topic retrieval (checking mapped intent first, then vector result, then fallback)
    topic = None
    if intent_res.intent_name in INTENT_TOPIC_MAP:
        mapped_id = INTENT_TOPIC_MAP[intent_res.intent_name]
        topic = next((t for t in BANKING_KNOWLEDGE_BASE if t["id"] == mapped_id), None)

    if not topic and top_vector:
        topic = {
            "id": top_vector["id"],
            "title": top_vector["title"],
            "answer": top_vector["content"],
            "policy": top_vector.get("policy", ""),
            "category": top_vector.get("category", category),
        }

    if not topic:
        topic = find_knowledge_topic(cleaned_query, category=category)

    # Compile grounded RAG context from top vector matches
    context_chunks = []
    if vector_matches:
        for m in vector_matches:
            context_chunks.append(f"Topic: {m['title']}\nGuidance: {m['content']}\nPolicy: {m.get('policy', '')}")
    elif topic:
        context_chunks.append(f"Topic: {topic['title']}\nAnswer: {topic.get('answer', '')}\nPolicy: {topic.get('policy', '')}")
    rag_context = "\n\n---\n\n".join(context_chunks)

    # -------------------------------------------------------------
    # CASE 2: Query is an actionable dispute / complaint / problem
    # (Ticket Decision: Ticket = True)
    # -------------------------------------------------------------
    if intent_res.is_dispute:
        # Generate issue title
        words = cleaned_query.split()
        short_title = " ".join(words[:10]) + ("..." if len(words) > 10 else "")
        title = f"{category} Issue: {short_title}"

        # Prepare AI context / summary based on policy
        policy_note = topic.get("policy", "Standard RBI Turnaround Time (TAT) applies.") if topic else "Standard banking dispute procedure initiated."
        guidance = topic.get("answer", "") if topic else ""
        ai_summary = f"Identified category: {category}. Suggested priority: {priority}. Applicable policy: {policy_note}"

        # 1. Automatically create and route the ticket via the Routing Engine
        ticket = create_and_route_ticket(
            db=db,
            customer=customer,
            title=title,
            description=cleaned_query,
            category=category,
            priority=priority,
            ai_summary=ai_summary,
        )

        ticket_data = format_ticket_dict(ticket)

        # 2. Try LLM generation if configured
        provider_configured = bool(os.getenv("BANKING_AI_API_KEY"))
        answer_text = ""
        mode = "ai"

        if provider_configured:
            try:
                answer_text = _call_ai_provider(
                    question=cleaned_query,
                    context=f"{rag_context}\nDispute Policy: {policy_note}",
                    is_ticket_response=True,
                    ticket_info=ticket_data,
                )
            except Exception:
                mode = "banking_agent_fallback"

        if not answer_text:
            # Deterministic, high-quality banking agent response
            assigned_team = ticket.assigned_tier
            assignee_text = f"assigned to our {assigned_team} team"
            if ticket.assigned_to:
                assignee_text += f" (Executive: {ticket.assigned_to.username})"

            answer_text = (
                f"We have registered your dispute regarding your {category} query.\n\n"
                f"📋 **Ticket Created:** #{ticket.ticket_number}\n"
                f"🔹 **Category:** {ticket.category}\n"
                f"🔹 **Priority:** {ticket.priority}\n"
                f"🔹 **Assigned To:** {assignee_text}\n"
                f"⏱️ **Target Resolution SLA:** {ticket.sla_hours} hours\n\n"
                f"**Turnaround Guidance:**\n{guidance}\n\n"
                f"Our banking support executive has been notified and will investigate the transaction logs. You can track this dispute anytime from your Overview tab."
            )
            if not provider_configured:
                mode = "banking_agent"

        return {
            "answer": answer_text,
            "mode": mode,
            "source": f"Banking Dispute Resolution ({category})",
            "category": category,
            "intent": intent_res.intent_name,
            "clarification_options": [],
            "ticket_created": True,
            "ticket": ticket_data,
        }

    # -------------------------------------------------------------
    # CASE 3: Query is informational (guidance, limits, how-to)
    # (Ticket Decision: Ticket = False)
    # -------------------------------------------------------------
    else:
        provider_configured = bool(os.getenv("BANKING_AI_API_KEY"))
        mode = "ai"
        answer_text = ""

        if provider_configured and (topic or rag_context):
            try:
                answer_text = _call_ai_provider(
                    question=cleaned_query,
                    context=rag_context,
                    is_ticket_response=False,
                )
            except Exception:
                mode = "help_center_fallback"

        if not answer_text:
            if topic:
                answer_text = f"**{topic['title']}**\n\n{topic['answer']}"
                source = topic["title"]
                mode = "banking_knowledge_base"
            else:
                answer_text = (
                    "I couldn't find a direct match in our verified banking knowledge base for that question.\n\n"
                    "You can ask about:\n"
                    "• Daily transaction limits for UPI and ATM\n"
                    "• How to reset UPI or ATM PIN\n"
                    "• Blocking cards or reporting unauthorized charges\n"
                    "• Downloading statements or balance queries\n"
                    "• KYC documents and re-KYC process\n\n"
                    "If you are experiencing an issue or need human support, please let me know and I will register a support ticket for you."
                )
                source = "general_guidance"
                mode = "banking_knowledge_base"
        else:
            source = topic["title"] if topic else "general_guidance"

        return {
            "answer": answer_text,
            "mode": mode,
            "source": source,
            "category": category,
            "intent": intent_res.intent_name,
            "clarification_options": [],
            "ticket_created": False,
            "ticket": None,
        }


# Maintain backward compatibility for any existing code calling answer_question
def answer_question(question: str) -> dict[str, Any]:
    topic = find_knowledge_topic(question)
    category = detect_category(question)
    if topic:
        return {
            "answer": f"{topic['title']}: {topic['answer']}",
            "mode": "help_center",
            "source": str(topic["title"]),
            "category": category,
            "ticket_created": False,
            "ticket": None,
        }
    return {
        "answer": (
            "I couldn't find verified guidance for that question. "
            "Please ask about UPI, ATM withdrawals, card security, account balance, or KYC."
        ),
        "mode": "help_center",
        "source": "no_match",
        "category": category,
        "ticket_created": False,
        "ticket": None,
    }
