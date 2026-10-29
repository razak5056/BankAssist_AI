"""
Comprehensive Banking Knowledge Dataset for BankAssist AI.
Covers 40 detailed scenarios across all 5 banking categories:
1. UPI & Digital Payments (8 scenarios)
2. ATM & Cash Withdrawal (8 scenarios)
3. Debit & Credit Cards (8 scenarios)
4. Account & Balance (8 scenarios)
5. Account Access & KYC (8 scenarios)

All guidelines are based on official Reserve Bank of India (RBI) mandates,
National Payments Corporation of India (NPCI) circulars, and banking ombudsman standards.
"""

BANKING_SCENARIOS = [
    # =========================================================================
    # CATEGORY 1: UPI & DIGITAL PAYMENTS (8 Scenarios)
    # =========================================================================
    {
        "id": "upi_failed_debited",
        "category": "UPI",
        "title": "UPI transaction failed but money debited from account",
        "is_dispute": True,
        "policy": "NPCI Circular & RBI TAT: Auto-reversal within T+1 business days. Penalty of ₹100/day after T+1 if delayed.",
        "content": (
            "When a UPI payment fails at a merchant or person-to-person transfer but money is debited from your bank account, "
            "the banking switch marks it as a failed or timed-out transaction. Under standard NPCI and RBI Turnaround Time (TAT) guidelines, "
            "an automatic reconciliation and reversal is initiated within T+1 business days (where T is the transaction date). "
            "If the beneficiary bank does not claim the funds, the money credits back to your source bank account. "
            "If the auto-reversal has not occurred after 24-48 hours, you should register a dispute ticket with the 12-digit "
            "Unique Transaction Reference (UTR) number printed in your SMS alert or passbook for inter-bank dispute resolution."
        ),
        "tags": ["upi failed", "money debited", "amount deducted", "failed payment", "utr", "auto reversal", "refund delayed", "npci tat"],
    },
    {
        "id": "upi_limits",
        "category": "UPI",
        "title": "Daily UPI transaction limits and transaction count caps",
        "is_dispute": False,
        "policy": "NPCI Master Direction: Standard cap of ₹1,00,000 and maximum 20 transactions per day per bank account.",
        "content": (
            "Under standard NPCI regulations, the general limit for UPI transactions is up to ₹1,00,000 (1 Lakh) per day, "
            "with a maximum of 20 financial transactions per day per bank account. Some special categories have enhanced limits: "
            "up to ₹5,00,000 for hospital and educational institution payments, and up to ₹2,00,000 for capital markets and insurance. "
            "Important Security Rule: When you link a new bank account or reset your UPI PIN on a new phone/SIM, "
            "banks impose a mandatory 24-hour cooling period during which the transaction limit is restricted to ₹5,000."
        ),
        "tags": ["upi limit", "daily limit", "how many transactions", "maximum upi", "per day limit", "cooling period", "upi cap"],
    },
    {
        "id": "upi_pin_reset",
        "category": "UPI",
        "title": "How to reset or change UPI PIN securely",
        "is_dispute": False,
        "policy": "NPCI Security Framework: PIN reset requires active debit card validation and 2FA OTP verification.",
        "content": (
            "To reset or change your UPI PIN securely: Open your UPI application (BHIM, Google Pay, PhonePe, Paytm, or Mobile Banking app). "
            "Navigate to your linked Bank Accounts section and select the account. Tap 'Forgot UPI PIN' or 'Reset PIN'. "
            "Enter the last 6 digits of your active physical Debit Card linked to that bank account, along with the card valid-thru (expiry) date. "
            "Your bank will dispatch a one-time password (OTP) to your registered mobile number. Enter the OTP, "
            "then choose a new 4-digit or 6-digit confidential UPI PIN and re-enter to confirm. "
            "Security Warning: Bank staff never ask for your UPI PIN, OTP, or CVV. Never share your PIN with anyone."
        ),
        "tags": ["reset pin", "forgot upi pin", "change pin", "create new pin", "debit card details", "upi password"],
    },
    {
        "id": "upi_lite",
        "category": "UPI",
        "title": "UPI Lite on-device wallet features, limits, and usage",
        "is_dispute": False,
        "policy": "RBI Monetary Policy: Maximum ₹500 per transaction and ₹2,000 cumulative wallet balance.",
        "content": (
            "UPI Lite is an on-device digital wallet that enables lightning-fast, small-value payments without entering a UPI PIN. "
            "Key features and limits: The maximum transaction limit is ₹500 per payment. The maximum cumulative wallet balance "
            "allowed at any time is ₹2,000. UPI Lite transactions do not clutter your official bank account passbook or statement; "
            "only the wallet top-up transactions appear on your bank statement. UPI Lite operates seamlessly even during peak banking server loads."
        ),
        "tags": ["upi lite", "wallet limit", "pinless payment", "small payments", "load wallet", "lite balance"],
    },
    {
        "id": "upi_wrong_transfer",
        "category": "UPI",
        "title": "Money transferred to wrong UPI ID or wrong mobile number",
        "is_dispute": True,
        "policy": "RBI Ombudsman Circular: Customer must report immediately; remitter bank contacts beneficiary bank to request consent-based refund.",
        "content": (
            "If you accidentally transfer money to an incorrect UPI ID or mobile number: "
            "1. Note the 12-digit UTR number, timestamp, and amount debited immediately. "
            "2. Under RBI directives, contact your bank's customer support and raise a 'Wrong Transfer' dispute ticket. "
            "3. Your remitter bank will initiate an inter-bank request with the beneficiary bank. Under banking privacy regulations, "
            "the beneficiary bank contacts the unintended recipient to obtain written consent for fund reversal. "
            "4. If the beneficiary refuses to reverse the money, you may lodge a formal complaint on the RBI Banking Ombudsman portal (cms.rbi.org.in)."
        ),
        "tags": ["wrong transfer", "sent to wrong person", "incorrect upi id", "mistaken transfer", "retrieve wrong payment"],
    },
    {
        "id": "upi_autopay",
        "category": "UPI",
        "title": "UPI AutoPay and recurring e-mandate management",
        "is_dispute": False,
        "policy": "RBI e-Mandate Framework: Pre-debit notification 24 hours prior; customer has right to revoke or pause mandate anytime.",
        "content": (
            "UPI AutoPay allows automated recurring payments for subscriptions, utility bills, EMIs, and mutual fund SIPs. "
            "Per RBI e-mandate guidelines, banks must dispatch a pre-debit SMS/notification at least 24 hours before the deduction occurs. "
            "Transactions up to ₹15,000 (enhanced to ₹1,00,000 for mutual funds, insurance, and education) execute without requiring a PIN. "
            "You can view, pause, modify, or permanently revoke active auto-debit mandates anytime directly from your UPI app's 'AutoPay' or 'Mandates' menu."
        ),
        "tags": ["autopay", "recurring payment", "cancel mandate", "e-mandate", "stop auto debit", "subscription debit"],
    },
    {
        "id": "upi_merchant_pending",
        "category": "UPI",
        "title": "Merchant payment pending or store QR payment delayed",
        "is_dispute": True,
        "policy": "NPCI Merchant Guidelines: Settlement confirmation within T+1; auto-reversal if merchant terminal rejects transaction.",
        "content": (
            "When paying at a retail shop or online merchant via QR code, if your account is debited but the merchant's machine "
            "shows 'Payment Pending' or 'Failed': Do not make an immediate duplicate payment until you verify status. "
            "Check the payment status in your app history. If the payment switch marks it as 'Failed', the funds will automatically "
            "reverse to your bank account within T+1 business days. If marked 'Successful' in your app, share the 12-digit UTR number "
            "with the merchant's payment gateway support to confirm receipt."
        ),
        "tags": ["merchant payment pending", "qr code pending", "store payment failed", "merchant not received money"],
    },
    {
        "id": "upi_international",
        "category": "UPI",
        "title": "UPI Global and International Payments",
        "is_dispute": False,
        "policy": "NIPL Framework: International UPI enabled for select countries using foreign QR codes.",
        "content": (
            "UPI Global allows Indian bank account holders traveling abroad to make cashless payments at international merchant QR codes. "
            "Supported countries currently include UAE, Singapore, France, Mauritius, Bhutan, Nepal, and Sri Lanka. "
            "To use it: In your UPI app, navigate to 'UPI International' or 'International Payments' and activate it for your bank account "
            "(valid up to 90 days). When scanning an overseas QR code, the transaction amount is displayed in foreign currency along with "
            "the estimated Indian Rupee (INR) conversion and applicable bank forex markup."
        ),
        "tags": ["upi international", "upi abroad", "travel payment", "foreign qr code", "international upi"],
    },

    # =========================================================================
    # CATEGORY 2: ATM & CASH WITHDRAWAL (8 Scenarios)
    # =========================================================================
    {
        "id": "atm_cash_not_dispensed",
        "category": "ATM",
        "title": "ATM cash not dispensed or partial cash dispensed but account debited",
        "is_dispute": True,
        "policy": "RBI DPSS Mandate: Resolution within T+5 calendar days. Mandatory compensation of ₹100 per day of delay payable to customer.",
        "content": (
            "If an ATM does not dispense cash (or dispenses only partial cash) but your bank account is debited: "
            "1. Retain the printed transaction slip if available, or save the SMS alert containing ATM ID and transaction reference. "
            "2. Under RBI circular DPSS.PD.No.2632/22.10.002/2010-11, banks are strictly mandated to re-credit the customer's account "
            "within T+5 business days (where T is the transaction date). "
            "3. If the bank fails to resolve the dispute and credit the funds within T+5 days, the bank is legally required to pay "
            "compensation of ₹100 per day of delay directly into the customer's account, provided the customer lodged the complaint within 30 days."
        ),
        "tags": ["cash not dispensed", "atm cash stuck", "partial cash", "atm debited no cash", "rbi compensation 100", "t+5 days"],
    },
    {
        "id": "atm_limits",
        "category": "ATM",
        "title": "Daily ATM cash withdrawal limits and financial withdrawal caps",
        "is_dispute": False,
        "policy": "Bank Card Guidelines: Daily limit ranges from ₹20,000 to ₹1,00,000 based on card variant (Classic/Platinum/Signature).",
        "content": (
            "Daily ATM cash withdrawal limits depend on your debit card variant: "
            "• Classic / Basic Debit Cards: ₹20,000 to ₹25,000 per day. "
            "• Platinum / Titanium Cards: ₹40,000 to ₹50,000 per day. "
            "• Signature / World / Infinite Cards: Up to ₹1,00,000 per day. "
            "Most ATMs also have a per-transaction dispensing limit of ₹10,000 (or ₹20,000 for own-bank customers) per withdrawal due to cash slot capacity. "
            "You can customize your domestic ATM daily limit downwards in your mobile banking app for fraud protection."
        ),
        "tags": ["atm limit", "daily cash withdrawal", "atm max cash", "how much cash can i withdraw", "platinum atm limit"],
    },
    {
        "id": "atm_card_swallowed",
        "category": "ATM",
        "title": "Debit card swallowed or retained by ATM machine",
        "is_dispute": True,
        "policy": "Card Security Policy: Retained cards are destroyed securely by custodian banks. A free replacement card is dispatched in 3-5 days.",
        "content": (
            "If an ATM machine captures, swallows, or retains your debit card: "
            "1. This can occur due to prolonged session inactivity, 3 wrong PIN attempts, card hardware sensor failure, or power disruption. "
            "2. For security and fraud prevention, banking guidelines forbid ATM custodians from returning captured cards directly to individuals. "
            "The captured card is shredded and destroyed securely. "
            "3. Open your mobile banking app or call our helpline to block the card immediately. "
            "A brand-new replacement debit card will be dispatched to your registered communication address within 3 to 5 business days."
        ),
        "tags": ["card swallowed", "atm retained card", "card stuck in atm", "card captured", "replacement debit card"],
    },
    {
        "id": "atm_interbank_charges",
        "category": "ATM",
        "title": "Inter-bank ATM free withdrawal rules and interchange charges",
        "is_dispute": False,
        "policy": "RBI Interchange Circular: 3 free transactions in 6 metro cities, 5 free transactions in non-metro centers per month. ₹21+GST thereafter.",
        "content": (
            "Under RBI regulations for other bank ATM usage: "
            "• Own Bank ATMs: Usually 5 free transactions per month (unlimited on select premium accounts). "
            "• Other Bank ATMs in 6 Metro Cities (Mumbai, New Delhi, Chennai, Kolkata, Bengaluru, Hyderabad): 3 free financial/non-financial transactions per calendar month. "
            "• Other Bank ATMs in Non-Metro Locations: 5 free transactions per calendar month. "
            "Charges after free limit: A maximum interchange fee of ₹21 + applicable GST per financial withdrawal and ₹11 + GST per non-financial inquiry (balance check / mini-statement)."
        ),
        "tags": ["atm charges", "free atm transactions", "metro atm rules", "interbank atm fee", "21 rupees charge"],
    },
    {
        "id": "atm_pin_blocked",
        "category": "ATM",
        "title": "ATM PIN blocked due to consecutive incorrect attempts",
        "is_dispute": False,
        "policy": "Banking Security Directive: 3 consecutive wrong PIN attempts trigger automatic 24-hour security lockout.",
        "content": (
            "If you enter the wrong ATM PIN 3 consecutive times, your debit card is temporarily blocked for security to prevent brute-force attacks: "
            "• Automatic Unlock: In most banks, the temporary block lifts automatically after exactly 24 hours from the last failed attempt. "
            "• Instant Self-Service Reset: If you need immediate access or forgot your PIN, do not wait 24 hours. Log in to Net Banking or Mobile Banking, "
            "navigate to 'Cards > Debit Cards > Generate Green PIN / Reset PIN', and set a new 4-digit PIN instantly using OTP verification."
        ),
        "tags": ["pin blocked", "wrong pin 3 times", "unblock pin", "unlock atm card", "forgot atm pin"],
    },
    {
        "id": "atm_cardless_cash",
        "category": "ATM",
        "title": "Cardless cash withdrawal at bank ATMs using mobile app",
        "is_dispute": False,
        "policy": "RBI Digital Banking Framework: Instant cash withdrawal without physical plastic card via dynamic OTP or QR code.",
        "content": (
            "Cardless cash withdrawal allows you to withdraw cash at your bank's ATMs without carrying your physical plastic card: "
            "1. Open your Mobile Banking application and select 'Cardless Cash Withdrawal' or 'UPI-ATM Cash'. "
            "2. Select the source bank account and enter the withdrawal amount (typically up to ₹10,000 to ₹20,000 per transaction). "
            "3. You will receive an instant 6-digit transaction reference code / OTP valid for 15 to 30 minutes. "
            "4. At the ATM, select 'Cardless Withdrawal' or 'UPI QR Cash', scan the QR or enter the OTP and your mobile number to dispense cash."
        ),
        "tags": ["cardless cash", "withdraw without card", "qr cash", "mobile atm cash", "cardless limit"],
    },
    {
        "id": "atm_cdm_deposit_stuck",
        "category": "ATM",
        "title": "Cash Deposit Machine (CDM / BNA) cash stuck but not credited",
        "is_dispute": True,
        "policy": "Cash Management Guidelines: Physical cash bin reconciliation within 3 to 5 business days.",
        "content": (
            "If you deposit currency notes into a Cash Deposit Machine (CDM) or Bunch Note Acceptor (BNA), and the machine experiences a jam, "
            "power cut, or reboots without printing a success receipt or crediting your account: "
            "1. Take a picture of the screen showing the CDM machine code, date, and timestamp. "
            "2. Report the incident to branch personnel if on-site, or raise a dispute ticket via customer support. "
            "3. The branch or third-party cash logistics team audits the CDM's reject and deposit cash cassettes during the next reconciliation cycle (typically 3 to 5 business days). "
            "4. The surplus cash count is matched against the electronic transaction logs and credited back to your account."
        ),
        "tags": ["cdm stuck", "cash deposit machine issue", "deposit cash not credited", "bna cash trapped", "cash machine error"],
    },
    {
        "id": "atm_foreign_card",
        "category": "ATM",
        "title": "International card usage and foreign ATM cash withdrawals",
        "is_dispute": False,
        "policy": "FEMA & RBI Regulations: Subject to Liberalised Remittance Scheme (LRS) and international access limits.",
        "content": (
            "To use your Indian debit card at overseas ATMs or use foreign cards at Indian ATMs: "
            "1. Enable 'International Transactions' and 'International ATM Cash' in your mobile banking app under Card Controls before travel. "
            "2. Withdrawal Fees: Standard international ATM withdrawal incurs an international transaction fee (typically ₹150 to ₹300 per withdrawal) "
            "plus a foreign currency conversion markup of 2% to 3.5% + GST. "
            "3. Dynamic Currency Conversion (DCC) Tip: Always choose to be billed in the local foreign currency (e.g., USD, EUR, AED) "
            "rather than INR at overseas ATMs to avoid inflated DCC exchange margins."
        ),
        "tags": ["international atm", "foreign withdrawal", "travel atm", "forex fee", "overseas atm withdrawal"],
    },

    # =========================================================================
    # CATEGORY 3: DEBIT & CREDIT CARDS (8 Scenarios)
    # =========================================================================
    {
        "id": "card_lost_stolen_block",
        "category": "Cards",
        "title": "Lost, stolen, or misplaced debit or credit card instant blocking",
        "is_dispute": True,
        "policy": "RBI Zero Liability Policy: Immediate blocking prevents unauthorized financial liability.",
        "content": (
            "If your debit or credit card is lost, stolen, or misplaced, take action immediately to protect your funds: "
            "1. Instant App Block: Open your Mobile Banking or Net Banking app, go to 'Cards', and toggle 'Block Card' to Permanent Block. "
            "2. SMS Blocking: Send a block SMS from your registered mobile number (e.g., 'BLOCK <last 4 digits>' to your bank's designated shortcode). "
            "3. 24x7 Emergency Hotline: Call our round-the-clock fraud helpline for immediate agent-assisted blocking. "
            "Once blocked, all online, offline POS, contactless, and ATM transactions are permanently denied. "
            "A replacement card with a new card number and CVV will be dispatched within 3 to 5 business days."
        ),
        "tags": ["lost card", "stolen card", "block card immediately", "hotlist card", "deactivate card", "misplaced card"],
    },
    {
        "id": "card_unauthorized_fraud",
        "category": "Cards",
        "title": "Reporting unauthorized card transactions and RBI zero-liability protection",
        "is_dispute": True,
        "policy": "RBI Circular DBR.No.Leg.BC.78/09.07.005/2017-18: Zero liability if customer reports fraud within 3 calendar days.",
        "content": (
            "Under RBI's customer protection framework for unauthorized electronic banking transactions: "
            "• Zero Customer Liability: If you report an unauthorized transaction within 3 calendar days of receiving the bank's SMS alert, "
            "you have ZERO financial liability for fraudulent losses (where fraud is not due to customer negligence like sharing OTP/PIN). "
            "• Limited Liability: If reported within 4 to 7 calendar days, customer liability is capped (maximum ₹10,000 for savings accounts and ₹25,000 for credit cards). "
            "• Action: 1. Block the card immediately. 2. Register a dispute ticket with transaction details and file a cybercrime report at cybercrime.gov.in."
        ),
        "tags": ["unauthorized transaction", "card fraud", "scam transaction", "rbi zero liability", "fraud dispute", "stolen money card"],
    },
    {
        "id": "card_online_usage",
        "category": "Cards",
        "title": "Enabling, disabling, and configuring online, POS, and contactless card limits",
        "is_dispute": False,
        "policy": "RBI Card Security Direction: Banks must provide 24x7 customer controls to switch on/off transaction channels and set custom spending limits.",
        "content": (
            "Per RBI card security mandates, all new debit and credit cards are issued with international and online transactions disabled by default. "
            "You have complete 24x7 control over your card channels via Net Banking or Mobile Banking: "
            "• Domestic E-Commerce (Online Spends): Toggle On/Off and set maximum daily spending limits. "
            "• Contactless (Tap & Pay / NFC): Toggle On/Off for transactions up to ₹5,000 without entering a PIN. "
            "• Point of Sale (POS) and ATM Cash: Adjust daily transaction caps individually. "
            "• International Usage: Keep turned Off when not traveling to eliminate overseas card fraud."
        ),
        "tags": ["card controls", "enable online transactions", "disable international", "contactless limit", "tap and pay", "pos limits"],
    },
    {
        "id": "card_pin_generation",
        "category": "Cards",
        "title": "Debit and credit card PIN generation and Green PIN setup",
        "is_dispute": False,
        "policy": "Paperless Green PIN Initiative: Instant self-service PIN creation via Net Banking, Mobile App, or Bank ATM.",
        "content": (
            "You can generate or change your 4-digit debit/credit card PIN paperlessly without waiting for a physical PIN mailer: "
            "• Method 1 (Mobile Banking): Go to Cards > Manage Card > Set/Change PIN. Enter your desired 4-digit PIN and confirm with OTP. "
            "• Method 2 (Net Banking): Log in > Cards > Debit Cards > Instant PIN Generation > select account and card > verify via OTP. "
            "• Method 3 (ATM): Insert your card > select 'Generate Green PIN / Set PIN' > enter OTP received on your mobile > enter new PIN. "
            "Do not choose predictable PINs like your year of birth, 1111, or 1234."
        ),
        "tags": ["generate pin", "green pin", "set card pin", "new card pin", "create debit card pin"],
    },
    {
        "id": "card_expiry_renewal",
        "category": "Cards",
        "title": "Debit and credit card expiry and automated renewal process",
        "is_dispute": False,
        "policy": "Card Issuance Rules: Automatic re-issuance 30 to 45 days prior to expiration for active accounts.",
        "content": (
            "Your debit or credit card is valid through the last day of the month printed on the card face (e.g., 'Valid Thru: 08/26' means valid until August 31, 2026). "
            "Automated Renewal: If your bank account is active and KYC is compliant, your bank automatically manufactures and dispatches "
            "a replacement card 30 to 45 days before the expiry date to your registered address via speed post. "
            "Action Required: Verify that your registered communication address is up to date in your profile. "
            "Once you receive the renewed card, activate it by generating a Green PIN in mobile banking."
        ),
        "tags": ["card expired", "renew card", "valid thru", "card expiry date", "replacement card dispatch"],
    },
    {
        "id": "card_billing_dispute",
        "category": "Cards",
        "title": "Credit card billing disputes, double charges, and chargeback process",
        "is_dispute": True,
        "policy": "Mastercard/Visa Chargeback Rules: Customer must dispute within 30 to 60 days of statement generation with transaction invoice.",
        "content": (
            "If your credit card statement shows an incorrect amount, double charge for a single purchase, or billing for cancelled services: "
            "1. Contact the merchant first to seek an amicable cancellation or refund receipt. "
            "2. If the merchant fails to refund within 7 business days, lodge a formal 'Credit Card Chargeback / Dispute' with your bank. "
            "3. Submit supporting documentation (order cancellation confirmation, invoice, communication log with merchant). "
            "4. Your bank will raise a chargeback through the card payment network (Visa, Mastercard, RuPay). "
            "The disputed amount is placed under temporary suspension/credit while inter-bank arbitration proceeds."
        ),
        "tags": ["credit card dispute", "double charge", "billing error", "chargeback", "merchant dispute credit card"],
    },
    {
        "id": "card_reward_points",
        "category": "Cards",
        "title": "Credit and debit card reward points earning, validity, and redemption",
        "is_dispute": False,
        "policy": "Loyalty Program Terms: Points valid for 24-36 months; redeemable via rewards portal.",
        "content": (
            "Earn and redeem reward points on your card purchases: "
            "• Accrual: Earn reward points on eligible retail, dining, travel, and online spends (fuel, wallet top-ups, and rent payments are typically excluded). "
            "• Validity: Reward points are generally valid for 24 to 36 months from the date of credit; unredeemed points expire automatically. "
            "• How to Redeem: Log in to your Net Banking portal > Cards > Rewards Catalog. "
            "Redeem points for shopping vouchers (Amazon, Flipkart), flight tickets, hotel bookings, merchandise, or statement cash credit."
        ),
        "tags": ["reward points", "redeem points", "credit card rewards", "points validity", "convert points to cash"],
    },
    {
        "id": "card_forex_markup",
        "category": "Cards",
        "title": "Foreign currency markup fees and cross-border transaction charges",
        "is_dispute": False,
        "policy": "FEMA Guidelines: Standard foreign exchange markup applies on all international retail and online payments.",
        "content": (
            "When using an Indian credit or debit card for international transactions (overseas travel or shopping on foreign websites like Netflix, Amazon US): "
            "• Foreign Currency Markup: Banks levy a forex markup fee of 1.5% to 3.5% on the gross converted transaction value. "
            "• Goods & Services Tax: 18% GST is levied on the forex markup fee component per Government of India tax rules. "
            "• Cross-Border Surcharge: If you pay in Indian Rupees (INR) on a website hosted outside India, a cross-border assessment fee of 1% + GST may apply."
        ),
        "tags": ["forex markup", "international card charges", "currency conversion fee", "overseas card payment fee"],
    },

    # =========================================================================
    # CATEGORY 4: ACCOUNT & BALANCE (8 Scenarios)
    # =========================================================================
    {
        "id": "account_balance_statement",
        "category": "Account",
        "title": "Checking account balance, mini-statement, and downloading bank statements",
        "is_dispute": False,
        "policy": "Digital Banking Standards: Real-time balance and digitally signed PDF statements provided 24x7.",
        "content": (
            "You can check your real-time available balance and view your recent transactions anytime through multiple channels: "
            "1. Customer Overview: View available balance, clear balance, and uncleared holds on your dashboard Overview tab. "
            "2. Missed-Call & SMS Banking: Give a missed call to your bank's toll-free balance inquiry number from your registered mobile. "
            "3. Official e-Statements: Download detailed PDF statements for 3, 6, 12 months, or custom date ranges from Net Banking > Accounts > e-Statement. "
            "Password Protection: Downloaded statements are encrypted. The standard password is your Date of Birth in DDMMYYYY format "
            "followed by the last 4 digits of your account or customer ID."
        ),
        "tags": ["check balance", "account balance", "download statement", "mini statement", "passbook", "e-statement password"],
    },
    {
        "id": "account_transfer_modes",
        "category": "Account",
        "title": "NEFT, RTGS, and IMPS fund transfer timings, limits, and settlement rules",
        "is_dispute": False,
        "policy": "RBI Payment Systems: NEFT and RTGS operate 24x7x365. Zero NEFT charges for savings accounts online.",
        "content": (
            "Comparison of domestic electronic fund transfer channels in India: "
            "• IMPS (Immediate Payment Service): Instant real-time settlement 24x7x365 up to ₹5,00,000 per transaction using Account+IFSC or Mobile+MMID. "
            "• NEFT (National Electronic Funds Transfer): Operates 24x7 in half-hourly batches with no minimum or maximum limit for online transfers. "
            "RBI mandates zero processing charges for online NEFT initiated by savings account holders. "
            "• RTGS (Real Time Gross Settlement): Real-time gross settlement for high-value fund transfers of ₹2,00,000 and above. Operates 24x7x365."
        ),
        "tags": ["neft timings", "rtgs limit", "imps limit", "fund transfer modes", "neft charges", "how to transfer money"],
    },
    {
        "id": "account_freeze_lien",
        "category": "Account",
        "title": "Account frozen, debit freeze, or lien marked on bank account",
        "is_dispute": True,
        "policy": "Statutory Compliance: Account restrictions imposed under court orders, Cyber Cell notices, Tax authorities, or KYC non-compliance.",
        "content": (
            "If your bank account displays a status of 'Debit Freeze', 'Account Frozen', or has a 'Lien Amount' marked: "
            "1. Debit Freeze: Credits are allowed but withdrawals and transfers are restricted. Common causes include expired KYC, "
            "statutory court attachment orders, Income Tax demand, or law enforcement / Cyber Crime notices regarding disputed transactions. "
            "2. Lien Amount: A specific fund amount is held and cannot be withdrawn (e.g., security for credit card, uncollected cheque, or loan guarantee). "
            "Resolution: Contact your home branch manager or customer support to obtain the official notice reference and issuing authority details. "
            "If frozen due to KYC, submit fresh KYC documents; if due to a cyber cell notice, an official clearance/NOC letter is required."
        ),
        "tags": ["account frozen", "debit freeze", "lien marked", "account blocked", "cyber cell hold", "cannot withdraw money"],
    },
    {
        "id": "account_min_balance",
        "category": "Account",
        "title": "Minimum Average Balance (MAB / AMB) requirements and non-maintenance charges",
        "is_dispute": False,
        "policy": "RBI Fair Practices Code: Penalties must be proportionate to the shortfall; accounts cannot turn negative due to penalties.",
        "content": (
            "Minimum Average Balance (MAB) / Average Monthly Balance (AMB) rules for savings accounts: "
            "• Requirements: Urban/Metro branches typically require ₹5,000 to ₹10,000; Semi-urban ₹2,000 to ₹5,000; Rural ₹500 to ₹1,000. "
            "• Zero Balance Accounts: Basic Savings Bank Deposit Accounts (BSBDA), Pradhan Mantri Jan Dhan Yojana (PMJDY), and Corporate Salary accounts have no MAB requirement. "
            "• RBI Directive: If balance falls below MAB, the bank must notify the customer via SMS/email giving 30 days to replenish the shortfall. "
            "Importantly, banks are prohibited by RBI from turning an account into a negative balance solely due to penalty charges."
        ),
        "tags": ["minimum balance", "mab charges", "amb penalty", "average balance shortfall", "zero balance account", "below minimum", "balance penalty", "minimum limit"],
    },
    {
        "id": "account_cheque_clearing",
        "category": "Account",
        "title": "Cheque clearing turnaround times (CTS) and cheque bounce legal guidelines",
        "is_dispute": False,
        "policy": "Cheque Truncation System (CTS): 24-hour clearing cycle. Cheque bounce for insufficient funds attracts Section 138 NI Act penalties.",
        "content": (
            "Cheque clearing standards under the Cheque Truncation System (CTS): "
            "• Clearing Timeline: Local and outstation CTS-compliant cheques are processed in automated clearing cycles, typically crediting within T+1 to T+2 business days. "
            "• Positive Pay System (PPS): For cheques of ₹50,000 and above, customers should submit PPS verification details "
            "(cheque number, date, payee name, amount) in their app prior to issuance to prevent fraud. "
            "• Cheque Bounce: Returning a cheque due to insufficient funds attracts bank bounce charges (₹250 - ₹500 + GST) and carries legal liabilities under Section 138 of the Negotiable Instruments Act."
        ),
        "tags": ["cheque clearing time", "cheque bounce", "positive pay system", "cts clearing", "cheque deposit"],
    },
    {
        "id": "account_interest_cert",
        "category": "Account",
        "title": "Downloading Interest Certificate and TDS Certificate Form 16A",
        "is_dispute": False,
        "policy": "Income Tax Compliance: Annual interest certificates provided for savings and fixed deposits for tax filing.",
        "content": (
            "For tax return filing, you can obtain official financial certificates directly from Net Banking without visiting a branch: "
            "• Interest Certificate: Summarizes total interest earned during the financial year on Savings Bank accounts and Term Deposits. "
            "• Form 16A (TDS Certificate): Issued quarterly if Tax Deducted at Source (TDS) was deducted on your Fixed Deposit interest (applicable if interest exceeds ₹40,000 for regular citizens or ₹50,000 for senior citizens). "
            "• Form 15G / 15H: Submit Form 15G (below 60 years) or Form 15H (senior citizens) at the beginning of each financial year to request non-deduction of TDS if total taxable income is below basic exemption."
        ),
        "tags": ["interest certificate", "form 16a", "tds certificate", "form 15g", "form 15h", "income tax certificate"],
    },
    {
        "id": "account_fd_rd_opening",
        "category": "Account",
        "title": "Fixed Deposit (FD) and Recurring Deposit (RD) creation and premature closure rules",
        "is_dispute": False,
        "policy": "RBI Master Direction on Deposits: Senior citizens receive 0.50% additional interest; premature withdrawal penalty is 0.5% - 1%.",
        "content": (
            "Managing Term Deposits (Fixed Deposits & Recurring Deposits): "
            "• Instant Opening: Create an FD or RD instantly via Net Banking or Mobile Banking with flexible tenures from 7 days to 10 years. "
            "• Senior Citizen Benefit: Senior citizens (aged 60 and above) receive an additional interest rate of 0.50% p.a. on all domestic deposit tenures. "
            "• Premature Closure: You can prematurely liquidate an FD online 24x7. A standard penal interest rate of 0.5% to 1.0% is deducted from the applicable interest rate for the period the deposit remained with the bank. "
            "• Loan against FD: You can avail an instant digital overdraft or loan against FD up to 90%-95% of deposit value at 1%-2% above the FD rate."
        ),
        "tags": ["fixed deposit", "fd interest rates", "recurring deposit", "premature fd closure", "loan against fd", "senior citizen fd"],
    },
    {
        "id": "account_dormant_reactivation",
        "category": "Account",
        "title": "Dormant or inoperative account reactivation and unclaimed deposits",
        "is_dispute": False,
        "policy": "RBI Inoperative Accounts Guidelines: Inoperative after 24 months of no customer transactions. Reactivation is free of charge.",
        "content": (
            "Under RBI Master Directions, a savings or current account is classified as 'Inoperative' or 'Dormant' if no customer-induced financial transaction occurs for over 2 years (24 months): "
            "• Impact: Standing instructions, interest credits, and dividend credits continue, but customer withdrawals are restricted. "
            "• No Charges Rule: Per RBI regulations, banks are strictly forbidden from levying any penalty charges for activating dormant accounts. "
            "• How to Reactivate: Visit your home branch with original Officially Valid KYC documents (Aadhaar/PAN/Passport) and a fresh passport photograph, "
            "submit an account reactivation form, and execute a customer-induced deposit or withdrawal transaction."
        ),
        "tags": ["dormant account", "inoperative account", "reactivate account", "account inactive", "unclaimed deposit"],
    },

    # =========================================================================
    # CATEGORY 5: ACCOUNT ACCESS & KYC (8 Scenarios)
    # =========================================================================
    {
        "id": "kyc_periodic_update",
        "category": "KYC",
        "title": "Periodic Re-KYC update guidelines and online self-declaration process",
        "is_dispute": False,
        "policy": "RBI Master Direction - Know Your Customer (KYC): Low risk every 10 years, medium risk every 8 years, high risk every 2 years.",
        "content": (
            "Reserve Bank of India mandates periodic updating of customer KYC records based on risk categorization: "
            "• Frequency: High Risk customers: every 2 years; Medium Risk customers: every 8 years; Low Risk customers: every 10 years. "
            "• Online Self-Declaration (No Change): If your address and details have not changed, you are NOT required to visit a branch. "
            "Submit a simple online self-declaration via Net Banking, Mobile Banking, or registered email. "
            "• Address Change: If your address has changed, complete Video KYC (V-CIP) or upload your updated Aadhaar for DigiLocker OTP verification."
        ),
        "tags": ["re-kyc", "periodic kyc", "update kyc", "kyc due", "online kyc self declaration", "v-cip"],
    },
    {
        "id": "kyc_valid_documents",
        "category": "KYC",
        "title": "Officially Valid Documents (OVD) for KYC verification",
        "is_dispute": False,
        "policy": "Prevention of Money Laundering Rules: 6 Officially Valid Documents recognized for proof of identity and address.",
        "content": (
            "Under PML Rules and RBI Master Directions, only the following 6 documents are recognized as Officially Valid Documents (OVDs): "
            "1. Passport "
            "2. Driving License "
            "3. Proof of possession of Aadhaar number (Aadhaar card/e-Aadhaar with masked first 8 digits) "
            "4. Voter's Identity Card issued by the Election Commission of India "
            "5. Job Card issued by NREGA duly signed by an officer of the State Government "
            "6. Letter issued by the National Population Register containing name and address details. "
            "PAN Card serves as mandatory proof of income/tax identification (or Form 60 if PAN is not allotted)."
        ),
        "tags": ["valid documents for kyc", "ovd list", "kyc document proof", "proof of address", "aadhaar kyc"],
    },
    {
        "id": "kyc_address_update",
        "category": "KYC",
        "title": "How to change or update registered communication address",
        "is_dispute": False,
        "policy": "RBI KYC Amendment: Address change permitted through Aadhaar-based OTP verification without physical branch visit.",
        "content": (
            "To update your communication address in bank records: "
            "• Digital Method (Instant): Log in to Net Banking or Mobile Banking > Profile > Update Address. "
            "Authenticate via Aadhaar DigiLocker integration. Once you enter the OTP sent to your Aadhaar-linked mobile number, "
            "the address is verified and updated in banking records within 24 hours. "
            "• Physical Branch Method: Submit a signed Address Updation Request form along with a self-attested copy of an Officially Valid Document (Passport, Driving License, Voter ID, or Utility Bill not older than 2 months)."
        ),
        "tags": ["change address", "update communication address", "address update online", "aadhaar address change"],
    },
    {
        "id": "kyc_mobile_email_update",
        "category": "KYC",
        "title": "Updating registered mobile number and email ID in bank records",
        "is_dispute": False,
        "policy": "Banking Security Standard: Mobile number updates require two-factor authentication or branch biometric verification to prevent SIM-swap fraud.",
        "content": (
            "Because your mobile number receives confidential transaction OTPs and security alerts, banks follow strict 2FA protocols to update it: "
            "• At Bank ATM: Insert your active Debit Card > select 'Registration / Services' > 'Update Mobile Number' > enter new number > verify OTP sent to both old and new numbers. "
            "• Net Banking: If you have an active OTP device or debit card credentials, navigate to Profile > Contact Details > Edit Mobile Number. "
            "• Branch Submission: Visit any branch with your original photo ID (PAN/Aadhaar) to perform biometric or signature-verified mobile updation."
        ),
        "tags": ["update mobile number", "change phone number", "update email id", "change registered mobile", "otp number change"],
    },
    {
        "id": "kyc_netbanking_locked",
        "category": "KYC",
        "title": "Net Banking or Mobile Banking login locked and password reset",
        "is_dispute": False,
        "policy": "Cyber Security Framework: Account access locked after 3 to 5 failed login attempts to prevent brute force unauthorized access.",
        "content": (
            "If your internet banking or mobile banking access is locked: "
            "• Cause: Entering an incorrect password or OTP 3 consecutive times triggers a temporary security lock. "
            "• Instant Self-Unlock: On the login screen, click 'Forgot Password / Unlock User Access'. Enter your Customer ID and registered mobile number. "
            "Validate your identity using your active Debit Card (Card number, ATM PIN, expiry) and the OTP sent to your mobile. "
            "• Set a strong password with at least 8-16 characters including uppercase, lowercase, numbers, and special symbols. "
            "Do not use predictable words like your name or banking password."
        ),
        "tags": ["netbanking locked", "unlock user id", "forgot netbanking password", "reset mobile banking login", "user access disabled"],
    },
    {
        "id": "kyc_nominee_registration",
        "category": "KYC",
        "title": "Adding, modifying, or updating Nominee in bank account (Form DA-1)",
        "is_dispute": False,
        "policy": "Banking Regulation Act (Section 45ZA): Every individual depositor has the legal right to register a nominee.",
        "content": (
            "Nomination ensures that in the unfortunate event of the depositor's demise, funds are released to the nominee without legal disputes or succession certificates: "
            "• Statutory Forms: Form DA-1 (New Nomination), Form DA-2 (Cancellation of Nomination), Form DA-3 (Variation/Change of Nominee). "
            "• Online Registration: Log in to Net Banking or Mobile Banking > Service Requests > Accounts > Manage Nomination. "
            "Enter the nominee's full name, date of birth, relationship with depositor, and address. If the nominee is a minor, provide guardian details. "
            "• Confirmation: Once submitted, the nominee's name is registered and will appear on your passbook and statement."
        ),
        "tags": ["nominee registration", "add nominee", "form da-1", "change nominee", "update nomination", "nominee name"],
    },
    {
        "id": "kyc_joint_account_ops",
        "category": "KYC",
        "title": "Joint account operation mandates (Either or Survivor, Former or Survivor, Joint)",
        "is_dispute": False,
        "policy": "RBI Guidelines on Deposit Accounts: Clear survivor mandates ensure smooth operation and payment upon death of a holder.",
        "content": (
            "Operational mandates for joint bank accounts: "
            "• Either or Survivor (E or S): Any one of the account holders can operate the account, draw cheques, and execute transfers independently during their lifetimes. "
            "Upon the demise of one holder, the survivor possesses full authority over remaining funds. "
            "• Former or Survivor (F or S): Only the primary (former) account holder can operate the account during their lifetime. "
            "The survivor can operate only after the demise of the former upon presenting a death certificate. "
            "• Jointly Operated: All account holders must sign cheques and authorize transactions jointly."
        ),
        "tags": ["joint account", "either or survivor", "former or survivor", "joint account rules", "how joint account works"],
    },
    {
        "id": "kyc_deceased_claim",
        "category": "KYC",
        "title": "Deceased depositor claim settlement process without probate",
        "is_dispute": False,
        "policy": "RBI Master Circular on Deceased Claims: Settlement within 15 calendar days of receiving full documentation.",
        "content": (
            "Settlement of funds standing to the credit of a deceased depositor: "
            "• With Valid Nomination: The registered nominee submits a death certificate of the account holder, identity proof of the nominee, "
            "and Claim Form. Per RBI guidelines, banks must settle the claim within a maximum of 15 calendar days without asking for a succession certificate. "
            "• Without Nomination: If no nominee was registered, legal heirs must submit an indemnity bond, death certificate, "
            "and letter of disclaimer from all heirs (for amounts up to the bank's simplified threshold of ₹1,00,000 to ₹5,00,000) or a legal heir certificate."
        ),
        "tags": ["deceased claim", "death claim settlement", "deceased depositor funds", "claim without nominee", "15 days claim settlement"],
    },
]
