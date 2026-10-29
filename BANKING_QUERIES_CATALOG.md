# BankAssist AI — Customer Query Catalog & Pre-Escalation Resolution Guide

This document catalogs **all types of customer queries that BankAssist AI resolves directly using the ChromaDB Vector Database and Groq LLM without opening or escalating a ticket to the L1 support team**.

It also outlines the **exact criteria that distinguish self-service informational queries from actionable dispute cases requiring L1 support escalation**.

---

## 1. Query Resolution Flow (HLD Pre-Escalation Engine)

```text
                                [ Customer Query ]
                                        │
                                        ▼
                          [ Intent & Category Detection ]
                                        │
         ┌──────────────────────────────┴──────────────────────────────┐
         ▼                                                             ▼
 [ Dispute / Loss / Fraud ]                                [ Informational / Guidance ]
 (Customer reports active problem)                        (Customer asks for limits, how-to, rules)
         │                                                             │
         ▼                                                             ▼
 [ TICKET CREATED = TRUE ]                                  [ TICKET CREATED = FALSE ]
 • Auto-generate Ticket #TK-XXXXX                           • ChromaDB Vector Semantic Search
 • Compute SLA Deadline (+24h/+48h)                         • Retrieve Verified RBI/NPCI Guidelines
 • Route to least-loaded L1 Executive                       • Generate grounded answer with Groq LLM
 • Log in ticket_history audit trail                        • Provide interactive suggestion chips
                                                            • 100% Self-Service Resolution
```

---

## 2. All Query Types Answered Directly (No Ticket / No L1 Escalation)

### A. Greetings & Platform Capabilities
*These queries are answered with friendly navigation and assistance options.*

| Sample Customer Queries | Intent Classification | Agent Action / Response | Ticket Created? |
| :--- | :--- | :--- | :---: |
| • `"hi"`<br>• `"hello"`<br>• `"hey there"`<br>• `"good morning"`<br>• `"who are you"`<br>• `"what can you do"` | `GREETING` | Greets customer by registered username; lists the 5 support categories (Cards, UPI, ATM, Account, KYC); prompts the customer to describe their banking need. | **NO** |

---

### B. Authenticated Customer Profile & Identity Inquiries
*These queries fetch real-time JWT session data and guide the customer to their dashboard overview.*

| Sample Customer Queries | Intent Classification | Agent Action / Response | Ticket Created? |
| :--- | :--- | :--- | :---: |
| • `"i need my account information"`<br>• `"show my profile"`<br>• `"what is my customer id"`<br>• `"my registered email"`<br>• `"who am i"`<br>• `"my account details"` | `ACCOUNT_PROFILE_INQUIRY` | Returns authenticated customer details: Full Name, Registered Email, Customer ID, Account Status (`Active`), and Security Session status. Directs customer to the Overview tab. | **NO** |

---

### C. Category Overviews (Dashboard Category Cards)
*When a customer selects a broad category without reporting a specific dispute, the agent provides an overview and interactive suggestion chips.*

| Sample Customer Queries | Intent Classification | Interactive Chips Offered | Ticket Created? |
| :--- | :--- | :--- | :---: |
| • `"I have a question about my account or balance"`<br>• `"help with account or balance"` | `ACCOUNT_CATEGORY_OVERVIEW` | `[Check Balance & Statement]`<br>`[Fund Transfer Timings]`<br>`[My Profile Details]` | **NO** |
| • `"I need help with a UPI or digital payment"`<br>• `"help with upi"` | `UPI_CATEGORY_OVERVIEW` | `[Failed UPI Transfer]`<br>`[Daily Transaction Limit]`<br>`[Reset UPI PIN]` | **NO** |
| • `"I need help with an ATM withdrawal"`<br>• `"help with atm"` | `ATM_CATEGORY_OVERVIEW` | `[Cash Not Dispensed]`<br>`[ATM Withdrawal Limits]`<br>`[Card Retained in ATM]` | **NO** |
| • `"I need help with my debit or credit card"`<br>• `"help with cards"` | `CARD_CATEGORY_OVERVIEW` | `[Block Card Immediately]`<br>`[Report Unauthorized Charge]`<br>`[Card Online Usage]` | **NO** |
| • `"I need help with account access or KYC verification"`<br>• `"help with kyc"` | `KYC_CATEGORY_OVERVIEW` | `[Periodic Re-KYC Steps]`<br>`[Dormant Account Activation]`<br>`[Acceptable Documents]` | **NO** |

