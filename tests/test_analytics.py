import pytest
from backend.database import init_db, reset_db
from backend.razorpay.mock_data import generate_mock_dataset
from backend.analytics.metrics import calculate_overview_metrics
from backend.analytics.leak_detector import detect_and_sync_leaks

@pytest.fixture(autouse=True)
def setup_database():
    reset_db()
    generate_mock_dataset()
    detect_and_sync_leaks()

def test_deterministic_metrics():
    metrics = calculate_overview_metrics()
    
    # 1. Volume & Count assertions (127 total transactions)
    assert metrics.total_transactions == 127
    assert metrics.successful_transactions == 70
    assert metrics.failed_transactions == 26
    assert metrics.pending_transactions == 31
    assert metrics.total_attempted_revenue == 1840000.0
    assert metrics.successful_revenue == 1603000.0
    
    # 2. Three distinct financial tiers
    assert metrics.revenue_at_risk == 237000.0
    assert metrics.eligible_for_recovery == 175000.0
    assert metrics.expected_recovery == 142000.0
    
    # 3. Operational failure rate (26 / 127 = 20.5%)
    assert metrics.failure_rate_percentage == 20.5

def test_leak_detection_categories():
    leaks = detect_and_sync_leaks()
    assert len(leaks) == 3
    
    leak_types = [l.type.value for l in leaks]
    assert "high_value_failure" in leak_types
    assert "abandoned_order" in leak_types
    assert "repeat_customer_failure" in leak_types
    
    # 100% Mathematical Reconciliation Check: Sum of 3 Leaks == 237,000.0
    total_leaks_amount = sum(l.amount_at_risk for l in leaks)
    assert total_leaks_amount == 237000.0
    
    total_expected_recovery = sum(l.expected_recovery for l in leaks)
    assert total_expected_recovery == 142000.0
    
    # High-value leak assertions (14 orders, ₹1,12,000.0)
    hv_leak = next(l for l in leaks if l.type.value == "high_value_failure")
    assert hv_leak.amount_at_risk == 112000.0
    assert hv_leak.expected_recovery == 67200.0
    assert hv_leak.affected_count == 14
    
    # Abandoned orders assertions (31 orders, ₹64,000.0)
    pend_leak = next(l for l in leaks if l.type.value == "abandoned_order")
    assert pend_leak.amount_at_risk == 64000.0
    assert pend_leak.expected_recovery == 38400.0
    assert pend_leak.affected_count == 31
    
    # Repeat friction assertions (12 orders across 7 customers, ₹61,000.0)
    rep_leak = next(l for l in leaks if l.type.value == "repeat_customer_failure")
    assert rep_leak.amount_at_risk == 61000.0
    assert rep_leak.expected_recovery == 36400.0
    assert rep_leak.affected_count == 12
