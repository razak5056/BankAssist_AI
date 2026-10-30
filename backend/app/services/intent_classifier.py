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
    case_type: str = "Inquiry"  # Complaint, Inquiry, Service Request, Feedback


# Normalized keywords and regex patterns
GREETING_PATTERNS = [
    r"^(hi|hello|hey|hola|greetings|good\s+(morning|afternoon|evening)|howdy)\b",
    r"^(who\s+are\s+you|what\s+can\s+you\s+do|help\s+me)\b",
]

# Dispute patterns (customer experiencing an active problem requiring human support)
DISPUTE_INDICATORS = [
    r"\b(failed|fail|failure|unsuccessful|declined)\b",
    r"\b(debited|deducted|cut|charged|lost\s+money|stolen\s+money)\b",
    r"\b(not (received|credited|dispensed|refunded|updated|working))\b",
    r"\b(unauthorized|fraud\w*|scam|dispute|complaint|grievance|problem|issues|issue\s+with|facing\s+(an?\s+)?issue|having\s+(an?\s+)?issue)\b",
    r"\b(frozen|blocked|freeze|locked|suspended|lien|rejected)\b",
    r"\b(raise (a )?ticket|create (a )?ticket|open (a )?ticket|escalate|esclicate|esclate|escalte|escalating|escalation|talk to human|human support|connect to support|agent)\b",
    r"\b(cash (did not|didnt|didn't) come|money (did not|didnt|didn't) come)\b",
]

# Informational / Guidance patterns
LIMIT_PATTERNS = [
    r"\b(how\s+many|how\s+much|limit|limits|maximum|max|allowed|cap|daily\s+limit|per\s+day)\b",
]


def detect_case_type(query: str, intent_name: str = "", is_dispute: bool = False) -> str:
    """
    Classifies the user's query into one of the canonical banking Case Types:
    - 'Complaint': Financial dispute, failed transaction, money deducted, fraud, unauthorized charge, grievance.
    - 'Inquiry': General banking question, limits, timings, interest rates, status check, guidelines.
    - 'Service Request': Asking the bank to perform an action (block card, cancel mandate, re-KYC, PIN change, chequebook).
    - 'Feedback': Suggestions, reviews, appreciation, complaints about branch/staff behavior or app UI.
    """
    q = query.strip().lower()

    # -------------------------------------------------------------------------
    # 1. FEEDBACK (Appreciation, reviews, suggestions, app UI, branch staff behavior)
    # -------------------------------------------------------------------------
    feedback_pattern = (
        r"\b(feedback|suggest|suggestion|suggestions|improve|improvement|"
        r"review|reviews|rating|ratings|stars|compliment|kudos|shoutout|"
        r"great service|bad service|poor service|slow app|love the app|hate the app|"
        r"customer experience|branch staff|staff behavior|rude executive|rude staff|"
        r"thank you|thanks|helpful|very helpful|great work|awesome app|good app|"
        r"user friendly|easy to use|hate this app|worst app|best app)\b"
    )
    if re.search(feedback_pattern, q):
        # Only classify as Feedback if not reporting direct financial loss or fraudulent debit
        if not re.search(r"\b(debited|deducted|cut|lost money|not dispensed|unauthorized|fraud\w*|scam)\b", q):
            return "Feedback"

    # -------------------------------------------------------------------------
    # 2. INFORMATIONAL QUESTIONS (Explicit inquiries for docs, rules, charges, limits)
    # -------------------------------------------------------------------------
    is_informational = bool(
        re.search(r"\b(what documents|what are the documents|which documents|acceptable documents|documents required)\b", q)
        or re.search(r"^(what|how many|how much|when|where|why|charges for|fee for|rules for|guidelines for|meaning of)\b", q)
        or re.search(r"\b(timing|timings|cutoff|limit|limits|interest rate|charges|fees|faqs?)\b", q)
    ) and not re.search(r"\b(block|cancel|stop|issue|reset|update|change)\b", q)

    if is_informational and not is_dispute and not re.search(r"\b(debited|deducted|cut|unauthorized|fraud\w*|failed)\b", q):
        return "Inquiry"

    # -------------------------------------------------------------------------
    # 3. SERVICE REQUEST (Asking the bank to perform an action / fulfillment)
    # -------------------------------------------------------------------------
    is_service_req = bool(
        # Cheque book issuance / request
        re.search(r"\b(cheque|check)\s?book\b", q)
        # Card block / unblock / hotlist / deactivate
        or (re.search(r"\b(block|unblock|freeze|unfreeze|hotlist|deactivate)\b", q) and re.search(r"\b(card|debit|credit|account)\b", q))
        # PIN operations (reset, change, generate, create, green pin)
        or (re.search(r"\b(reset|change|generate|create|forgot|set)\b", q) and re.search(r"\b(pin|password|mpin|tpin)\b", q))
        # Mandate / Autopay cancellation or pause
        or (re.search(r"\b(cancel|stop|pause|revoke|delete|disable)\b", q) and re.search(r"\b(mandate|autopay|standing instruction|si|recurring)\b", q))
        # Card channel controls (enable/disable international, contactless, online)
        or (re.search(r"\b(enable|disable|turn on|turn off|activate)\b", q) and re.search(r"\b(international|contactless|nfc|online|ecommerce|pos)\b", q))
        # Account / Profile updates (address, mobile, email, nominee)
        or (re.search(r"\b(update|change)\b", q) and re.search(r"\b(address|mobile|phone|email|nominee|pan|aadhaar)\b", q))
        # Statement / Certificate download or request
        or (re.search(r"\b(download|send|email|request|get)\b", q) and re.search(r"\b(statement|certificate)\b", q))
        # Periodic Re-KYC completion
        or re.search(r"\b(submit|update|complete|do)\b.*\b(kyc|re-kyc|periodic kyc)\b", q)
    )
    if is_service_req and not re.search(r"\b(debited|deducted|cut|lost money|not dispensed|unauthorized|fraud\w*|scam)\b", q):
        return "Service Request"

    # -------------------------------------------------------------------------
    # 4. COMPLAINT (Financial disputes, failed transactions, debits, ATM failures, fraud)
    # -------------------------------------------------------------------------
    complaint_pattern = (
        r"\b(failed|fail|failure|debited|deducted|cut|charged twice|double debit|overcharged|"
        r"not credited|not received|not dispensed|lost money|money missing|"
        r"fraud\w*|scam|unauthorized|stolen|robbed|dispute|complaint|grievance|"
        r"problem|penalty|wrong debit|did not dispense|didnt dispense|cash stuck)\b"
    )
    if is_dispute or re.search(complaint_pattern, q):
        return "Complaint"

    # -------------------------------------------------------------------------
    # 5. INQUIRY (Default for general questions, FAQs, balance, ticket tracking)
    # -------------------------------------------------------------------------
    return "Inquiry"


