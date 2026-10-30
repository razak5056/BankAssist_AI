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

from backend.app.models.ticket import Ticket
from backend.app.models.user import User
from backend.app.services.intent_classifier import (
    classify_intent,
    is_unresolved_solution_followup,
    is_clarification_or_didnt_get_followup,
    is_direct_escalation_request,
)
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
            f"An automatic ticket has already been registered in the banking system with clear SLA:\n"
            f"• Ticket Number: #{ticket_info['ticket_number']}\n"
            f"• Category: {ticket_info['category']}\n"
            f"• Case Type: {ticket_info.get('case_type', 'Complaint')}\n"
            f"• Priority: {ticket_info['priority']}\n"
            f"• Assigned Tier: {ticket_info['assigned_tier']}\n"
            f"• Assigned Desk: {ticket_info.get('assigned_to_name', 'Support Queue')}\n"
            f"• SLA Turnaround Window: {ticket_info['sla_hours']} Hours (Standard Banking TAT)\n"
            f"• Target Resolution Deadline: {ticket_info.get('sla_deadline')}\n\n"
            "Your response MUST explicitly confirm the registered ticket details and clearly inform the customer of:\n"
            "1. The Ticket Reference Number\n"
            "2. The SLA Resolution Window (e.g. 24 hours for L1)\n"
            "3. The Exact Target Resolution Deadline\n"
            "4. Immediate procedural turnaround instructions and regulatory safety rules (e.g. RBI zero liability / instant card blocking if unauthorized charges)\n"
            "Be empathetic, reassuring, professional, and clear. Never ask for PINs, passwords, or OTPs."
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
    sla_remaining_hours = None
    sla_status = "On Track"
    if ticket.sla_deadline:
        now_utc = datetime.now(timezone.utc)
        deadline = ticket.sla_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        diff_seconds = (deadline - now_utc).total_seconds()
        sla_remaining_hours = round(diff_seconds / 3600.0, 1)
        if ticket.status in ("Resolved", "Closed"):
            sla_status = "Completed"
        elif diff_seconds < 0:
            sla_status = "Breached"
        elif diff_seconds <= 4 * 3600:
            sla_status = "Critical"
        elif diff_seconds <= 12 * 3600:
            sla_status = "Approaching"
        else:
            sla_status = "On Track"

    return {
        "id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "case_type": getattr(ticket, "case_type", "Complaint") or "Complaint",
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_tier": ticket.assigned_tier,
        "sla_hours": ticket.sla_hours,
        "sla_deadline": ticket.sla_deadline.isoformat() if ticket.sla_deadline else None,
        "sla_remaining_hours": sla_remaining_hours,
        "sla_status": sla_status,
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
    "ACCOUNT_PROFILE_INQUIRY": "account_balance_statement",
    "UPI_TRANSACTION_LIMIT": "upi_limits",
    "ATM_WITHDRAWAL_LIMIT": "atm_limits",
    "CARD_USAGE_LIMIT": "card_online_usage",
    "CARD_MANAGEMENT_INQUIRY": "card_online_usage",
    "CARD_BLOCK_GUIDANCE": "card_lost_stolen_block",
    "PIN_RESET_GUIDANCE": "upi_pin_reset",
    "BALANCE_STATEMENT_INQUIRY": "account_balance_statement",
    "KYC_PROCESS_INQUIRY": "kyc_periodic_update",
    "KYC_DOCUMENTS_INQUIRY": "kyc_valid_documents",
    "DORMANT_ACCOUNT_INQUIRY": "account_dormant_reactivation",
    "TRANSFER_MODES_INQUIRY": "account_transfer_modes",
    "ATM_CARD_SWALLOWED": "atm_card_swallowed",
    "ATM_CASH_DISPENSE_FAILURE": "atm_cash_not_dispensed",
    "UPI_TRANSACTION_FAILURE": "upi_failed_debited",
    "UNAUTHORIZED_FRAUD_DISPUTE": "card_unauthorized_fraud",
}


CUSTOMER_LAST_CONTEXT: dict[int, dict[str, Any]] = {}


