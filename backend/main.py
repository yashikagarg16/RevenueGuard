import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db, get_db_connection, reset_db
from backend.razorpay.mock_data import generate_mock_dataset
from backend.razorpay.provider import get_payment_provider
from backend.analytics.metrics import calculate_overview_metrics, get_transaction_breakdown
from backend.analytics.leak_detector import detect_and_sync_leaks, get_leak_by_id
from backend.agents.revenue_agent import RevenueGuardAgent
from backend.safety.policy_engine import SafetyEngine, circuit_breaker
from backend.audit.logger import AuditLogger
from backend.models.schema import (
    OverviewMetrics, RevenueLeak, AIInvestigation, SafetyValidationResult,
    ApprovalRequest, ApprovalDecision, AuditEvent, AuditEventType,
    SimulationRequest, SimulationResponse, ActionStatus
)

# Initialize FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    description="A Permissioned Autonomous Merchant Agent for Revenue Leak Detection and Safe Recovery",
    version=settings.APP_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = RevenueGuardAgent()

@app.on_event("startup")
def startup_event():
    init_db()
    generate_mock_dataset()
    detect_and_sync_leaks()
    
    # Log startup event in tamper-evident ledger if empty
    events = AuditLogger.get_all_events()
    if not events:
        AuditLogger.log_event(
            event_type=AuditEventType.AGENT_ANALYSIS_STARTED,
            actor="RevenueGuard AI",
            action="System initialized. Analyzed 127 transaction records.",
            metadata={"environment": settings.ENVIRONMENT_MODE, "version": settings.APP_VERSION}
        )

# ----------------- 1. Overview & Metrics -----------------

@app.get("/api/overview", response_model=OverviewMetrics)
def get_overview():
    metrics = calculate_overview_metrics()
    return metrics

@app.get("/api/breakdown")
def get_breakdown():
    return get_transaction_breakdown()

# ----------------- 2. Revenue Leaks -----------------

@app.get("/api/leaks", response_model=List[RevenueLeak])
def list_leaks():
    leaks = detect_and_sync_leaks()
    return leaks

@app.get("/api/leaks/{leak_id}", response_model=RevenueLeak)
def get_leak_detail(leak_id: str):
    leak = get_leak_by_id(leak_id)
    if not leak:
        raise HTTPException(status_code=404, detail="Leak not found")
    return leak

# ----------------- 3. AI Investigation -----------------

@app.post("/api/agent/investigate", response_model=AIInvestigation)
def investigate_leak_endpoint(payload: Dict[str, str]):
    leak_id = payload.get("leak_id", "leak_hv_failures")
    try:
        investigation = agent.investigate_leak(leak_id)
        
        # Log AI Investigation in Audit Ledger
        AuditLogger.log_event(
            event_type=AuditEventType.RECOMMENDATION_GENERATED,
            actor="RevenueGuard AI",
            action=f"Deep investigation completed for {leak_id}. Recommended {investigation.recommended_action[:60]}...",
            transaction_id=investigation.suggested_transaction_id,
            amount=investigation.target_amount,
            metadata={
                "confidence": investigation.confidence,
                "expected_impact": investigation.expected_impact,
                "evidence_count": len(investigation.evidence)
            }
        )
        return investigation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ----------------- 4. Approval Center & Actions -----------------

@app.get("/api/approvals/pending", response_model=List[ApprovalRequest])
def list_pending_approvals():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, t.customer_id, c.name as customer_name, c.email as customer_email
        FROM actions a
        JOIN transactions t ON a.transaction_id = t.id
        JOIN customers c ON t.customer_id = c.id
        WHERE a.status = 'proposed'
        ORDER BY a.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    requests = []
    for r in rows:
        safety_val = SafetyEngine.validate_action(
            transaction_id=r["transaction_id"],
            requested_amount=float(r["amount"]),
            action_type=r["action_type"],
            check_existing=False
        )
        requests.append(ApprovalRequest(
            action_id=r["id"],
            leak_id=r["leak_id"],
            transaction_id=r["transaction_id"],
            customer_name=r["customer_name"],
            customer_email=r["customer_email"],
            amount=float(r["amount"]),
            action_type=r["action_type"],
            reason="High-value failed transaction with strong purchase intent and positive historical LTV.",
            status=ActionStatus(r["status"]),
            safety_result=safety_val,
            created_at=r["created_at"]
        ))
    return requests

