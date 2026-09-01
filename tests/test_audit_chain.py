import pytest
from backend.database import init_db, reset_db
from backend.audit.logger import AuditLogger
from backend.models.schema import AuditEventType

@pytest.fixture(autouse=True)
def setup_database():
    reset_db()

def test_hash_chain_integrity():
    # Log 3 sequential events
    ev1 = AuditLogger.log_event(
        event_type=AuditEventType.AGENT_ANALYSIS_STARTED,
        actor="RevenueGuard AI",
        action="System initialized."
    )
    assert ev1.previous_hash == "0000000000000000000000000000000000000000000000000000000000000000"
    
    ev2 = AuditLogger.log_event(
        event_type=AuditEventType.LEAK_DETECTED,
        actor="Analytics Engine",
        action="Detected high value failure",
        amount=18500.0
    )
    assert ev2.previous_hash == ev1.event_hash
    
    ev3 = AuditLogger.log_event(
        event_type=AuditEventType.MERCHANT_APPROVED,
        actor="Merchant Admin",
        action="Approved recovery action",
        amount=18500.0
    )
    assert ev3.previous_hash == ev2.event_hash
    
    # Verify the entire chain
    res = AuditLogger.verify_audit_chain()
    assert res["chain_valid"] is True
    assert res["status"] == "VERIFIED"
    assert res["total_events"] == 3

def test_tamper_detection():
    # Log 2 events
    AuditLogger.log_event(
        event_type=AuditEventType.AGENT_ANALYSIS_STARTED,
        actor="RevenueGuard AI",
        action="Genesis block event"
    )
    AuditLogger.log_event(
        event_type=AuditEventType.RESULT_SUCCESS,
        actor="Razorpay Provider",
        action="Recovery link created"
    )
    
    # Inject unauthorized tampering in event 1
    AuditLogger.tamper_event_for_demo(1)
    
    # Verification must catch the tampering
    res = AuditLogger.verify_audit_chain()
    assert res["chain_valid"] is False
    assert res["status"] == "HASH_MISMATCH"
    assert res["corrupted_event_id"] == 1