---

### D. Category 1: UPI & Digital Payments (Self-Service Queries)
*Vector DB searches against NPCI Master Directions and UPI Procedural Guidelines.*

| # | Sample Customer Queries | ChromaDB Scenario | Grounded Resolution Provided by Agent | Ticket Created? |
| :-: | :--- | :--- | :--- | :---: |
| **1** | • `"how many transaction will i done per day"`<br>• `"what is the daily upi limit"`<br>• `"maximum amount i can send via upi"` | `upi_limits` | Explains NPCI cap: up to ₹1,00,000 and max 20 transactions per day per bank account. Details initial 24h ₹5,000 cooling limit for newly linked devices. Provides interactive clarification chips. | **NO** |
| **2** | • `"how to reset my upi pin"`<br>• `"forgot upi pin how to change"`<br>• `"how to set new upi pin securely"` | `upi_pin_reset` | Step-by-step guidance: Open UPI app > Select Bank Account > Forgot/Reset PIN > Enter last 6 digits of Debit Card + Expiry > Verify OTP > Enter new PIN. Safety warning against sharing PIN/OTP. | **NO** |
| **3** | • `"what is upi lite limit"`<br>• `"how much can i pay without pin in upi lite"`<br>• `"upi lite wallet balance limit"` | `upi_lite` | Explains ₹500 per transaction limit and ₹2,000 maximum cumulative wallet balance. Explains that individual small payments do not clutter bank statement. | **NO** |
| **4** | • `"how to cancel upi autopay"`<br>• `"stop recurring mandate on upi"`<br>• `"can bank deduct autopay without otp"` | `upi_autopay` | Explains RBI e-mandate rules: 24h advance SMS notification; how to pause/revoke active mandates in app up to ₹15,000 without PIN. | **NO** |
| **5** | • `"can i use upi in dubai or singapore"`<br>• `"how does upi international work"`<br>• `"upi global activation steps"` | `upi_international` | Details international UPI activation for UAE, Singapore, France, Mauritius, Nepal, Bhutan, Sri Lanka; explains currency conversion and forex markup. | **NO** |
| **6** | • `"merchant payment pending what to do"`<br>• `"store qr debited but merchant says pending"` | `upi_merchant_pending` | Advises not to make immediate duplicate payments; explains $T+1$ auto-reversal if terminal rejected, or sharing 12-digit UTR with merchant gateway. | **NO** |

---

### E. Category 2: ATM & Cash Withdrawal (Self-Service Queries)
*Vector DB searches against RBI DPSS ATM Directives and Interchange Circulars.*

| # | Sample Customer Queries | ChromaDB Scenario | Grounded Resolution Provided by Agent | Ticket Created? |
| :-: | :--- | :--- | :--- | :---: |
| **7** | • `"what is the daily atm withdrawal limit"`<br>• `"how much cash can i withdraw at atm per day"`<br>• `"platinum card atm cash limit"` | `atm_limits` | Explains daily withdrawal limits by card tier: Classic (₹20k–₹25k), Platinum (₹40k–₹50k), Signature/World (up to ₹1 Lakh); notes per-transaction machine limit of ₹10,000–₹20,000. | **NO** |
| **8** | • `"how many free atm withdrawals per month"`<br>• `"charges for using other bank atm"`<br>• `"interbank atm withdrawal charges"` | `atm_interbank_charges` | Details RBI rules: 3 free transactions in 6 metro cities, 5 free in non-metro centers per month. Maximum fee of ₹21 + GST for financial and ₹11 + GST for non-financial transactions thereafter. | **NO** |
| **9** | • `"my atm pin is blocked for 3 wrong attempts"`<br>• `"how to unblock atm card after wrong pin"`<br>• `"when will blocked atm pin reset"` | `atm_pin_blocked` | Explains 24-hour automatic security lockout; guides customer on instant reset via Net Banking / Mobile Banking 'Generate Green PIN' without waiting. | **NO** |
| **10** | • `"how to withdraw cash without debit card at atm"`<br>• `"cardless cash withdrawal process"`<br>• `"what is upi atm cash limit"` | `atm_cardless_cash` | Step-by-step instructions: Initiate in mobile app > Generate 6-digit transaction reference code/OTP (valid 15–30 min) > Select 'Cardless Cash' at ATM (limit ₹10,000–₹20,000). | **NO** |
| **11** | • `"can i use my debit card at international atm"`<br>• `"what is the fee for foreign atm withdrawal"`<br>• `"what is dynamic currency conversion at atm"` | `atm_foreign_card` | Explains enabling International ATM Cash toggle in app; outlines foreign transaction fees (₹150–₹300) + 2%–3.5% forex markup; warns to choose local currency over INR to avoid inflated DCC margins. | **NO** |

