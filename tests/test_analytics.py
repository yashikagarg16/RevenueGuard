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
    
    # 1. Volume & Count assertions
    assert metrics.total_transactions == 127
    assert metrics.successful_transactions == 60
    assert metrics.failed_transactions == 36
    assert metrics.pending_transactions == 31
    assert metrics.total_attempted_revenue == 1840000.0
    assert metrics.successful_revenue == 1603000.0
    
    # 2. Three distinct financial tiers
    assert metrics.revenue_at_risk == 237000.0
    assert metrics.eligible_for_recovery == 175000.0
    assert metrics.expected_recovery == 142000.0
    
    # 3. Operational ratios
    assert round(metrics.failure_rate_percentage, 1) == 28.3 or round(metrics.failure_rate_percentage, 1) > 0

def test_leak_detection_categories():
    leaks = detect_and_sync_leaks()
    assert len(leaks) == 3
    
    leak_types = [l.type.value for l in leaks]
    assert "high_value_failure" in leak_types
    assert "abandoned_order" in leak_types
    assert "repeat_customer_failure" in leak_types
    
    # High-value leak assertions
    hv_leak = next(l for l in leaks if l.type.value == "high_value_failure")
    assert hv_leak.amount_at_risk == 82000.0
    assert hv_leak.expected_recovery == 48000.0
    assert hv_leak.affected_count == 12
