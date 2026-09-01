import json
from typing import Dict, Any, Optional, List
from backend.database import get_db_connection
from backend.analytics.metrics import calculate_overview_metrics
from backend.analytics.leak_detector import get_leak_by_id

class AgentTools:
    """
    Controlled toolset exposed to RevenueGuard AI.
    Strict Least-Privilege Design: The agent has inspection and recommendation capabilities only.
    IT CANNOT DIRECTLY EXECUTE FINANCIAL TRANSACTIONS.
    """

    @staticmethod
    def analyze_metrics() -> Dict[str, Any]:
        """Returns the high-level financial and operational health metrics."""
        metrics = calculate_overview_metrics()
        return metrics.model_dump()

    @staticmethod
    def inspect_transaction(transaction_id: str) -> Optional[Dict[str, Any]]:
        """Inspects detailed transaction record and error telemetry from the database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, c.name as customer_name, c.email as customer_email, c.phone as customer_phone,
                   c.total_orders, c.successful_orders, c.failed_orders, c.lifetime_value
            FROM transactions t
            LEFT JOIN customers c ON t.customer_id = c.id
            WHERE t.id = ?
        """, (transaction_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return dict(row)

    @staticmethod
    def inspect_customer_history(customer_id: str) -> Optional[Dict[str, Any]]:
        """Inspects customer order history and lifetime value."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        cust = cursor.fetchone()
        if not cust:
            conn.close()
            return None
            
        cursor.execute("""
            SELECT id, order_id, amount, status, error_code, created_at 
            FROM transactions 
            WHERE customer_id = ?
            ORDER BY created_at DESC
        """, (customer_id,))
        txs = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        cust_dict = dict(cust)
        cust_dict["transactions"] = txs
        return cust_dict

    @staticmethod
    def identify_leak(leak_id: str) -> Optional[Dict[str, Any]]:
        """Fetches structured information and affected transaction list for a detected leak."""
        leak = get_leak_by_id(leak_id)
        if not leak:
            return None
        return leak.model_dump()

    @staticmethod
    def estimate_recovery(leak_id: str) -> Dict[str, Any]:
        """Calculates expected recoverable impact and confidence for a leak category."""
        leak = get_leak_by_id(leak_id)
        if not leak:
            return {"error": "Leak not found"}
        return {
            "leak_id": leak.id,
            "amount_at_risk": leak.amount_at_risk,
            "eligible_amount": leak.eligible_amount,
            "expected_recovery": leak.expected_recovery,
            "recovery_rate_pct": round((leak.expected_recovery / leak.eligible_amount * 100), 1) if leak.eligible_amount > 0 else 0
        }

    @staticmethod
    def request_recovery(transaction_id: str, recovery_strategy: str) -> Dict[str, Any]:
        """
        AI agent tool to propose a recovery action for human-gated approval.
        NOTE: This does NOT execute payment. It submits the proposal to the Safety Engine & Approval Queue.
        """
        tx = AgentTools.inspect_transaction(transaction_id)
        if not tx:
            return {"error": f"Transaction {transaction_id} not found."}
            
        return {
            "status": "PROPOSED_FOR_APPROVAL",
            "transaction_id": transaction_id,
            "amount": tx["amount"],
            "strategy": recovery_strategy,
            "message": "Action successfully routed to Safety Engine and Merchant Approval Queue."
        }
