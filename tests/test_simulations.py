import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, reset_db
from backend.razorpay.mock_data import generate_mock_dataset
from backend.analytics.leak_detector import detect_and_sync_leaks

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_app():
    reset_db()
    generate_mock_dataset()
    detect_and_sync_leaks()

def test_scenario_a_timeout():
    res = client.post("/api/simulation/run", json={"scenario": "API_TIMEOUT", "transaction_id": "pay_hv_02"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "RESILIENT_FAILURE_HANDLED"
    assert data["circuit_breaker_active"] is True
    assert "No duplicate financial action was executed." in data["message"]

def test_scenario_b_duplicate():
    res = client.post("/api/simulation/run", json={"scenario": "DUPLICATE_REQUEST", "transaction_id": "pay_hv_01"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "BLOCKED_BY_SAFETY_ENGINE"
    assert data["duplicate_prevented"] is True
    assert "Duplicate financial action prevented." in data["message"]

def test_scenario_c_tampering():
    res = client.post("/api/simulation/run", json={
        "scenario": "AMOUNT_TAMPERING",
        "transaction_id": "pay_hv_01",
        "tampered_amount": 25000.0
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SECURITY_ATTACK_BLOCKED"
    assert data["tamper_blocked"] is True
    assert "does not match verified database record" in data["message"]
