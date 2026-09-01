from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class PaymentStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"

class LeakType(str, Enum):
    HIGH_VALUE_FAILURE = "high_value_failure"
    ABANDONED_ORDER = "abandoned_order"
    REPEAT_CUSTOMER_FAILURE = "repeat_customer_failure"

class LeakSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    SAFETY_PASSED = "safety_passed"
    SAFETY_FAILED = "safety_failed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"
    BLOCKED = "blocked"

class AuditEventType(str, Enum):
    AGENT_ANALYSIS_STARTED = "AGENT_ANALYSIS_STARTED"
    TRANSACTIONS_ANALYZED = "TRANSACTIONS_ANALYZED"
    LEAK_DETECTED = "LEAK_DETECTED"
    RECOMMENDATION_GENERATED = "RECOMMENDATION_GENERATED"
    MERCHANT_APPROVAL_REQUESTED = "MERCHANT_APPROVAL_REQUESTED"
    MERCHANT_APPROVED = "MERCHANT_APPROVED"
    MERCHANT_REJECTED = "MERCHANT_REJECTED"
    SAFETY_VALIDATION_PASSED = "SAFETY_VALIDATION_PASSED"
    SAFETY_VALIDATION_FAILED = "SAFETY_VALIDATION_FAILED"
    RAZORPAY_API_CALLED = "RAZORPAY_API_CALLED"
    RECOVERY_INITIATED = "RECOVERY_INITIATED"
    RESULT_SUCCESS = "RESULT_SUCCESS"
    RESULT_FAILURE = "RESULT_FAILURE"
    CIRCUIT_BREAKER_TRIGGERED = "CIRCUIT_BREAKER_TRIGGERED"
    DUPLICATE_PREVENTED = "DUPLICATE_PREVENTED"
    AMOUNT_TAMPER_BLOCKED = "AMOUNT_TAMPER_BLOCKED"

# Customer schema
class Customer(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    lifetime_value: float = 0.0

# Transaction schema
class Transaction(BaseModel):
    id: str
    order_id: str
    customer_id: str
    amount: float
    currency: str = "INR"
    status: PaymentStatus
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    created_at: str
    updated_at: str

# Metric Overview schema
class OverviewMetrics(BaseModel):
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    pending_transactions: int
    total_attempted_revenue: float
    successful_revenue: float
    # Three distinct financial tiers
    revenue_at_risk: float
    eligible_for_recovery: float
    expected_recovery: float
    failure_rate_percentage: float
    high_value_failure_count: int
    pending_order_count: int
    repeat_failed_customer_count: int
    environment_mode: str

# Detected Leak schema
class RevenueLeak(BaseModel):
    id: str
    type: LeakType
    title: str
    description: str
    severity: LeakSeverity
    amount_at_risk: float
    eligible_amount: float
    expected_recovery: float
    affected_count: int
    confidence: str = "High"
    sample_transaction_ids: List[str] = []
    created_at: str

# Grounded AI Investigation schema (Evidence -> Known Facts -> Inference -> Unknowns -> Confidence -> Recommendation -> Impact)
class AIInvestigation(BaseModel):
    leak_id: str
    leak_type: LeakType
    evidence: List[str] = Field(description="Directly observed telemetry and error data")
    known_facts: List[str] = Field(description="Deterministic database facts: amounts, order history, timestamps")
    inference: str = Field(description="High-probability operational diagnosis")
    unknowns: List[str] = Field(description="Data missing from gateway/issuing bank")
    confidence: str = Field(description="High, Medium, or Low with grounded rationale")
    recommended_action: str = Field(description="Specific recovery action strategy")
    action_type: str = "RECOVERY_PAYMENT_LINK"
    suggested_transaction_id: str
    target_amount: float
    expected_impact: float
    roi_percentage: float
    created_at: str

# Safety Policy Evaluation Result
class SafetyCheckItem(BaseModel):
    check_name: str
    passed: bool
    details: str

class SafetyValidationResult(BaseModel):
    is_safe: bool
    transaction_id: str
    amount: float
    checks: List[SafetyCheckItem]
    rejection_reason: Optional[str] = None

# Approval Request
class ApprovalRequest(BaseModel):
    action_id: str
    leak_id: str
    transaction_id: str
    customer_name: str
    customer_email: str
    amount: float
    action_type: str
    reason: str
    status: ActionStatus
    safety_result: SafetyValidationResult
    created_at: str

# Decision on Approval
class ApprovalDecision(BaseModel):
    action_id: str
    decision: str  # "APPROVE" or "REJECT"
    approved_by: str = "Merchant Admin"
    notes: Optional[str] = None

# Audit Log Event (SHA-256 Chained)
class AuditEvent(BaseModel):
    id: int
    timestamp: str
    event_type: AuditEventType
    actor: str  # "RevenueGuard AI", "Safety Engine", "Merchant Admin", "Razorpay Provider"
    action: str
    transaction_id: Optional[str] = None
    amount: Optional[float] = None
    metadata: Dict[str, Any] = {}
    previous_hash: str
    event_hash: str

# Simulation Requests & Results
class SimulationRequest(BaseModel):
    scenario: str  # "API_TIMEOUT", "DUPLICATE_REQUEST", "AMOUNT_TAMPERING"
    transaction_id: Optional[str] = None
    tampered_amount: Optional[float] = None

class SimulationResponse(BaseModel):
    scenario: str
    status: str
    message: str
    circuit_breaker_active: bool = False
    duplicate_prevented: bool = False
    tamper_blocked: bool = False
    audit_event_id: Optional[int] = None
    details: Dict[str, Any] = {}
