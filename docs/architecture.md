# RevenueGuard AI — Architectural Specification

> **Track 01**: AI Growth & Agentic Commerce (Razorpay Hackathon)  
> **Positioning**: A Permissioned Autonomous Merchant Agent for Revenue Leak Detection and Safe Recovery.

---

## 1. System Overview & The 5 Core Layers

```
                         ┌────────────────────────────────────────┐
                         │         MERCHANT DASHBOARD (UI)        │
                         │   (Overview, Leaks, AI, Approval, Log) │
                         └───────────────────┬────────────────────┘
                                             │ REST API / JSON
                                             ↓
                         ┌────────────────────────────────────────┐
                         │         FastAPI APPLICATION CORE       │
                         └───────────────────┬────────────────────┘
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      ↓                                      ↓                                      ↓
┌───────────────────────┐         ┌───────────────────────┐         ┌───────────────────────┐
│ Layer 2: Analytics    │         │ Layer 3: AI Agent 🧠  │         │ Layer 5: Audit Ledger │
│ (Deterministic Math)  │         │ (Grounded Reasoning)  │         │ (SHA-256 Hash Chain)  │
│                       │         │                       │         │                       │
│ • Revenue at Risk     │         │ • Evidence Extraction │         │ • Genesis Block Link  │
│ • Eligible Recovery   │         │ • Known DB Facts      │         │ • Tamper Detection    │
│ • Expected Recovery   │         │ • Root Cause Diagnosis│         │ • Action Audit Trail  │
│ • Leak Categorization │         │ • Controlled Tools    │         │ • State Verifier      │
└───────────┬───────────┘         └───────────┬───────────┘         └───────────▲───────────┘
            │                                 │                                 │
            └────────────────┬────────────────┘                                 │
                             ↓                                                  │
                ┌─────────────────────────┐                                     │
                │ Layer 4: Safety Engine  │ 🛡️                                  │
                │                         │                                     │
                │ 1. Transaction Integrity│                                     │
                │ 2. Amount Match Check   │                                     │
                │ 3. Policy Ceiling Limit │                                     │
                │ 4. Idempotency Lock     │                                     │
                │ 5. Circuit Breaker Liveness                                   │
                └────────────┬────────────┘                                     │
                             │ Verified Safe Proposal                           │
                             ↓                                                  │
                ┌─────────────────────────┐                                     │
                │ Merchant Approval Gate  │ (Human-in-the-Loop)                 │
                └────────────┬────────────┘                                     │
                             │ Signed Approval Token                            │
                             ↓                                                  │
                ┌─────────────────────────┐                                     │
                │ Layer 1: Provider Layer │                                     │
                │  (PaymentProvider ABC)  │                                     │
                │            │            │                                     │
                │ ┌──────────┴──────────┐ │                                     │
                │ │ Demo Sandbox        │ │                                     │
                │ │ Razorpay Test Mode  │ │                                     │
                │ └──────────┬──────────┘ │                                     │
                └────────────┼────────────┘                                     │
                             │                                                  │
                             └──────────── Execution Result ────────────────────┘
```

---