---

### F. Category 3: Debit & Credit Cards (Self-Service Queries)
*Vector DB searches against RBI Card Issuance & Conduct Directions.*

| # | Sample Customer Queries | ChromaDB Scenario | Grounded Resolution Provided by Agent | Ticket Created? |
| :-: | :--- | :--- | :--- | :---: |
| **12** | • `"how to enable online transactions on my debit card"`<br>• `"how to turn on international card payments"`<br>• `"how does tap and pay contactless card work"` | `card_online_usage` | Explains RBI mandate: new cards have online/international disabled by default. Guides on 24x7 app toggle for E-commerce, Contactless (NFC up to ₹5,000 without PIN), and setting daily limits. | **NO** |
| **13** | • `"how to generate debit card pin"`<br>• `"how to create green pin for new card"`<br>• `"card pin generation steps"` | `card_pin_generation` | Outlines the 3 paperless methods: Mobile Banking (Manage Card > Set PIN > OTP), Net Banking, or Bank ATM Green PIN generation. | **NO** |
| **14** | • `"my debit card is expiring this month"`<br>• `"what does valid thru 08/26 mean"`<br>• `"when will bank send replacement card"` | `card_expiry_renewal` | Explains card is valid through the last day of the month; bank automatically manufactures and speed-posts renewed card 30–45 days prior if KYC is active; how to activate upon delivery. | **NO** |
| **15** | • `"how to redeem credit card reward points"`<br>• `"when do my reward points expire"`<br>• `"can i convert reward points to cash"` | `card_reward_points` | Explains reward point accrual on retail/online spends, 24–36 month validity window, and catalog redemption for flight tickets, vouchers, or statement cash credit. | **NO** |
| **16** | • `"what is foreign currency markup on credit card"`<br>• `"forex charges for netflix or amazon us"`<br>• `"cross border assessment fee on card"` | `card_forex_markup` | Explains 1.5% to 3.5% forex markup fee + 18% GST on foreign currency and cross-border payment conversions. | **NO** |

---

### G. Category 4: Account & Balance (Self-Service Queries)
*Vector DB searches against RBI Banking Regulations & Fair Practices Code.*

