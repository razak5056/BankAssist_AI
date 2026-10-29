"""
Intent Classification Engine for BankAssist AI.
Classifies customer queries into structured banking intents, categories,
and determines whether an informational response or dispute ticket is required.
"""

from dataclasses import dataclass, field
from typing import Optional
import re


@dataclass
class IntentResult:
    intent_name: str
    category: str
    is_dispute: bool
    suggested_priority: str = "Normal"
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: list[str] = field(default_factory=list)
    confidence: float = 1.0


# Normalized keywords and regex patterns
GREETING_PATTERNS = [
    r"^(hi|hello|hey|hola|greetings|good\s+(morning|afternoon|evening)|howdy)\b",
    r"^(who\s+are\s+you|what\s+can\s+you\s+do|help\s+me)\b",
]

# Dispute patterns (customer experiencing an active problem requiring human support)
DISPUTE_INDICATORS = [
    r"\b(failed|fail|failure|unsuccessful|declined)\b",
    r"\b(debited|deducted|cut|charged|lost|stolen)\b",
    r"\b(not (received|credited|dispensed|refunded|updated|working))\b",
    r"\b(unauthorized|fraud|scam|dispute|complaint|grievance|problem|issue)\b",
    r"\b(frozen|blocked|freeze|locked|suspended|lien|rejected)\b",
    r"\b(raise (a )?ticket|create (a )?ticket|escalate|talk to human|agent)\b",
    r"\b(cash (did not|didnt|didn't) come|money (did not|didnt|didn't) come)\b",
]

# Informational / Guidance patterns
LIMIT_PATTERNS = [
    r"\b(how\s+many|how\s+much|limit|limits|maximum|max|allowed|cap|daily\s+limit|per\s+day)\b",
]