def get_previous_turn_context(
    customer_id: int,
    history: Optional[list[dict[str, Any]]] = None,
    current_query: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Extracts the previous user turn, category, and knowledge topic
    from explicit history array or server-side customer session cache.
    Recovers the substantive question and topic even across multiple follow-ups.
    """
    if history and len(history) > 0:
        prev_user_q = None
        prev_assistant_meta = {}
        substantive_q = None
        substantive_topic = None
        substantive_cat = None

        for msg in reversed(history):
            role = msg.get("role")
            content = msg.get("content", "").strip()
            if role == "user":
                if current_query and content.lower() == current_query.lower() and not prev_assistant_meta:
                    continue
                if not prev_user_q:
                    prev_user_q = content
                is_meta_followup = (
                    is_direct_escalation_request(content)
                    or is_clarification_or_didnt_get_followup(content)
                    or is_unresolved_solution_followup(content)
                )
                if not is_meta_followup and not substantive_q:
                    substantive_q = content
            elif role == "assistant":
                if not prev_assistant_meta:
                    prev_assistant_meta = msg
                src = msg.get("source", "")
                cat = msg.get("category", "")
                if cat and cat != "General" and not substantive_cat:
                    substantive_cat = cat
                if src and not src.startswith("Guidance Clarification") and src != "Clarification" and not substantive_topic:
                    substantive_topic = src

        chosen_q = substantive_q or prev_user_q
        chosen_cat = substantive_cat or prev_assistant_meta.get("category")
        if not chosen_cat or chosen_cat in ("General", "Account", None):
            detected = detect_category(chosen_q or "")
            if detected and detected != "General":
                chosen_cat = detected
            elif "card" in (chosen_q or "").lower():
                chosen_cat = "Cards"
            elif "upi" in (chosen_q or "").lower():
                chosen_cat = "UPI"
            elif "atm" in (chosen_q or "").lower():
                chosen_cat = "ATM"
            elif "kyc" in (chosen_q or "").lower():
                chosen_cat = "KYC"

        chosen_topic = substantive_topic or prev_assistant_meta.get("source") or prev_assistant_meta.get("intent") or "General Inquiry"

        if chosen_q:
            return {
                "query": chosen_q,
                "category": chosen_cat or "General",
                "topic": chosen_topic,
                "case_type": prev_assistant_meta.get("case_type") or "Inquiry",
            }

    if customer_id and customer_id in CUSTOMER_LAST_CONTEXT:
        cached = CUSTOMER_LAST_CONTEXT[customer_id]
        diff = (datetime.now(timezone.utc) - cached.get("timestamp", datetime.now(timezone.utc))).total_seconds()
        if diff < 1800:
            return cached

    return None


def _cache_customer_turn(customer_id: int, query: str, response: dict[str, Any]):
    if not customer_id:
        return
    CUSTOMER_LAST_CONTEXT[customer_id] = {
        "query": query,
        "category": response.get("category", "General"),
        "topic": response.get("source") or response.get("intent", ""),
        "source": response.get("source", ""),
        "intent": response.get("intent", ""),
        "case_type": response.get("case_type", "Inquiry"),
        "ticket_created": response.get("ticket_created", False),
        "timestamp": datetime.now(timezone.utc),
    }


def process_customer_query(
    db: Session,
    customer: User,
    question: str,
    history: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Core AI Agent entrypoint for customer queries.
    1. Understands customer query and detects category & intent.
    2. Maintains multi-turn context (e.g. handling "this solution not working").
    3. Uses banking knowledge base.
    4. If query is ambiguous (e.g. daily limits without payment type), asks for clarification.
    5. Decides whether to answer directly or automatically create a support ticket.
    6. Summarizes and responds.
    """
    cleaned_query = question.strip()

    def finalize(result: dict[str, Any]) -> dict[str, Any]:
        _cache_customer_turn(customer.id if customer else 0, cleaned_query, result)
        return result

    # -------------------------------------------------------------
    # CASE: Explicit Escalation to Human Support / Open Ticket
    # e.g., "esclicate to support", "escalate to support", "talk to agent"
    # -------------------------------------------------------------
    if is_direct_escalation_request(cleaned_query):
        prev_ctx = get_previous_turn_context(customer.id if customer else 0, history, current_query=cleaned_query)
        if prev_ctx and prev_ctx.get("query"):
            inherited_category = prev_ctx.get("category") or "General"
            if inherited_category in ("General", "Account", None):
                detected = detect_category(prev_ctx["query"])
                if detected and detected != "General":
                    inherited_category = detected
                elif "card" in prev_ctx["query"].lower():
                    inherited_category = "Cards"
                elif "upi" in prev_ctx["query"].lower():
                    inherited_category = "UPI"
                elif "atm" in prev_ctx["query"].lower():
                    inherited_category = "ATM"
                elif "kyc" in prev_ctx["query"].lower():
                    inherited_category = "KYC"
                else:
                    inherited_category = "Account"

            prev_q = prev_ctx["query"]
            prev_topic = prev_ctx.get("topic") or "Customer Inquiry"
            clean_title = prev_topic if prev_topic not in ("no_match", "general_guidance", "General Inquiry", "greeting") else prev_q[:40]

            title = f"{inherited_category} Issue: {clean_title} - Escalated to Support"

            description = (
                f"Customer Query / Need: {prev_q}\n"
                f"Guidance Provided: {prev_topic}\n"
                f"Customer Escalation Request: {cleaned_query}\n\n"
                f"Summary: Customer requested human support escalation for their {inherited_category} request. "
                f"Ticket automatically opened and routed to {inherited_category} Support for direct investigation and resolution."
            )

            # Policy
            cat_topic = find_knowledge_topic(prev_q, category=inherited_category)
            if not cat_topic:
                cat_topic = find_knowledge_topic(f"{inherited_category} support", category=inherited_category)
            policy_note = cat_topic.get("policy", f"Standard {inherited_category} turnaround time guidelines apply.") if cat_topic else f"Standard {inherited_category} dispute procedure."
            ai_summary = f"Identified category: {inherited_category}. Suggested priority: High. Applicable policy: {policy_note}"

            priority = "High" if inherited_category in ("ATM", "Cards") else "Normal"

            ticket = create_and_route_ticket(
                db=db,
                customer=customer,
                title=title,
                description=description,
                category=inherited_category,
                priority=priority,
                ai_summary=ai_summary,
                case_type="Complaint",
            )
            ticket_data = format_ticket_dict(ticket)

            assigned_team = ticket.assigned_tier
            assignee_text = f"assigned to our {assigned_team} team"
            if ticket.assigned_to:
                assignee_text += f" (Specialist: {ticket.assigned_to.username})"

            created_dt = ticket.created_at or datetime.now(timezone.utc)
            deadline_dt = ticket.sla_deadline or (created_dt + timedelta(hours=ticket.sla_hours))
            created_str = created_dt.strftime("%d %b %Y, %I:%M %p")
            deadline_str = deadline_dt.strftime("%d %b %Y, %I:%M %p")

            answer_text = (
                f"I have escalated your request and registered a priority support ticket for your **{inherited_category}** case:\n\n"
                f"📋 **Ticket Reference:** #{ticket.ticket_number}\n"
                f"🔹 **Category:** {ticket.category}\n"
                f"🔹 **Case Type:** {ticket.case_type}\n"
                f"🔹 **Title:** {ticket.title}\n"
                f"🔹 **Assigned Desk:** {assignee_text}\n"
                f"🕐 **Ticket Created:** {created_str}\n"
                f"⏱️ **SLA Resolution Window:** {ticket.sla_hours} Hours (RBI/NPCI Standard)\n"
                f"📅 **Target Resolution Deadline:** {deadline_str}\n\n"
                f"Our **{inherited_category} support executive** has been assigned with your complete request and will investigate within the {ticket.sla_hours}-hour SLA window. You can track this ticket anytime from your Overview tab."
            )

            return finalize({
                "answer": answer_text,
                "mode": "banking_agent",
                "source": f"Escalated Support ({inherited_category})",
                "category": inherited_category,
                "intent": f"{inherited_category}_ESCALATED_TO_SUPPORT",
                "case_type": "Complaint",
                "clarification_options": [],
                "ticket_created": True,
                "ticket": ticket_data,
            })
        else:
            answer_text = (
                "Which banking service or department would you like to escalate your request to?\n\n"
                "• 💳 **Debit & Credit Cards** (block card, unauthorized charge, PIN)\n"
                "• 💸 **UPI & Digital Payments** (failed transaction, refund, UPI PIN)\n"
                "• 🏧 **ATM Cash Withdrawals** (cash not dispensed, swallowed card)\n"
                "• 📄 **Account & Balance** (statements, balance hold, transfer timings)\n"
                "• 📑 **KYC & Account Access** (re-KYC update, dormant account)\n\n"
                "Select a department below and I will immediately register a support ticket for you:"
            )
            return finalize({
                "answer": answer_text,
                "mode": "banking_agent",
                "source": "Escalation Desk",
                "category": "General",
                "intent": "ESCALATION_NEEDS_CATEGORY",
                "case_type": "Inquiry",
                "clarification_options": [
                    "Connect to Cards Support",
                    "Connect to UPI Support",
                    "Connect to ATM Support",
                    "Connect to Account Support",
                    "Connect to KYC Support",
                ],
                "ticket_created": False,
                "ticket": None,
            })

    # -------------------------------------------------------------
    # CASE: Unresolved Guidance / Solution Did Not Work Escalation
    # e.g., "this solution not working", "it didn't work", "still not working"
    # -------------------------------------------------------------
    if is_unresolved_solution_followup(cleaned_query):
        prev_ctx = get_previous_turn_context(customer.id if customer else 0, history, current_query=cleaned_query)
        if prev_ctx and prev_ctx.get("query"):
            inherited_category = prev_ctx.get("category") or "General"
            if inherited_category in ("General", "Account", None):
                detected = detect_category(prev_ctx["query"])
                if detected and detected != "General":
                    inherited_category = detected
                elif "upi" in prev_ctx["query"].lower():
                    inherited_category = "UPI"
                elif "atm" in prev_ctx["query"].lower():
                    inherited_category = "ATM"
                elif "card" in prev_ctx["query"].lower():
                    inherited_category = "Cards"
                elif "kyc" in prev_ctx["query"].lower():
                    inherited_category = "KYC"
                else:
                    inherited_category = "Account"

            prev_q = prev_ctx["query"]
            prev_topic = prev_ctx.get("topic") or "Self-service Guidance"

            clean_prev_title = prev_topic if prev_topic not in ("no_match", "general_guidance", "General Inquiry", "greeting") else prev_q[:40]
            title = f"{inherited_category} Issue: {clean_prev_title} - Solution Not Working"

            description = (
                f"Original Customer Request: {prev_q}\n"
                f"AI Knowledge Guidance Provided: {prev_topic}\n"
                f"Customer Feedback / Problem: {cleaned_query}\n\n"
                f"Summary: The customer followed the automated banking instructions provided by BankAssist AI, "
                f"but reported that the solution did not resolve their issue. Automatically escalated to "
                f"{inherited_category} L1 Support for manual review, system verification, and direct assistance."
            )

            # Policy guidance for inherited category
            cat_topic = find_knowledge_topic(prev_q, category=inherited_category)
            if not cat_topic:
                cat_topic = find_knowledge_topic(f"{inherited_category} support", category=inherited_category)
            policy_note = cat_topic.get("policy", f"Standard {inherited_category} turnaround time guidelines apply.") if cat_topic else f"Standard {inherited_category} dispute escalation procedure."
            ai_summary = f"Identified category: {inherited_category}. Suggested priority: Normal. Applicable policy: {policy_note}"

            priority = "High" if inherited_category in ("ATM", "Cards") else "Normal"

            ticket = create_and_route_ticket(
                db=db,
                customer=customer,
                title=title,
                description=description,
                category=inherited_category,
                priority=priority,
                ai_summary=ai_summary,
                case_type="Complaint",
            )
            ticket_data = format_ticket_dict(ticket)

            assigned_team = ticket.assigned_tier
            assignee_text = f"assigned to our {assigned_team} team"
            if ticket.assigned_to:
                assignee_text += f" (Specialist: {ticket.assigned_to.username})"

            created_dt = ticket.created_at or datetime.now(timezone.utc)
            deadline_dt = ticket.sla_deadline or (created_dt + timedelta(hours=ticket.sla_hours))
            created_str = created_dt.strftime("%d %b %Y, %I:%M %p")
            deadline_str = deadline_dt.strftime("%d %b %Y, %I:%M %p")

            answer_text = (
                f"I understand that the solution provided for your **{inherited_category}** query (_{prev_q}_) did not resolve the issue.\n\n"
                f"I have escalated your case and registered a priority support ticket with our specialist team:\n\n"
                f"📋 **Ticket Reference:** #{ticket.ticket_number}\n"
                f"🔹 **Category:** {ticket.category}\n"
                f"🔹 **Case Type:** {ticket.case_type}\n"
                f"🔹 **Title:** {ticket.title}\n"
                f"🔹 **Assigned Desk:** {assignee_text}\n"
                f"🕐 **Ticket Created:** {created_str}\n"
                f"⏱️ **SLA Resolution Window:** {ticket.sla_hours} Hours (RBI/NPCI Standard)\n"
                f"📅 **Target Resolution Deadline:** {deadline_str}\n\n"
                f"Our specialized **{inherited_category} support desk** has been assigned with your conversation details and will resolve your case within the {ticket.sla_hours}-hour SLA window. You can monitor progress anytime from your Overview tab."
            )

            return finalize({
                "answer": answer_text,
                "mode": "banking_agent",
                "source": f"Escalated Support ({inherited_category})",
                "category": inherited_category,
                "intent": f"{inherited_category}_SOLUTION_NOT_WORKING",
                "case_type": "Complaint",
                "clarification_options": [],
                "ticket_created": True,
                "ticket": ticket_data,
            })
        else:
            answer_text = (
                "Could you please specify which banking service or solution is not working?\n\n"
                "For example:\n"
                "• 💸 **UPI & Digital Payments** (failed transfer, reset UPI PIN)\n"
                "• 💳 **Debit & Credit Cards** (block card, PIN change, online payments)\n"
                "• 🏧 **ATM Cash Withdrawals** (cash not dispensed, machine error)\n"
                "• 📄 **Account & Balance** (statements, balance hold, transfer timings)\n\n"
                "Once you provide the details or select an option below, I can open a ticket with the right support specialist or provide targeted help."
            )
            return finalize({
                "answer": answer_text,
                "mode": "banking_agent",
                "source": "Clarification",
                "category": "General",
                "intent": "UNRESOLVED_SOLUTION_NEEDS_CONTEXT",
                "case_type": "Inquiry",
                "clarification_options": [
                    "UPI PIN / Payment Issue",
                    "ATM Cash Dispense Issue",
                    "Card Transaction / Block",
                    "Account Statement / Balance",
                ],
                "ticket_created": False,
                "ticket": None,
            })

    # -------------------------------------------------------------
    # CASE: Clarification / Didn't Get / Confusion on Previous Topic
    # e.g., "i didnt get", "didn't understand", "not clear"
    # -------------------------------------------------------------
    if is_clarification_or_didnt_get_followup(cleaned_query):
        prev_ctx = get_previous_turn_context(customer.id if customer else 0, history, current_query=cleaned_query)
        if prev_ctx and prev_ctx.get("query"):
            inherited_category = prev_ctx.get("category") or "General"
            if inherited_category in ("General", "Account", None):
                detected = detect_category(prev_ctx["query"])
                if detected and detected != "General":
                    inherited_category = detected
                elif "card" in prev_ctx["query"].lower():
                    inherited_category = "Cards"
                elif "upi" in prev_ctx["query"].lower():
                    inherited_category = "UPI"
                elif "atm" in prev_ctx["query"].lower():
                    inherited_category = "ATM"
                elif "kyc" in prev_ctx["query"].lower():
                    inherited_category = "KYC"
                else:
                    inherited_category = "Account"

            prev_q = prev_ctx["query"]
            prev_topic = prev_ctx.get("topic") or "Your previous request"

            # CARDS CLARIFICATION:
            if inherited_category == "Cards":
                answer_text = (
                    f"I understand that you need simpler clarification or haven't received what you needed regarding your **Cards** request (_{prev_topic}_).\n\n"
                    "Here are the immediate steps and options:\n\n"
                    "1. 📱 **To Block Your Card Right Away:**\n"
                    "   • **App:** Open your Mobile Banking app > Tap **Cards** > Select Card > Tap **Block Card**.\n"
                    "   • **SMS:** Send `BLOCK <last 4 digits>` to **567676** from your registered mobile number.\n"
                    "   • **Helpline:** Call our 24x7 emergency card helpline at **1800-123-4567**.\n\n"
                    "2. 📬 **Didn't Receive Your Replacement Card?**\n"
                    "   • Replacement cards are dispatched via speed post within 3 to 5 business days after blocking.\n"
                    "   • If it has been more than 5 days, our Cards Support desk can track the courier AWB or re-dispatch.\n\n"
                    "Would you like to open a direct support ticket with our **Cards Specialist (Anita Sharma)** to assist you?"
                )
                clarification_options = [
                    "Connect to Cards Support",
                    "Block Card Immediately",
                    "Report Unauthorized Charge",
                ]
            # UPI CLARIFICATION:
            elif inherited_category == "UPI":
                answer_text = (
                    f"Let me break down the steps very simply for your **UPI** request (_{prev_topic}_):\n\n"
                    "1. Open your UPI app (Google Pay / PhonePe / Paytm).\n"
                    "2. Tap your **Profile picture** > Select your **Bank Account**.\n"
                    "3. Tap **'Reset UPI PIN'** or **'Forgot PIN'**.\n"
                    "4. Enter the last 6 digits & expiry date of your Debit Card, then enter the OTP received on SMS.\n"
                    "5. Set your new 4 or 6 digit UPI PIN.\n\n"
                    "If you didn't receive the OTP or your payment is stuck, would you like me to connect you to our **UPI Support Specialist (Rajesh Kumar)**?"
                )
                clarification_options = [
                    "Connect to UPI Support",
                    "Failed UPI Transfer",
                    "Daily Transaction Limit",
                ]
            # ATM CLARIFICATION:
            elif inherited_category == "ATM":
                answer_text = (
                    f"Let me clarify the steps for your **ATM** request (_{prev_topic}_):\n\n"
                    "• If the ATM **did not dispense cash** but money was debited, the standard auto-reversal timeline is **T+5 business days**.\n"
                    "• If your **card was retained/swallowed** by the ATM machine, it is securely destroyed for your protection and a replacement is dispatched.\n\n"
                    "Would you like me to register an ATM dispute ticket with our **ATM Specialist (Suresh Patel)**?"
                )
                clarification_options = [
                    "Connect to ATM Support",
                    "Cash Not Dispensed",
                    "ATM Withdrawal Limits",
                ]
            # KYC CLARIFICATION:
            elif inherited_category == "KYC":
                answer_text = (
                    f"Let me explain the **KYC verification process** in 3 simple points:\n\n"
                    "1. **No change in address/details?** Submit a simple online self-declaration via Net Banking or Mobile Banking — no branch visit required.\n"
                    "2. **Address changed?** Upload your updated Aadhaar via DigiLocker OTP or complete Video KYC.\n"
                    "3. **Officially Valid Documents:** Passport, Driving License, Aadhaar, or Voter ID.\n\n"
                    "Would you like our **KYC Specialist (Deepak Verma)** to assist you?"
                )
                clarification_options = [
                    "Connect to KYC Support",
                    "Periodic Re-KYC Steps",
                    "Acceptable Documents",
                ]
            # ACCOUNT / GENERAL CLARIFICATION:
            else:
                answer_text = (
                    f"Let me clarify this for your **Account** request (_{prev_topic}_):\n\n"
                    "• You can check real-time available balance on your **Overview** dashboard.\n"
                    "• Download official PDF statements from Net Banking > Accounts > e-Statement.\n"
                    "• For funds transfer (NEFT/RTGS/IMPS), ensure the beneficiary IFSC code and account number match.\n\n"
                    "Would you like to connect to our **Account Specialist (Kavita Rao)** for assistance?"
                )
                clarification_options = [
                    "Connect to Account Support",
                    "Check Balance & Statement",
                    "Fund Transfer Timings",
                ]

            return finalize({
                "answer": answer_text,
                "mode": "banking_agent",
                "source": f"Guidance Clarification ({inherited_category})",
                "category": inherited_category,
                "intent": f"{inherited_category}_CLARIFICATION",
                "case_type": "Inquiry",
                "clarification_options": clarification_options,
                "ticket_created": False,
                "ticket": None,
            })

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
        return finalize({
            "answer": greeting_msg,
            "mode": "banking_agent",
            "source": "greeting",
            "category": "General",
            "intent": "GREETING",
            "clarification_options": [],
            "ticket_created": False,
            "ticket": None,
        })

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
        return finalize({
            "answer": overview_msg,
            "mode": "banking_agent",
            "source": "Account & Balance Services",
            "category": "Account",
            "intent": "ACCOUNT_CATEGORY_OVERVIEW",
            "case_type": intent_res.case_type,
            "clarification_options": [
                "Check Balance & Statement",
                "Fund Transfer Timings",
                "My Profile Details",
            ],
            "ticket_created": False,
            "ticket": None,
        })

    if intent_res.intent_name == "UPI_CATEGORY_OVERVIEW":
        overview_msg = (
            "You are asking about **UPI & Digital Payments**.\n\n"
            "Here are the key UPI services and guidelines:\n\n"
            "• 💸 **Failed UPI Transfer with Money Debited:** Standard auto-reversal is completed within **T+1 business days**. If it has exceeded 24 hours, we can open a dispute ticket with your UTR number.\n"
            "• 📊 **Daily Transaction Limits:** Standard NPCI limit allows up to **20 transactions** or **₹1,00,000 per day**.\n"
            "• 🔑 **Reset UPI PIN:** Go to your UPI app, select the bank account, and verify using the last 6 digits of your debit card and OTP.\n\n"
            "Could you please confirm what UPI assistance you need?"
        )
        return finalize({
            "answer": overview_msg,
            "mode": "banking_agent",
            "source": "UPI & Digital Payments",
            "category": "UPI",
            "intent": "UPI_CATEGORY_OVERVIEW",
            "case_type": intent_res.case_type,
            "clarification_options": [
                "Failed UPI Transfer",
                "Daily Transaction Limit",
                "Reset UPI PIN",
            ],
            "ticket_created": False,
            "ticket": None,
        })

    if intent_res.intent_name == "ATM_CATEGORY_OVERVIEW":
        overview_msg = (
            "You are asking about **ATM Cash Withdrawals**.\n\n"
            "Here is the key guidance for ATM services:\n\n"
            "• 🏧 **Cash Not Dispensed but Debited:** Under RBI mandate, banks must resolve failed ATM cash dispense within **T+5 business days**, failing which compensation of **₹100 per day** of delay is payable.\n"
            "• 💳 **Daily Cash Limits:** Standard debit cards allow **₹20,000 to ₹50,000** in daily ATM cash withdrawals (typically 3 to 5 financial withdrawals per day).\n"
            "• 🛑 **Card Swallowed by ATM:** If the ATM machine retained your debit card, the card is destroyed securely for safety and a replacement is dispatched within 3-5 business days.\n\n"
            "Could you please confirm what ATM assistance you need?"
        )
        return finalize({
            "answer": overview_msg,
            "mode": "banking_agent",
            "source": "ATM Withdrawals",
            "category": "ATM",
            "intent": "ATM_CATEGORY_OVERVIEW",
            "case_type": intent_res.case_type,
            "clarification_options": [
                "Cash Not Dispensed",
                "ATM Withdrawal Limits",
                "Card Retained in ATM",
            ],
            "ticket_created": False,
            "ticket": None,
        })

    if intent_res.intent_name == "CARD_CATEGORY_OVERVIEW":
        overview_msg = (
            "You are asking about **Debit & Credit Cards**.\n\n"
            "Here are the key card safety and usage guidelines:\n\n"
            "• 🛡️ **Lost / Stolen Card (Instant Block):** You can block your card instantly via your mobile banking app or by contacting our 24/7 hotline to prevent unauthorized transactions.\n"
            "• ⚠️ **Report Unauthorized Charges:** Under RBI's zero-liability policy, reporting fraud within **3 business days** ensures zero customer liability.\n"
            "• 🌐 **Online & International Usage:** Enable or disable domestic online, contactless (tap & pay), or international spending anytime in your app.\n\n"
            "Could you please confirm what card assistance you need?"
        )
        return finalize({
            "answer": overview_msg,
            "mode": "banking_agent",
            "source": "Debit & Credit Cards",
            "category": "Cards",
            "intent": "CARD_CATEGORY_OVERVIEW",
            "case_type": intent_res.case_type,
            "clarification_options": [
                "Block Card Immediately",
                "Report Unauthorized Charge",
                "Card Online Usage",
            ],
            "ticket_created": False,
            "ticket": None,
        })

    if intent_res.intent_name == "KYC_CATEGORY_OVERVIEW":
        overview_msg = (
            "You are asking about **Account Access & KYC Verification**.\n\n"
            "Here is the verified guidance for account access and KYC:\n\n"
            "• 📑 **Periodic Re-KYC Update:** Low-risk customers require re-KYC every 10 years, medium-risk every 8 years, and high-risk every 2 years. If no details changed, submit a self-declaration online.\n"
            "• 🔒 **Dormant / Inoperative Account:** If no customer-induced transaction occurred in 2 years, your account is marked dormant. Reactivate by visiting your branch with original KYC documents.\n"
            "• 🪪 **Officially Valid Documents:** Passport, Driving License, Proof of possession of Aadhaar, Voter's Identity Card, or NREGA Job Card.\n\n"
            "Could you please confirm what KYC or account access help you need?"
        )
        return finalize({
            "answer": overview_msg,
            "mode": "banking_agent",
            "source": "Account Access & KYC",
            "category": "KYC",
            "intent": "KYC_CATEGORY_OVERVIEW",
            "case_type": intent_res.case_type,
            "clarification_options": [
                "Periodic Re-KYC Steps",
                "Dormant Account Activation",
                "Acceptable Documents",
            ],
            "ticket_created": False,
            "ticket": None,
        })

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
        return finalize({
            "answer": clarification_answer,
            "mode": "banking_agent",
            "source": "Daily Transaction Limits",
            "category": "UPI",
            "intent": "DAILY_TRANSACTION_LIMIT",
            "case_type": intent_res.case_type,
            "clarification_options": ["UPI Transactions", "ATM Withdrawals", "Debit/Credit Cards"],
            "ticket_created": False,
            "ticket": None,
        })

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
        return finalize({
            "answer": profile_answer,
            "mode": "banking_agent",
            "source": "Account Profile",
            "category": "Account",
            "intent": "ACCOUNT_PROFILE_INQUIRY",
            "case_type": "Inquiry",
            "clarification_options": [],
            "ticket_created": False,
            "ticket": None,
        })

    # -------------------------------------------------------------
    # CASE 1C: Ticket Status & Support Reply Inquiry
    # -------------------------------------------------------------
    ticket_num_match = re.search(r"\b(TK-[A-Za-z0-9\-]+)\b", cleaned_query, re.IGNORECASE)
    lower_query = cleaned_query.lower()
    is_status_query = bool(
        ticket_num_match
        or "ticket status" in lower_query
        or "dispute status" in lower_query
        or "status of my ticket" in lower_query
        or "track ticket" in lower_query
        or "support reply" in lower_query
        or "reply to customer" in lower_query
        or "check my ticket" in lower_query
    )

    if is_status_query and customer:
        query_builder = db.query(Ticket).filter(Ticket.customer_id == customer.id)
        target_ticket = None
        if ticket_num_match:
            searched_num = ticket_num_match.group(1).upper()
            target_ticket = query_builder.filter(Ticket.ticket_number == searched_num).first()
        else:
            target_ticket = query_builder.order_by(Ticket.created_at.desc()).first()

        if target_ticket:
            desk_info = target_ticket.assigned_to.username if target_ticket.assigned_to else target_ticket.assigned_tier
            sla_text = target_ticket.sla_deadline.strftime("%d %b %Y, %I:%M %p") if target_ticket.sla_deadline else f"{target_ticket.sla_hours} hours"
            
            if target_ticket.resolution_notes:
                reply_section = f"💬 **Official Bank Reply:**\n> \"{target_ticket.resolution_notes}\""
            else:
                reply_section = f"⏳ **Support Status:** Active investigation by {desk_info}. The official resolution reply will be posted within SLA turnaround."

            status_response = (
                f"Here is the latest live status for your dispute:\n\n"
                f"🎫 **Ticket Reference:** #{target_ticket.ticket_number}\n"
                f"📌 **Category:** {target_ticket.category}\n"
                f"⚡ **Current Status:** {target_ticket.status}\n"
                f"🎧 **Assigned Support Desk:** {desk_info} ({target_ticket.assigned_tier})\n"
                f"⏱️ **SLA Target:** {sla_text}\n\n"
                f"{reply_section}\n\n"
                "You can also click **'🔍 View Reply'** in your **My Active Disputes** table below to see the full event timeline and attached evidence."
            )
            return finalize({
                "answer": status_response,
                "mode": "banking_agent",
                "source": "Ticket Management",
                "category": target_ticket.category,
                "intent": "TICKET_STATUS_INQUIRY",
                "case_type": "Inquiry",
                "clarification_options": [],
                "ticket_created": False,
                "ticket": format_ticket_dict(target_ticket),
            })

    # -------------------------------------------------------------
    # CASE 1D: Customer Feedback or Suggestions
    # -------------------------------------------------------------
    if intent_res.case_type == "Feedback":
        feedback_reply = (
            "🙏 **Thank you for sharing your feedback with BankAssist!**\n\n"
            "We value your suggestions and experience. Your feedback has been recorded and shared with our customer service and product teams to help us improve our banking services and digital applications.\n\n"
            "If there is any specific transaction issue, account service, or dispute you would like us to investigate, please let us know anytime!"
        )
        return finalize({
            "answer": feedback_reply,
            "mode": "banking_agent",
            "source": "Customer Feedback Desk",
            "category": "General",
            "intent": "CUSTOMER_FEEDBACK",
            "case_type": "Feedback",
            "clarification_options": [],
            "ticket_created": False,
            "ticket": None,
        })

    category = intent_res.category
    priority = intent_res.suggested_priority

    # Inherit active category from prior context if current category is General
    if category in ("General", None):
        prev_ctx = get_previous_turn_context(customer.id if customer else 0, history, current_query=cleaned_query)
        if prev_ctx and prev_ctx.get("category") and prev_ctx["category"] != "General":
            category = prev_ctx["category"]

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
            case_type=intent_res.case_type,
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
                assignee_text += f" (Specialist: {ticket.assigned_to.username})"

            created_dt = ticket.created_at or datetime.now(timezone.utc)
            deadline_dt = ticket.sla_deadline or (created_dt + timedelta(hours=ticket.sla_hours))
            created_str = created_dt.strftime("%d %b %Y, %I:%M %p")
            deadline_str = deadline_dt.strftime("%d %b %Y, %I:%M %p")

            answer_text = (
                f"We have registered your dispute regarding your {category} query.\n\n"
                f"📋 **Ticket Reference:** #{ticket.ticket_number}\n"
                f"🔹 **Category:** {ticket.category}\n"
                f"🔹 **Case Type:** {ticket.case_type}\n"
                f"🔹 **Priority:** {ticket.priority}\n"
                f"🔹 **Assigned Desk:** {assignee_text}\n"
                f"🕐 **Ticket Created:** {created_str}\n"
                f"⏱️ **SLA Resolution Window:** {ticket.sla_hours} Hours (RBI/NPCI Grounded)\n"
                f"📅 **Target Resolution Deadline:** {deadline_str}\n\n"
                f"**Turnaround Guidance:**\n{guidance}\n\n"
                f"Our banking support desk has been assigned and will investigate your case within the {ticket.sla_hours}-hour SLA guarantee. You can monitor live progress and upload supporting evidence anytime from your Overview tab."
            )
            if not provider_configured:
                mode = "banking_agent"

        return finalize({
            "answer": answer_text,
            "mode": mode,
            "source": f"Banking Dispute Resolution ({category})",
            "category": category,
            "intent": intent_res.intent_name,
            "case_type": intent_res.case_type,
            "clarification_options": [],
            "ticket_created": True,
            "ticket": ticket_data,
        })

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

        return finalize({
            "answer": answer_text,
            "mode": mode,
            "source": source,
            "category": category,
            "intent": intent_res.intent_name,
            "case_type": intent_res.case_type,
            "clarification_options": [],
            "ticket_created": False,
            "ticket": None,
        })


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