| # | Sample Customer Queries | ChromaDB Scenario | Grounded Resolution Provided by Agent | Ticket Created? |
| :-: | :--- | :--- | :--- | :---: |
| **17** | • `"how to check account balance"`<br>• `"how to download 6 months bank statement pdf"`<br>• `"what is the password for bank statement pdf"` | `account_balance_statement` | Details channels: Overview dashboard, Missed-call banking, Net Banking > Accounts > e-Statement. Explains PDF encryption password (Date of Birth DDMMYYYY + last 4 digits of account). | **NO** |
| **18** | • `"what is the difference between neft and rtgs"`<br>• `"what is imps transfer limit and timings"`<br>• `"are there charges for neft transfers online"` | `account_transfer_modes` | Compares IMPS (instant 24x7 up to ₹5L), NEFT (24x7 half-hourly batches, zero online charges for savings), and RTGS (real-time for ₹2L and above). | **NO** |
| **19** | • `"what is the penalty for minimum balance shortfall"`<br>• `"can account balance go negative due to penalty"`<br>• `"minimum average balance requirements"` | `account_min_balance` | Outlines MAB requirements by branch tier; explains RBI mandatory 30-day notice to replenish shortfall; emphasizes RBI rule that **penalties cannot turn balance negative**; notes BSBDA exemption. | **NO** |
| **20** | • `"how long does cheque clearing take"`<br>• `"what is positive pay system for cheques"`<br>• `"cheque bounce charges and rules"` | `account_cheque_clearing` | Details Cheque Truncation System (CTS) 24h clearing cycle ($T+1$ to $T+2$ days); PPS verification for cheques of ₹50,000+; Section 138 penalties for dishonored cheques. | **NO** |
| **21** | • `"how to download interest certificate for itr"`<br>• `"how to get form 16a tds certificate"`<br>• `"who can submit form 15g or form 15h"` | `account_interest_cert` | Explains downloading annual Interest Certificate and quarterly Form 16A TDS certificates from Net Banking; rules for submitting Form 15G (under 60) and Form 15H (senior citizens). | **NO** |
| **22** | • `"how to open fixed deposit online"`<br>• `"premature withdrawal penalty for fd"`<br>• `"senior citizen extra interest on fd"` | `account_fd_rd_opening` | Details digital FD/RD creation (7 days to 10 yrs); 0.50% extra interest for senior citizens; 0.5%–1% penal interest for premature closure; loan against FD up to 90%. | **NO** |
| **23** | • `"what is a dormant or inoperative account"`<br>• `"how to reactivate dormant account"`<br>• `"charges for dormant account activation"` | `account_dormant_reactivation` | Explains 24-month inactivity classification; highlights **RBI rule that reactivation is strictly free of charge**; branch KYC submission and transaction requirements. | **NO** |

---

### H. Category 5: Account Access & KYC (Self-Service Queries)
*Vector DB searches against RBI Master Direction on KYC & PML Rules.*

| # | Sample Customer Queries | ChromaDB Scenario | Grounded Resolution Provided by Agent | Ticket Created? |
| :-: | :--- | :--- | :--- | :---: |
| **24** | • `"how often is periodic re-kyc required"`<br>• `"can i complete re-kyc online without visiting branch"`<br>• `"re-kyc self-declaration steps"` | `kyc_periodic_update` | Details RBI risk intervals: Low Risk (every 10 yrs), Medium (every 8 yrs), High (every 2 yrs); explains that **if no details changed, an online self-declaration suffices without visiting a branch**. | **NO** |
| **25** | • `"what documents are required for kyc"`<br>• `"which documents are officially valid ovd"`<br>• `"is pan card mandatory for bank account"` | `kyc_valid_documents` | Lists the 6 Officially Valid Documents (Passport, Driving License, Proof of Aadhaar, Voter ID, NREGA Job Card, NPR Letter); explains PAN Card or Form 60 requirement. | **NO** |
| **26** | • `"how to update my address in bank account"`<br>• `"can i change communication address with aadhaar otp"`<br>• `"documents required for address change"` | `kyc_address_update` | Details digital address change via DigiLocker Aadhaar OTP within 24 hours vs physical branch submission with self-attested OVD. | **NO** |
| **27** | • `"how to change registered mobile number"`<br>• `"can i update mobile number at atm"`<br>• `"why cannot mobile number be updated online without otp"` | `kyc_mobile_email_update` | Details security 2FA mechanisms to prevent SIM-swap fraud: ATM card-based update, Net Banking OTP authentication, or in-person branch biometric verification. | **NO** |
| **28** | • `"my netbanking is locked due to wrong password"`<br>• `"how to unlock netbanking user access"`<br>• `"forgot netbanking password self reset"` | `kyc_netbanking_locked` | Guides customer through online self-service unlock using Customer ID, Debit Card credentials, and OTP verification without branch visits. | **NO** |
| **29** | • `"how to add nominee to bank account"`<br>• `"what is form da-1 for nomination"`<br>• `"can nominee be changed later"` | `kyc_nominee_registration` | Explains Section 45ZA statutory rights: Form DA-1 (new), Form DA-2 (cancel), Form DA-3 (modify); step-by-step Net Banking submission. | **NO** |
| **30** | • `"what is either or survivor in joint account"`<br>• `"difference between either or survivor and former or survivor"`<br>• `"who can operate joint bank account"` | `kyc_joint_account_ops` | Explains operational mandates: Either or Survivor (independent operation + sole authority to survivor on death), Former or Survivor (only primary operates while alive), and Joint operation. | **NO** |
| **31** | • `"how to claim bank balance of deceased person"`<br>• `"deceased claim settlement timeline by bank"`<br>• `"can nominee claim money without succession certificate"` | `kyc_deceased_claim` | Outlines RBI 15-day maximum settlement timeline for registered nominee upon submitting death certificate and claim form without needing probate or succession certificates. | **NO** |