def classify_intent(query: str) -> IntentResult:
    """
    Classifies customer banking queries into high-precision intents.
    Distinguishes informational inquiries from actionable disputes.
    """
    q = query.strip().lower()
    clean_q = re.sub(r"[^\w\s]", " ", q)
    words = clean_q.split()

    # -------------------------------------------------------------------------
    # 1. GREETING INTENT
    # -------------------------------------------------------------------------
    if any(re.search(pat, q) for pat in GREETING_PATTERNS) and len(words) <= 4:
        return IntentResult(
            intent_name="GREETING",
            category="General",
            is_dispute=False,
            suggested_priority="Low",
        )

    # -------------------------------------------------------------------------
    # 2. CHECK FOR DISPUTE / COMPLAINT (Ticket Required)
    # -------------------------------------------------------------------------
    has_dispute_indicator = any(re.search(pat, q) for pat in DISPUTE_INDICATORS)

    # Specific Dispute: ATM Cash Not Dispensed
    if re.search(r"\b(atm|cash machine)\b", q) and re.search(r"\b(not dispensed|deducted|debited|stuck|captured|retained|didnt come)\b", q):
        priority = "High"
        return IntentResult(
            intent_name="ATM_CASH_DISPENSE_FAILURE",
            category="ATM",
            is_dispute=True,
            suggested_priority=priority,
        )

    # Specific Dispute: UPI Transaction Failed but Debited
    if re.search(r"\b(upi|gpay|phonepe|paytm|bhim|qr|vpa)\b", q) and re.search(r"\b(failed|debited|deducted|pending|not credited|not received)\b", q):
        return IntentResult(
            intent_name="UPI_TRANSACTION_FAILURE",
            category="UPI",
            is_dispute=True,
            suggested_priority="Normal",
        )

    # Specific Dispute: Unauthorized / Fraudulent Card Charge
    if re.search(r"\b(unauthorized|fraud|scam|stolen|stole|compromised|unknown charge|unknown transaction)\b", q):
        category = "Cards" if re.search(r"\b(card|credit|debit|pos|swipe|online)\b", q) else "UPI" if re.search(r"\b(upi|gpay|phonepe)\b", q) else "Account"
        return IntentResult(
            intent_name="UNAUTHORIZED_FRAUD_DISPUTE",
            category=category,
            is_dispute=True,
            suggested_priority="Urgent",
        )

    # Specific Dispute: Account Frozen / Lien / Debit Freeze
    if re.search(r"\b(account)\b", q) and re.search(r"\b(frozen|freeze|lien|locked|blocked|cannot withdraw)\b", q):
        return IntentResult(
            intent_name="ACCOUNT_RESTRICTION_DISPUTE",
            category="Account",
            is_dispute=True,
            suggested_priority="High",
        )

    # Specific Dispute: KYC Rejected / Blocked
    if re.search(r"\b(kyc)\b", q) and re.search(r"\b(rejected|failed|blocked|pending\s+for\s+\d+|delayed)\b", q):
        return IntentResult(
            intent_name="KYC_VERIFICATION_DISPUTE",
            category="KYC",
            is_dispute=True,
            suggested_priority="Normal",
        )

    # General Dispute / Direct Ticket Request
    if has_dispute_indicator:
        # Deduce category
        if re.search(r"\b(upi|gpay|phonepe|paytm|bhim)\b", q):
            category = "UPI"
        elif re.search(r"\b(atm|cash machine|dispensed)\b", q):
            category = "ATM"
        elif re.search(r"\b(card|debit card|credit card|cvv|swipe)\b", q):
            category = "Cards"
        elif re.search(r"\b(kyc|re-kyc|aadhaar|pan)\b", q):
            category = "KYC"
        else:
            category = "Account"

        priority = "Urgent" if re.search(r"\b(urgent|emergency|immediately|stolen)\b", q) else "High" if category in ("ATM", "Cards") else "Normal"

        return IntentResult(
            intent_name="GENERAL_DISPUTE",
            category=category,
            is_dispute=True,
            suggested_priority=priority,
        )

    # -------------------------------------------------------------------------
    # 3. INFORMATIONAL INQUIRIES (NO Ticket Created)
    # -------------------------------------------------------------------------

    # Direct selection of clarification options
    if q in ("upi transactions", "upi transaction", "upi payments", "upi payment", "upi"):
        return IntentResult(
            intent_name="UPI_TRANSACTION_LIMIT",
            category="UPI",
            is_dispute=False,
            needs_clarification=False,
        )
    if q in ("atm withdrawals", "atm withdrawal", "atm cash", "atm"):
        return IntentResult(
            intent_name="ATM_WITHDRAWAL_LIMIT",
            category="ATM",
            is_dispute=False,
            needs_clarification=False,
        )
    if q in ("debit/credit cards", "debit and credit cards", "debit cards", "credit cards", "cards", "card usage"):
        return IntentResult(
            intent_name="CARD_USAGE_LIMIT",
            category="Cards",
            is_dispute=False,
            needs_clarification=False,
        )

    # Intent: Transaction Limits (e.g. "how many transaction will i done per day")
    is_asking_limits = any(re.search(pat, q) for pat in LIMIT_PATTERNS) and (
        re.search(r"\b(transaction|transactions|transfer|transfers|payment|payments|withdraw|withdrawal|done|make|send)\b", q)
        or re.search(r"\b(per\s+day|daily|in\s+a\s+day|day)\b", q)
    )

    if is_asking_limits:
        # Check if customer specified the payment method
        has_upi = bool(re.search(r"\b(upi|gpay|phonepe|paytm|bhim|digital)\b", q))
        has_atm = bool(re.search(r"\b(atm|cash|withdraw|withdrawal)\b", q))
        has_card = bool(re.search(r"\b(card|debit|credit|pos|swipe|online)\b", q))

        if has_upi and not has_atm:
            return IntentResult(
                intent_name="UPI_TRANSACTION_LIMIT",
                category="UPI",
                is_dispute=False,
                needs_clarification=False,
            )
        elif has_atm and not has_upi:
            return IntentResult(
                intent_name="ATM_WITHDRAWAL_LIMIT",
                category="ATM",
                is_dispute=False,
                needs_clarification=False,
            )
        elif has_card and not has_upi and not has_atm:
            return IntentResult(
                intent_name="CARD_USAGE_LIMIT",
                category="Cards",
                is_dispute=False,
                needs_clarification=False,
            )
        else:
            # Ambiguous limit question (e.g. "how many transaction will i done per day")
            return IntentResult(
                intent_name="GENERAL_TRANSACTION_LIMIT",
                category="UPI",
                is_dispute=False,
                needs_clarification=True,
                clarification_question="Could you please confirm whether you are asking about UPI transactions, ATM withdrawals, or Debit/Credit card usage?",
                clarification_options=["UPI Transactions", "ATM Withdrawals", "Debit/Credit Cards"],
            )

    # Intent: PIN Reset (UPI or ATM)
    if re.search(r"\b(pin|password)\b", q) and re.search(r"\b(reset|forgot|change|new|create|generate)\b", q):
        category = "ATM" if "atm" in q else "UPI"
        return IntentResult(
            intent_name="PIN_RESET_GUIDANCE",
            category=category,
            is_dispute=False,
        )

    # -------------------------------------------------------------------------
    # CATEGORY OVERVIEWS (from Dashboard Category Buttons or General Category Prompts)
    # -------------------------------------------------------------------------
    if (
        re.search(r"\b(account\s+(and|or)\s+balance|question about (my\s+)?account|help with (my\s+)?account)\b", q)
        and not re.search(r"\b(check|how to|download|mini|passbook)\b", q)
        and not has_dispute_indicator
        and not re.search(r"\b(freeze|frozen|lien|block|failed|kyc|access)\b", q)
    ):
        return IntentResult(
            intent_name="ACCOUNT_CATEGORY_OVERVIEW",
            category="Account",
            is_dispute=False,
            needs_clarification=True,
            clarification_question="What specific Account & Balance assistance do you need?",
            clarification_options=["Check Balance & Statement", "Fund Transfer Timings", "My Profile Details"],
        )

    if (
        re.search(r"\b(upi(\s+or|\s+and)?\s+digital payment|help with (a\s+)?upi|digital payments)\b", q)
        and not has_dispute_indicator
    ):
        return IntentResult(
            intent_name="UPI_CATEGORY_OVERVIEW",
            category="UPI",
            is_dispute=False,
            needs_clarification=True,
            clarification_question="What UPI assistance do you require?",
            clarification_options=["Failed UPI Transfer", "Daily Transaction Limit", "Reset UPI PIN"],
        )

    if (
        re.search(r"\b(help with (an\s+)?atm|atm withdrawal|cash withdrawal|atm withdrawals)\b", q)
        and not has_dispute_indicator
    ):
        return IntentResult(
            intent_name="ATM_CATEGORY_OVERVIEW",
            category="ATM",
            is_dispute=False,
            needs_clarification=True,
            clarification_question="What ATM assistance do you require?",
            clarification_options=["Cash Not Dispensed", "ATM Withdrawal Limits", "Card Retained in ATM"],
        )

    if (
        re.search(r"\b(help with (my\s+)?(debit|credit\s+)?card|debit(\s+and|\s+or)?\s+credit card)\b", q)
        and not has_dispute_indicator
    ):
        return IntentResult(
            intent_name="CARD_CATEGORY_OVERVIEW",
            category="Cards",
            is_dispute=False,
            needs_clarification=True,
            clarification_question="What Debit/Credit card assistance do you require?",
            clarification_options=["Block Card Immediately", "Report Unauthorized Charge", "Card Online Usage"],
        )

    if (
        re.search(r"\b(account access(\s+or|\s+and)?\s+kyc|help with (account access|kyc))\b", q)
        and not has_dispute_indicator
    ):
        return IntentResult(
            intent_name="KYC_CATEGORY_OVERVIEW",
            category="KYC",
            is_dispute=False,
            needs_clarification=True,
            clarification_question="What KYC or Account Access help do you need?",
            clarification_options=["Periodic Re-KYC Steps", "Dormant Account Activation", "Acceptable KYC Documents"],
        )

    # Intent: Explicit Account Profile / Information (e.g. "i need my account information")
    profile_patterns = [
        r"\b(account\s+(info|information|details))\b",
        r"\b(my\s+(profile|account\s+info|account\s+details|customer\s+id|registered\s+email))\b",
        r"\b(who\s+am\s+i|show\s+my\s+profile|view\s+my\s+profile|my\s+details)\b",
        r"\b(check|show|view|need|get)\s+(my\s+)?(profile|account\s+info|account\s+details|customer\s+id)\b",
    ]
    if (
        any(re.search(pat, q) for pat in profile_patterns)
        and not has_dispute_indicator
        and not is_asking_limits
        and not re.search(r"\b(balance|statement|kyc|transfer|neft|rtgs|imps)\b", q)
    ):
        return IntentResult(
            intent_name="ACCOUNT_PROFILE_INQUIRY",
            category="Account",
            is_dispute=False,
            needs_clarification=False,
        )

    # Intent: Balance or Statement
    if re.search(r"\b(balance|statement|mini statement|passbook|e-statement)\b", q):
        return IntentResult(
            intent_name="BALANCE_STATEMENT_INQUIRY",
            category="Account",
            is_dispute=False,
        )

    # Intent: Card Controls / Enable International / Replacement
    if re.search(r"\b(card)\b", q) and re.search(r"\b(enable|disable|international|contactless|replacement|reissue|block)\b", q):
        return IntentResult(
            intent_name="CARD_MANAGEMENT_INQUIRY",
            category="Cards",
            is_dispute=False,
        )

    # Intent: KYC Process / Guidelines
    if re.search(r"\b(kyc|re-kyc|aadhaar|pan|dormant|inoperative|reactivate)\b", q):
        return IntentResult(
            intent_name="KYC_PROCESS_INQUIRY",
            category="KYC",
            is_dispute=False,
        )

    # Intent: Transfer Modes (NEFT, RTGS, IMPS)
    if re.search(r"\b(neft|rtgs|imps|timing|timings|charges)\b", q):
        return IntentResult(
            intent_name="TRANSFER_MODES_INQUIRY",
            category="Account",
            is_dispute=False,
        )

    # Fallback to General Inquiry
    return IntentResult(
        intent_name="GENERAL_INQUIRY",
        category="General",
        is_dispute=False,
    )
