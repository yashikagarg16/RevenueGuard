import pytest
from backend.database import init_db, reset_db
from backend.razorpay.mock_data import generate_mock_dataset
from backend.safety.policy_engine import SafetyEngine, circuit_breaker

@pytest.fixture(autouse=True)
def setup_database():
    reset_db()
    generate_mock_dataset()
    circuit_breaker.reset()

def test_valid_action_safety():
    # pay_hv_01 exists in DB with amount ₹18,500
    res = SafetyEngine.validate_action(
        transaction_id="pay_hv_01",
        requested_amount=18500.0,
        action_type="RECOVERY_PAYMENT_LINK",
        check_existing=False
    )
    assert res.is_safe is True
    assert res.rejection_reason is None
    assert all(c.passed for c in res.checks)

def test_amount_tamper_detection():
    # Attempting to change amount from 18,500 to 25,000
    res = SafetyEngine.validate_action(
        transaction_id="pay_hv_01",
        requested_amount=25000.0,
        action_type="RECOVERY_PAYMENT_LINK",
        check_existing=False
    )
    assert res.is_safe is False
    assert "TAMPER DETECTED" in str(res.checks[0].details)
    assert "does not match verified database record" in res.rejection_reason

def test_nonexistent_transaction():
    res = SafetyEngine.validate_action(
        transaction_id="pay_fake_99999",
        requested_amount=5000.0,
        action_type="RECOVERY_PAYMENT_LINK",
        check_existing=False
    )
    assert res.is_safe is False
    assert "does not exist" in res.rejection_reason

def test_over_limit_enforcement():
    res = SafetyEngine.validate_action(
        transaction_id="pay_hv_01",
        requested_amount=75000.0,  # Exceeds ₹50,000 ceiling
        action_type="RECOVERY_PAYMENT_LINK",
        check_existing=False
    )
    assert res.is_safe is False
    assert "exceeds merchant ceiling limit" in res.rejection_reason