---

## 3. Contrast: Queries that DO Create a Ticket and Escalate to L1 Support

When a customer reports an **active financial failure, money deduction without service, unauthorized fraud, or administrative restriction**, the AI Banking Agent immediately creates a support ticket, computes SLA deadlines, and routes to the appropriate L1 executive.

| Category | Trigger Customer Queries | Intent Detected | Auto-Ticket Action | Assigned L1 Tier | SLA Target |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **UPI** | • `"upi transaction failed but money debited from account"`<br>• `"amount debited via gpay but receiver did not get money"`<br>• `"money sent to wrong upi id by mistake please reverse"` | `UPI_TRANSACTION_FAILURE` / `UPI_WRONG_TRANSFER` | **Ticket Created (`TK-XXXXX`)** | **L1 Support** (`rajesh_l1`) | **24 Hours** ($T+1$ TAT) |
| **ATM** | • `"atm debited 5000 rs but cash was not dispensed"`<br>• `"atm machine swallowed my debit card"`<br>• `"deposited cash in cdm machine but not credited to account"` | `ATM_CASH_DISPENSE_FAILURE` / `ATM_MACHINE_ISSUE` | **Ticket Created (`TK-XXXXX`)** | **L1 Support** | **24 Hours** ($T+5$ TAT + ₹100/day compensation) |
| **Cards** | • `"unauthorized transaction on my credit card"`<br>• `"lost my debit card block it immediately"`<br>• `"billed twice for single purchase on my credit card"` | `UNAUTHORIZED_FRAUD_DISPUTE` / `CARD_BLOCK_DISPUTE` | **Ticket Created (`TK-XXXXX`)** | **L1 Support** (Priority: Urgent) | **24 Hours** (RBI 3-day zero-liability) |
| **Account** | • `"my account is frozen with debit freeze"`<br>• `"lien amount marked on my savings account"`<br>• `"cyber cell hold on my bank account"` | `ACCOUNT_RESTRICTION_DISPUTE` | **Ticket Created (`TK-XXXXX`)** | **L1 Support** | **48 Hours** |
| **KYC** | • `"re-kyc verification rejected by branch"`<br>• `"account marked inoperative despite submitted kyc"` | `KYC_VERIFICATION_DISPUTE` | **Ticket Created (`TK-XXXXX`)** | **L1 Support** | **48 Hours** |

---

## 4. Key Takeaways for Stakeholders & Developers

1. **Deflection Rate:** Over **80% of routine banking inquiries** (limits, PIN reset, statement downloads, KYC timelines, charges, transfer timings) are resolved instantly by the AI Banking Agent without human intervention.
2. **Zero Unnecessary Tickets:** Informational questions and greetings never open support tickets, keeping the L1 queue clear of clutter.
3. **Evidence-Ready Disputes:** When an actual dispute occurs, the customer is assigned a unique reference (`TK-YYYYMMDD-XXXXX`) and can upload unverified transaction slips/evidence directly for the L1 executive's investigation.
4. **Auditability:** Every ticket action, escalation, and resolution note is tracked in the `ticket_history` audit trail with strict SLA monitoring.

