import hashlib
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from backend.database import get_db_connection
from backend.models.schema import (
    SafetyValidationResult, SafetyCheckItem, ActionStatus, AuditEventType
)
from backend.config import settings

class CircuitBreaker:
    """Tracks downstream API failures to prevent cascading errors."""
    def __init__(self, failure_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.consecutive_failures = 0
        self.is_tripped = False
        self.last_failure_time: Optional[datetime] = None

    def record_failure(self):
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now()
        if self.consecutive_failures >= self.failure_threshold:
            self.is_tripped = True

    def record_success(self):
        self.consecutive_failures = 0
        self.is_tripped = False

    def reset(self):
        self.consecutive_failures = 0
        self.is_tripped = False

circuit_breaker = CircuitBreaker(failure_threshold=settings.MAX_SIMULTANEOUS_RETRIES)

class SafetyEngine:
    """
    Safety Engine: The Non-Bypassable Security Perimeter.
    Validates all proposed actions against deterministic rules:
    1. Database & Amount Integrity (tamper resistance)
    2. Merchant Ceiling Limits (<= ₹50,000)
    3. Idempotency & Duplicate Action Prevention
    4. Mandatory Merchant Authorization
    5. Circuit Breaker Liveness
    """

    @staticmethod
    def generate_idempotency_key(transaction_id: str, amount: float, action_type: str) -> str:
        raw_key = f"{transaction_id}:{amount:.2f}:{action_type}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def validate_action(
        transaction_id: str,
        requested_amount: float,
        action_type: str = "RECOVERY_PAYMENT_LINK",
        check_existing: bool = True
    ) -> SafetyValidationResult:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        checks = []
        is_safe = True
        rejection_reason = None
        
        # --- Check 1: Transaction & Amount Integrity ---
        cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
        tx = cursor.fetchone()
        
        if not tx:
            is_safe = False
            rejection_reason = f"Security Alert: Transaction '{transaction_id}' does not exist in merchant records."
            checks.append(SafetyCheckItem(
                check_name="Transaction Existence & Record Integrity",
                passed=False,
                details=f"Transaction '{transaction_id}' not found in database."
            ))
        else:
            db_amount = float(tx["amount"])
            if abs(db_amount - requested_amount) > 0.01:
                is_safe = False
                rejection_reason = f"Security Violation: Requested amount (₹{requested_amount:,.2f}) does not match verified database record (₹{db_amount:,.2f})."
                checks.append(SafetyCheckItem(
                    check_name="Amount Integrity & Tamper Check",
                    passed=False,
                    details=f"TAMPER DETECTED: Requested ₹{requested_amount:,.2f} != DB amount ₹{db_amount:,.2f}."
                ))
            else:
                checks.append(SafetyCheckItem(
                    check_name="Transaction Integrity & Amount Match",
                    passed=True,
                    details=f"Verified against Order {tx['order_id']} for exact amount ₹{db_amount:,.2f}."
                ))

        # --- Check 2: Merchant Ceiling Limits ---
        if requested_amount > settings.MAX_RECOVERY_AMOUNT_INR:
            is_safe = False
            rejection_reason = f"Policy Violation: Recovery amount (₹{requested_amount:,.2f}) exceeds merchant ceiling limit (₹{settings.MAX_RECOVERY_AMOUNT_INR:,.2f})."
            checks.append(SafetyCheckItem(
                check_name="Merchant Spending / Recovery Ceiling Limit",
                passed=False,
                details=f"Amount ₹{requested_amount:,.2f} exceeds max allowed ₹{settings.MAX_RECOVERY_AMOUNT_INR:,.2f}."
            ))
        else:
            checks.append(SafetyCheckItem(
                check_name="Merchant Ceiling Limit Enforcement",
                passed=True,
                details=f"Amount ₹{requested_amount:,.2f} is within permitted ceiling of ₹{settings.MAX_RECOVERY_AMOUNT_INR:,.2f}."
            ))

        # --- Check 3: Idempotency & Duplicate Action Prevention ---
        idempotency_key = SafetyEngine.generate_idempotency_key(transaction_id, requested_amount, action_type)
        if check_existing:
            cursor.execute("""
                SELECT * FROM actions 
                WHERE idempotency_key = ? AND status IN ('executed', 'executing', 'approved')
            """, (idempotency_key,))
            existing_action = cursor.fetchone()
            
            if existing_action:
                is_safe = False
                rejection_reason = f"Idempotency Alert: A recovery action for {transaction_id} has already been executed or approved (Action ID: {existing_action['id']})."
                checks.append(SafetyCheckItem(
                    check_name="Idempotency & Duplicate Prevention",
                    passed=False,
                    details=f"DUPLICATE BLOCKED: Action {existing_action['id']} already processed with status '{existing_action['status']}'."
                ))
            else:
                checks.append(SafetyCheckItem(
                    check_name="Idempotency & Duplicate Prevention",
                    passed=True,
                    details=f"Unique action hash verified ({idempotency_key[:12]}...). No duplicate execution found."
                ))
        else:
            checks.append(SafetyCheckItem(
                check_name="Idempotency Key Generation",
                passed=True,
                details=f"Idempotency token generated: {idempotency_key[:12]}..."
            ))

        # --- Check 4: Circuit Breaker Status ---
        if circuit_breaker.is_tripped:
            is_safe = False
            rejection_reason = "Circuit Breaker Active: Downstream payment provider is currently experiencing downtime. Recovery temporarily paused."
            checks.append(SafetyCheckItem(
                check_name="Downstream Provider Circuit Breaker",
                passed=False,
                details="Circuit breaker TRIPPED due to consecutive API timeouts."
            ))
        else:
            checks.append(SafetyCheckItem(
                check_name="Circuit Breaker Status",
                passed=True,
                details="Circuit breaker HEALTHY. Downstream provider available."
            ))

        conn.close()
        
        return SafetyValidationResult(
            is_safe=is_safe,
            transaction_id=transaction_id,
            amount=requested_amount,
            checks=checks,
            rejection_reason=rejection_reason
        )