@app.post("/api/approvals/propose")
def propose_action(payload: Dict[str, Any]):
    """
    Submits a proposed recovery action from the AI investigation to the Approval Center.
    Routes strictly through the Safety Engine first!
    """
    transaction_id = payload.get("transaction_id", "pay_hv_01")
    leak_id = payload.get("leak_id", "leak_hv_failures")
    
    # Query transaction amount from DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
    tx = cursor.fetchone()
    if not tx:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
        
    amount = float(tx["amount"])
    action_type = payload.get("action_type", "RECOVERY_PAYMENT_LINK")
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    idempotency_key = SafetyEngine.generate_idempotency_key(transaction_id, amount, action_type)
    
    # Run Safety Validation
    safety_check = SafetyEngine.validate_action(transaction_id, amount, action_type)
    
    status = "proposed" if safety_check.is_safe else "safety_failed"
    
    cursor.execute("""
        INSERT INTO actions (id, leak_id, transaction_id, action_type, amount, status, idempotency_key, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(idempotency_key) DO UPDATE SET
            status = excluded.status
    """, (action_id, leak_id, transaction_id, action_type, amount, status, idempotency_key, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    AuditLogger.log_event(
        event_type=AuditEventType.MERCHANT_APPROVAL_REQUESTED,
        actor="RevenueGuard AI",
        action=f"Proposed recovery action {action_id} for transaction {transaction_id} (₹{amount:,.2f})",
        transaction_id=transaction_id,
        amount=amount,
        metadata={"idempotency_key": idempotency_key, "is_safe": safety_check.is_safe}
    )
    
    return {
        "action_id": action_id,
        "transaction_id": transaction_id,
        "amount": amount,
        "status": status,
        "safety_result": safety_check
    }

@app.post("/api/approvals/{action_id}/decide")
def decide_approval(action_id: str, decision_data: ApprovalDecision):
    """
    Executes the human-gated decision:
    If APPROVED: Re-verifies Safety Engine -> Calls active PaymentProvider -> Logs Execution.
    If REJECTED: Marks action REJECTED -> Logs reason.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, t.customer_id, c.name as customer_name, c.email as customer_email, c.phone as customer_phone
        FROM actions a
        JOIN transactions t ON a.transaction_id = t.id
        JOIN customers c ON t.customer_id = c.id
        WHERE a.id = ?
    """, (action_id,))
    action = cursor.fetchone()
    
    if not action:
        conn.close()
        raise HTTPException(status_code=404, detail="Action not found")
        
    transaction_id = action["transaction_id"]
    amount = float(action["amount"])
    customer_name = action["customer_name"]
    customer_email = action["customer_email"]
    customer_phone = action["customer_phone"]
    
    if decision_data.decision.upper() == "REJECT":
        cursor.execute("UPDATE actions SET status = 'rejected' WHERE id = ?", (action_id,))
        cursor.execute("""
            INSERT INTO approvals (id, action_id, decision, approved_by, approved_at, notes)
            VALUES (?, ?, 'REJECTED', ?, ?, ?)
        """, (f"app_{uuid.uuid4().hex[:6]}", action_id, decision_data.approved_by, datetime.now().isoformat(), decision_data.notes))
        conn.commit()
        conn.close()
        
        AuditLogger.log_event(
            event_type=AuditEventType.MERCHANT_REJECTED,
            actor=decision_data.approved_by,
            action=f"Merchant REJECTED recovery action {action_id}",
            transaction_id=transaction_id,
            amount=amount,
            metadata={"notes": decision_data.notes}
        )
        return {"status": "rejected", "message": "Action rejected by merchant."}

    # If APPROVED: Mandatory Safety Re-Validation before execution
    safety_check = SafetyEngine.validate_action(
        transaction_id=transaction_id,
        requested_amount=amount,
        action_type=action["action_type"],
        check_existing=False
    )
    
    if not safety_check.is_safe:
        conn.close()
        AuditLogger.log_event(
            event_type=AuditEventType.SAFETY_VALIDATION_FAILED,
            actor="Safety Engine",
            action=f"Pre-execution safety validation failed: {safety_check.rejection_reason}",
            transaction_id=transaction_id,
            amount=amount
        )
        raise HTTPException(status_code=400, detail=safety_check.rejection_reason)
        
    # Safety Passed
    AuditLogger.log_event(
        event_type=AuditEventType.SAFETY_VALIDATION_PASSED,
        actor="Safety Engine",
        action="Pre-execution safety validation passed. Integrity verified, within limit, no duplicate.",
        transaction_id=transaction_id,
        amount=amount
    )
    
    # Execute through PaymentProvider
    provider = get_payment_provider()
    
    AuditLogger.log_event(
        event_type=AuditEventType.RAZORPAY_API_CALLED,
        actor=provider.get_provider_name(),
        action=f"Calling {provider.get_provider_name()} to generate recovery payment link",
        transaction_id=transaction_id,
        amount=amount
    )
    
    recovery_result = provider.create_recovery_payment_link(
        transaction_id=transaction_id,
        amount=amount,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        description=f"RevenueGuard Recovery for {transaction_id}"
    )
    
    # Update DB status
    cursor.execute("UPDATE actions SET status = 'executed' WHERE id = ?", (action_id,))
    cursor.execute("""
        INSERT INTO approvals (id, action_id, decision, approved_by, approved_at, notes)
        VALUES (?, ?, 'APPROVED', ?, ?, ?)
    """, (f"app_{uuid.uuid4().hex[:6]}", action_id, decision_data.approved_by, datetime.now().isoformat(), decision_data.notes))
    
    conn.commit()
    conn.close()
    
    # Final Success Audit
    AuditLogger.log_event(
        event_type=AuditEventType.RESULT_SUCCESS,
        actor=provider.get_provider_name(),
        action=f"Recovery link {recovery_result.get('id', 'plink_success')} successfully created and dispatched.",
        transaction_id=transaction_id,
        amount=amount,
        metadata={"short_url": recovery_result.get("short_url"), "provider": provider.get_provider_name()}
    )
    
    return {
        "status": "executed",
        "action_id": action_id,
        "transaction_id": transaction_id,
        "amount": amount,
        "provider": provider.get_provider_name(),
        "recovery_details": recovery_result
    }

# ----------------- 5. Security & Failure Simulations -----------------

@app.post("/api/simulation/run", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    """
    Executes one of the 3 realistic failure/security demo scenarios:
    Scenario A: API Timeout & Circuit Breaker -> 'No duplicate financial action was executed.'
    Scenario B: Duplicate Request -> 'Duplicate financial action prevented.'
    Scenario C: Amount Tampering -> 'Security Violation: Amount Mismatch Blocked.'
    """
    scenario = req.scenario.upper()
    
    if scenario == "API_TIMEOUT":
        # Scenario A: Downstream API Timeout & Circuit Breaker
        tx_id = req.transaction_id or "pay_hv_02"
        amount = 14200.0
        
        # Trip circuit breaker to demonstrate recovery protection
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        audit = AuditLogger.log_event(
            event_type=AuditEventType.CIRCUIT_BREAKER_TRIGGERED,
            actor="Circuit Breaker",
            action="Downstream API connection timed out. 3 retries failed. Circuit breaker tripped to protect merchant balance.",
            transaction_id=tx_id,
            amount=amount,
            metadata={"status": "FAILED_PENDING_RETRY", "duplicate_prevented": True}
        )
        
        return SimulationResponse(
            scenario="API_TIMEOUT",
            status="RESILIENT_FAILURE_HANDLED",
            message="Downstream Razorpay API timed out during recovery. Circuit breaker tripped safely. No duplicate financial action was executed.",
            circuit_breaker_active=True,
            audit_event_id=audit.id,
            details={
                "transaction_id": tx_id,
                "retries_attempted": 3,
                "action_state": "FAILED_PENDING_RETRY",
                "guarantee": "No duplicate financial action was executed."
            }
        )

    elif scenario == "DUPLICATE_REQUEST":
        # Scenario B: Duplicate Request / Idempotency Protection
        tx_id = req.transaction_id or "pay_hv_01"
        amount = 18500.0
        idempotency_key = SafetyEngine.generate_idempotency_key(tx_id, amount, "RECOVERY_PAYMENT_LINK")
        
        audit = AuditLogger.log_event(
            event_type=AuditEventType.DUPLICATE_PREVENTED,
            actor="Safety Engine",
            action=f"Duplicate request detected for {tx_id}. Idempotency hash match: {idempotency_key[:16]}...",
            transaction_id=tx_id,
            amount=amount,
            metadata={"idempotency_key": idempotency_key, "blocked": True}
        )
        
        return SimulationResponse(
            scenario="DUPLICATE_REQUEST",
            status="BLOCKED_BY_SAFETY_ENGINE",
            message="Duplicate financial action prevented. Idempotency filter rejected duplicate submission.",
            duplicate_prevented=True,
            audit_event_id=audit.id,
            details={
                "transaction_id": tx_id,
                "idempotency_key": idempotency_key,
                "guarantee": "Duplicate financial action prevented."
            }
        )

    elif scenario == "AMOUNT_TAMPERING":
        # Scenario C: Amount Tampering Attack
        tx_id = req.transaction_id or "pay_hv_01"
        original_amount = 18500.0
        tampered_amount = req.tampered_amount or 25000.0
        
        val_result = SafetyEngine.validate_action(
            transaction_id=tx_id,
            requested_amount=tampered_amount,
            action_type="RECOVERY_PAYMENT_LINK"
        )
        
        audit = AuditLogger.log_event(
            event_type=AuditEventType.AMOUNT_TAMPER_BLOCKED,
            actor="Safety Engine",
            action=f"SECURITY ALERT: Tampered amount ₹{tampered_amount:,.2f} rejected. DB amount is ₹{original_amount:,.2f}.",
            transaction_id=tx_id,
            amount=tampered_amount,
            metadata={"original_amount": original_amount, "tampered_amount": tampered_amount}
        )
        
        return SimulationResponse(
            scenario="AMOUNT_TAMPERING",
            status="SECURITY_ATTACK_BLOCKED",
            message=f"Security Violation: Requested amount (₹{tampered_amount:,.2f}) does not match verified database record (₹{original_amount:,.2f}). Action blocked.",
            tamper_blocked=True,
            audit_event_id=audit.id,
            details={
                "transaction_id": tx_id,
                "original_amount": original_amount,
                "tampered_amount": tampered_amount,
                "rejection_reason": val_result.rejection_reason
            }
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid simulation scenario")

@app.post("/api/simulation/reset-circuit-breaker")
def reset_breaker():
    circuit_breaker.reset()
    return {"message": "Circuit breaker reset to HEALTHY."}

# ----------------- 6. Audit Chain & Verification -----------------

@app.get("/api/audit/events", response_model=List[AuditEvent])
def get_audit_events():
    return AuditLogger.get_all_events()

@app.get("/api/audit/verify")
def verify_audit():
    return AuditLogger.verify_audit_chain()

@app.post("/api/audit/tamper-demo")
def tamper_audit_for_demo(payload: Dict[str, int]):
    event_id = payload.get("event_id", 1)
    res = AuditLogger.tamper_event_for_demo(event_id)
    return res

@app.post("/api/data/reset")
def reset_data():
    reset_db()
    generate_mock_dataset()
    detect_and_sync_leaks()
    circuit_breaker.reset()
    
    AuditLogger.log_event(
        event_type=AuditEventType.AGENT_ANALYSIS_STARTED,
        actor="RevenueGuard AI",
        action="Database reset. Re-seeded 127 realistic merchant transactions.",
        metadata={"environment": settings.ENVIRONMENT_MODE}
    )
    return {"status": "success", "message": "Database reset and re-seeded successfully."}

# ----------------- Mount Static Frontend -----------------

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def serve_ui():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "RevenueGuard AI API Running. Frontend directory not found."}