## 2. End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Merchant
    participant UI as Merchant Dashboard
    participant API as FastAPI Backend
    participant Analytics as Deterministic Analytics
    participant Agent as RevenueGuard AI Agent
    participant Safety as Safety & Policy Engine
    participant Provider as Razorpay Payment Provider
    participant Audit as Cryptographic Audit Ledger

    Merchant->>UI: Opens Dashboard
    UI->>API: GET /api/overview
    API->>Analytics: Calculate Metrics (Direct SQLite)
    Analytics-->>API: Returns Revenue at Risk (₹2.37L), Eligible (₹1.75L), Expected (₹1.42L)
    API-->>UI: Render Metric Cards & Failure Charts

    Merchant->>UI: Clicks "Investigate with AI" (Leak ID: leak_hv_failures)
    UI->>API: POST /api/agent/investigate
    API->>Agent: investigate_leak("leak_hv_failures")
    Agent->>API: inspect_transaction("pay_hv_01")
    Agent-->>API: Synthesizes Grounded Telemetry (Evidence, Known Facts, Inference, Unknowns, Confidence)
    API->>Audit: Log Audit Event (RECOMMENDATION_GENERATED)
    Audit-->>API: Appended Block N with SHA-256 Hash
    API-->>UI: Displays 4-Box Grounded AI Reasoning & ROI Proposal

    Merchant->>UI: Clicks "Submit for Merchant Approval"
    UI->>API: POST /api/approvals/propose
    API->>Safety: validate_action("pay_hv_01", amount=18500.0)
    Safety-->>API: Safety Checks Passed (Integrity, Amount Match, Idempotency, Limit)
    API-->>UI: Action Enqueued in Approval Center

    Merchant->>UI: Clicks "Approve & Execute via Razorpay"
    UI->>API: POST /api/approvals/{action_id}/decide (decision="APPROVE")
    API->>Safety: Pre-Execution Safety Re-Check
    Safety-->>API: Passed
    API->>Provider: create_recovery_payment_link("pay_hv_01", amount=18500.0)
    Provider-->>API: Generated Razorpay Smart Link (plink_xxx, https://rzp.io/i/xxx)
    API->>Audit: Log Audit Event (RESULT_SUCCESS)
    Audit-->>API: Appended Block N+1 with SHA-256 Hash
    API-->>UI: Recovery Dispatched Successfully (Updates Timeline & Metrics)
```

---

## 3. Layer 1 — Razorpay & Payment Provider Abstraction

The system enforces a clean polymorphism pattern via `PaymentProvider`:

```python
class PaymentProvider(ABC):
    @abstractmethod
    def get_provider_name(self) -> str: ...
    @abstractmethod
    def create_recovery_payment_link(self, ...) -> Dict[str, Any]: ...
    @abstractmethod
    def fetch_transaction_status(self, ...) -> Dict[str, Any]: ...
```

- **`MockPaymentProvider`**: Generates high-fidelity synthetic Razorpay payment links, short URLs (`https://rzp.io/i/...`), and lifecycle timestamps. Used automatically when running in `ENVIRONMENT: DEMO SANDBOX`.
- **`RazorpayPaymentProvider`**: Uses the official `razorpay` Python SDK to create real payment links and query order states when `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are provided in `ENVIRONMENT: RAZORPAY TEST MODE`.

---

## 4. Layer 2 — Deterministic Analytics Engine (Zero LLM Hallucinations)

All numbers shown in the dashboard are computed directly from the SQLite transactions database using deterministic arithmetic:

1. **Total Attempted Volume**: $\sum \text{amount}_{\text{all}} = ₹18,40,000.00$
2. **Successful Volume**: $\sum \text{amount}_{\text{success}} = ₹16,03,000.00$
3. **Revenue at Risk**: $\sum \text{amount}_{\text{failed}} + \sum \text{amount}_{\text{pending}} = ₹2,37,000.00$
4. **Eligible for Recovery**: Transactions with $\text{amount} \le ₹50,000$ and age $< 7 \text{ days} = ₹1,75,000.00$
5. **Expected Recovery**: Probability-weighted recovery potential based on customer lifetime value and channel conversion rate $= ₹1,42,000.00$

### Leak Cohorts Identified
- **High-Value Failed Transactions**: 12 orders totaling ₹82,000.
- **Abandoned & Pending Orders**: 31 checkouts totaling ₹41,000.
- **Repeat Customer Payment Failures**: 7 loyal customer orders totaling ₹29,000.

---

## 5. Layer 3 — Grounded AI Reasoning Engine

Rather than unstructured prompting, the AI receives structured telemetry and outputs a 7-element grounded analysis:

$$\text{Evidence} \longrightarrow \text{Known Facts} \longrightarrow \text{Inference} \longrightarrow \text{Unknowns} \longrightarrow \text{Confidence} \longrightarrow \text{Recommendation} \longrightarrow \text{Expected Impact}$$

### Controlled Agent Toolset (Least Privilege)
The agent is restricted to read and propose tools:
- `analyze_metrics()`
- `inspect_transaction(transaction_id)`
- `inspect_customer_history(customer_id)`
- `identify_leak(leak_id)`
- `estimate_recovery(leak_id)`
- `request_recovery(transaction_id, strategy)` *(Submits to Safety Engine; cannot execute payment)*

---

## 6. Layer 4 — Deterministic Safety Engine 🛡️

The Safety Engine serves as an impenetrable security boundary between AI recommendations and payment APIs:

```mermaid
flowchart TD
    PROP[AI Proposes Recovery Action] --> CHK1{1. Transaction Exists in DB?}
    CHK1 -- No --> BLK1[BLOCKED: Unknown Transaction ID]
    CHK1 -- Yes --> CHK2{2. Requested Amount == DB Amount?}
    CHK2 -- No (Tamper) --> BLK2[BLOCKED: Amount Mismatch Alert]
    CHK2 -- Yes --> CHK3{3. Amount <= ₹50,000 Policy Limit?}
    CHK3 -- No --> BLK3[BLOCKED: Over Limit Violation]
    CHK3 -- Yes --> CHK4{4. Idempotency Key Unique?}
    CHK4 -- No (Duplicate) --> BLK4[BLOCKED: Duplicate Action Prevented]
    CHK4 -- Yes --> CHK5{5. Circuit Breaker Healthy?}
    CHK5 -- Tripped --> BLK5[BLOCKED: Downstream Outage Paused]
    CHK5 -- Healthy --> GATE[Merchant Human-in-the-Loop Gate]
    GATE --> EXEC[Execute via Razorpay Provider]
```

---

## 7. Layer 5 — Cryptographic SHA-256 Hash Chain Audit Ledger 📜

Every system action generates an immutable block linked to the previous block hash:

```
Block N Hash = SHA-256( Timestamp | EventType | Actor | Action | TxID | Amount | Metadata | Block N-1 Hash )
```

- **Live Verification**: Cryptographic validator traverses the ledger from Genesis block to latest block to verify unbroken chain integrity.
- **Tamper Simulation**: Demonstrates instantaneous detection if any database row is altered after the fact.

---

## 8. Resilience & Security Simulations

1. **Scenario A — API Timeout & Circuit Breaker**:
   - Downstream network timeout $\to$ 3 retry attempts fail $\to$ circuit breaker trips $\to$ action marked `FAILED_PENDING_RETRY` $\to$ **Guarantee**: *"No duplicate financial action was executed."*
2. **Scenario B — Duplicate Request / Idempotency Defense**:
   - Duplicate submission $\to$ Idempotency hash filter detects duplicate $\to$ **Guarantee**: *"Duplicate financial action prevented."*
3. **Scenario C — Amount Tampering Attack**:
   - Payload altered from ₹18,500 to ₹25,000 $\to$ Safety Engine flags `AMOUNT_MISMATCH` $\to$ **Guarantee**: *"Security Alert: Amount Mismatch Blocked."*