def _classify_intent_internal(query: str) -> IntentResult:
    """
    Internal classifier for customer banking queries.
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
    if re.search(r"\b(unauthorized|fraud\w*|scam|stolen|stole|compromised|unknown\s+(fraudulent\s+)?(charge|transaction|debit|payment))\b", q):
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

    # -------------------------------------------------------------------------
    # Direct selection of clarification chips & common direct prompts
    # -------------------------------------------------------------------------
    # Direct support desk connect chips:
    if q in ("connect to cards support", "connect to support agent", "open support ticket", "speak to an agent"):
        return IntentResult(
            intent_name="GENERAL_DISPUTE",
            category="Cards",
            is_dispute=True,
            suggested_priority="Normal",
            case_type="Complaint",
        )
    if q in ("connect to upi support", "upi support"):
        return IntentResult(
            intent_name="GENERAL_DISPUTE",
            category="UPI",
            is_dispute=True,
            suggested_priority="Normal",
            case_type="Complaint",
        )
    if q in ("connect to atm support", "register atm dispute ticket"):
        return IntentResult(
            intent_name="ATM_CASH_DISPENSE_FAILURE",
            category="ATM",
            is_dispute=True,
            suggested_priority="High",
            case_type="Complaint",
        )
    if q in ("connect to kyc support", "kyc support"):
        return IntentResult(
            intent_name="KYC_VERIFICATION_DISPUTE",
            category="KYC",
            is_dispute=True,
            suggested_priority="Normal",
            case_type="Complaint",
        )
    if q in ("connect to account support", "account support"):
        return IntentResult(
            intent_name="GENERAL_DISPUTE",
            category="Account",
            is_dispute=True,
            suggested_priority="Normal",
            case_type="Complaint",
        )

    # Cards chips:
    if q in ("block card immediately", "block card", "block my card", "instant block"):
        return IntentResult(
            intent_name="CARD_BLOCK_GUIDANCE",
            category="Cards",
            is_dispute=False,
            suggested_priority="High",
            case_type="Service Request",
        )
    if q in ("report unauthorized charge", "report unauthorized charges", "unauthorized charge", "report fraud"):
        return IntentResult(
            intent_name="UNAUTHORIZED_FRAUD_DISPUTE",
            category="Cards",
            is_dispute=True,
            suggested_priority="Urgent",
            case_type="Complaint",
        )
    if q in ("card online usage", "online card usage", "card controls", "online usage"):
        return IntentResult(
            intent_name="CARD_USAGE_LIMIT",
            category="Cards",
            is_dispute=False,
            case_type="Inquiry",
        )

    # UPI chips:
    if q in ("failed upi transfer", "failed upi payment", "upi transfer failed"):
        return IntentResult(
            intent_name="UPI_TRANSACTION_FAILURE",
            category="UPI",
            is_dispute=True,
            suggested_priority="Normal",
            case_type="Complaint",
        )
    if q in ("daily transaction limit", "upi transaction limit", "daily upi limit", "upi limits"):
        return IntentResult(
            intent_name="UPI_TRANSACTION_LIMIT",
            category="UPI",
            is_dispute=False,
            case_type="Inquiry",
        )
    if q in ("reset upi pin", "change upi pin", "forgot upi pin"):
        return IntentResult(
            intent_name="PIN_RESET_GUIDANCE",
            category="UPI",
            is_dispute=False,
            suggested_priority="Normal",
            case_type="Service Request",
        )

    # ATM chips:
    if q in ("cash not dispensed", "atm cash not dispensed", "atm not dispensing"):
        return IntentResult(
            intent_name="ATM_CASH_DISPENSE_FAILURE",
            category="ATM",
            is_dispute=True,
            suggested_priority="High",
            case_type="Complaint",
        )
    if q in ("atm withdrawal limits", "atm limits", "atm withdrawal limit"):
        return IntentResult(
            intent_name="ATM_WITHDRAWAL_LIMIT",
            category="ATM",
            is_dispute=False,
            case_type="Inquiry",
        )
    if q in ("card retained in atm", "card swallowed", "atm retained card", "card swallowed by atm"):
        return IntentResult(
            intent_name="ATM_CARD_SWALLOWED",
            category="ATM",
            is_dispute=True,
            suggested_priority="High",
            case_type="Complaint",
        )

    # Account chips:
    if q in ("check balance & statement", "check balance and statement", "account balance"):
        return IntentResult(
            intent_name="BALANCE_STATEMENT_INQUIRY",
            category="Account",
            is_dispute=False,
            case_type="Inquiry",
        )
    if q in ("fund transfer timings", "transfer timings", "neft rtgs imps"):
        return IntentResult(
            intent_name="TRANSFER_MODES_INQUIRY",
            category="Account",
            is_dispute=False,
            case_type="Inquiry",
        )
    if q in ("my profile details", "profile details", "my profile"):
        return IntentResult(
            intent_name="ACCOUNT_PROFILE_INQUIRY",
            category="Account",
            is_dispute=False,
            case_type="Inquiry",
        )

    # KYC chips:
    if q in ("periodic re-kyc steps", "periodic re-kyc", "re-kyc steps"):
        return IntentResult(
            intent_name="KYC_PROCESS_INQUIRY",
            category="KYC",
            is_dispute=False,
            case_type="Inquiry",
        )
    if q in ("dormant account activation", "dormant account", "inoperative account"):
        return IntentResult(
            intent_name="DORMANT_ACCOUNT_INQUIRY",
            category="Account",
            is_dispute=False,
            case_type="Inquiry",
        )
    if q in ("acceptable kyc documents", "acceptable documents", "valid kyc documents"):
        return IntentResult(
            intent_name="KYC_DOCUMENTS_INQUIRY",
            category="KYC",
            is_dispute=False,
            case_type="Inquiry",
        )

    # Direct selection of limit category options
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
    if re.search(r"\b(pin|password|mpin|tpin)\b", q) and re.search(r"\b(reset|forgot|change|chgnhe|chnage|cahnge|chg|new|create|generate|set)\b", q):
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

    # Intent: Card Blocking / Hotlisting (Lost, stolen, misplaced, block card)
    if (
        (re.search(r"\b(card|cards)\b", q) and re.search(r"\b(block|freeze|hotlist|deactivate|lost|stolen|misplaced)\b", q))
        or re.search(r"\b(block|hotlist)\s+(my\s+)?(card|debit|credit)\b", q)
    ) and not re.search(r"\b(unauthorized|fraud\w*|scam|stolen\s+money|lost\s+money)\b", q):
        return IntentResult(
            intent_name="CARD_BLOCK_GUIDANCE",
            category="Cards",
            is_dispute=False,
            suggested_priority="High",
            case_type="Service Request",
        )

    # Intent: Card Controls / Enable International / Contactless / Channel Limits
    if re.search(r"\b(card|cards)\b", q) and re.search(r"\b(enable|disable|international|contactless|nfc|replacement|reissue|online\s+usage|channel)\b", q):
        return IntentResult(
            intent_name="CARD_MANAGEMENT_INQUIRY",
            category="Cards",
            is_dispute=False,
            case_type="Inquiry",
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

    # Category-specific fallbacks if intent not recognized but domain keyword is present
    if re.search(r"\b(upi|gpay|phonepe|paytm|bhim|vpa)\b", q):
        return IntentResult(
            intent_name="UPI_GENERAL_INQUIRY",
            category="UPI",
            is_dispute=False,
        )
    if re.search(r"\b(atm|cash machine|cdm)\b", q):
        return IntentResult(
            intent_name="ATM_GENERAL_INQUIRY",
            category="ATM",
            is_dispute=False,
        )
    if re.search(r"\b(card|credit card|debit card|cvv|swipe|pos)\b", q):
        return IntentResult(
            intent_name="CARD_GENERAL_INQUIRY",
            category="Cards",
            is_dispute=False,
        )
    if re.search(r"\b(kyc|re-kyc|aadhaar|pan)\b", q):
        return IntentResult(
            intent_name="KYC_GENERAL_INQUIRY",
            category="KYC",
            is_dispute=False,
        )

    # Fallback to General Inquiry
    return IntentResult(
        intent_name="GENERAL_INQUIRY",
        category="General",
        is_dispute=False,
    )


def is_unresolved_solution_followup(query: str) -> bool:
    """
    Detects if the customer's query indicates that a previously provided self-service
    solution or knowledge guidance did not resolve their issue.
    """
    q = query.strip().lower()
    solution_not_working_regex = (
        r"\b(this\s+solution\s+(is\s+)?not\s+working|solution\s+not\s+working|solution\s+didn'?t\s+work|"
        r"this\s+is\s+not\s+working|it('?s|\s+is)?\s+not\s+working|not\s+working|"
        r"it\s+didn'?t\s+work|did\s*not\s+work|didn'?t\s+work|didn'?t\s+help|did\s*not\s+help|"
        r"still\s+(not\s+working|facing|having|failing|broken|unable|cannot|doesn'?t\s+work)|"
        r"tried\s+(this|it)\s*(but\s+)?(failed|didn'?t\s+work|not\s+working)|"
        r"not\s+resolved|issue\s+not\s+solved|problem\s+not\s+solved|not\s+fixed|"
        r"doesn'?t\s+work|does\s+not\s+work)\b"
    )
    return bool(re.search(solution_not_working_regex, q))


def is_clarification_or_didnt_get_followup(query: str) -> bool:
    """
    Detects if the customer is expressing that they didn't understand,
    didn't get the solution, didn't receive the item/card/otp, or need simpler assistance.
    """
    q = query.strip().lower()
    return bool(
        re.search(r"\b(i\s+)?(didn'?t|did\s+not|don'?t|do\s+not)\s+get(\s+it)?\b", q)
        or re.search(r"\b(didn'?t|did\s+not|don'?t|do\s+not)\s+understand(\s+it)?\b", q)
        or re.search(r"\b(not\s+clear|confused|what\s+do\s+you\s+mean|what\s+does\s+that\s+mean|explain\s+(simply|more)|i\s+am\s+confused)\b", q)
        or re.search(r"\b(how\s+to\s+do\s+(this|it)|can\s+you\s+help\s+me\s+do\s+(this|it))\b", q)
        or re.search(r"\b(haven'?t\s+received|have\s+not\s+received|didn'?t\s+receive|did\s+not\s+receive|not\s+received)\b", q)
    )


def is_direct_escalation_request(query: str) -> bool:
    """
    Detects if the user is explicitly requesting to escalate to support,
    talk to a human agent, connect to support desk, or open a ticket.
    Tolerates common typos like 'esclicate', 'esclate', 'escalte'.
    """
    q = query.strip().lower()
    return bool(
        # Typo-tolerant escalation
        re.search(r"\b(esclicate|escalate|esclate|escalte|escalating|escalation|esculate)\b", q)
        # Direct support connect
        or re.search(r"\b(connect|talk|transfer|speak|reach|forward|handover)\s+(me\s+)?(to\s+)?(human|agent|support|executive|specialist|representative|person|team)\b", q)
        or re.search(r"\b(support\s+(please|now|desk|agent|executive)|need\s+(human|support|agent)|call\s+support)\b", q)
        # Direct ticket creation request
        or re.search(r"\b(open|create|raise|file|register|lodge)\s+(a\s+)?(ticket|complaint|dispute|case)\b", q)
        # Affirmative answer after bot offered to connect to support
        or (re.search(r"^(yes|yes\s+please|please\s+do|please|sure|ok|open\s+it|connect\s+me)\b", q) and len(q.split()) <= 4)
    )


def classify_intent(query: str) -> IntentResult:
    """
    Classifies customer banking queries into structured intents, categories,
    and assigns the exact banking Case Type (Complaint, Inquiry, Service Request, Feedback).
    """
    res = _classify_intent_internal(query)
    res.case_type = detect_case_type(query, res.intent_name, res.is_dispute)
    return res
