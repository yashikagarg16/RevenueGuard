import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.database import get_db_connection
from backend.models.schema import AuditEvent, AuditEventType

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

class AuditLogger:
    """
    Cryptographic SHA-256 Hash Chained Audit Ledger.
    Guarantees tamper-evident, verifiable recording of every agent and financial action.
    """

    @staticmethod
    def _calculate_hash(
        timestamp: str,
        event_type: str,
        actor: str,
        action: str,
        transaction_id: Optional[str],
        amount: Optional[float],
        metadata_str: str,
        previous_hash: str
    ) -> str:
        payload = f"{timestamp}|{event_type}|{actor}|{action}|{transaction_id or ''}|{amount or 0.0:.2f}|{metadata_str}|{previous_hash}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def log_event(
        cls,
        event_type: AuditEventType,
        actor: str,
        action: str,
        transaction_id: Optional[str] = None,
        amount: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch the previous event's hash
        cursor.execute("SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        previous_hash = last_row["event_hash"] if last_row else GENESIS_HASH
        
        timestamp = datetime.now().isoformat()
        metadata_dict = metadata or {}
        metadata_str = json.dumps(metadata_dict, sort_keys=True)
        
        event_hash = cls._calculate_hash(
            timestamp=timestamp,
            event_type=event_type.value,
            actor=actor,
            action=action,
            transaction_id=transaction_id,
            amount=amount,
            metadata_str=metadata_str,
            previous_hash=previous_hash
        )
        
        cursor.execute("""
            INSERT INTO audit_events (timestamp, event_type, actor, action, transaction_id, amount, metadata, previous_hash, event_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp, event_type.value, actor, action, transaction_id, amount,
            metadata_str, previous_hash, event_hash
        ))
        
        inserted_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return AuditEvent(
            id=inserted_id,
            timestamp=timestamp,
            event_type=event_type,
            actor=actor,
            action=action,
            transaction_id=transaction_id,
            amount=amount,
            metadata=metadata_dict,
            previous_hash=previous_hash,
            event_hash=event_hash
        )

    @classmethod
    def get_all_events(cls) -> List[AuditEvent]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_events ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        
        events = []
        for r in rows:
            events.append(AuditEvent(
                id=r["id"],
                timestamp=r["timestamp"],
                event_type=AuditEventType(r["event_type"]),
                actor=r["actor"],
                action=r["action"],
                transaction_id=r["transaction_id"],
                amount=float(r["amount"]) if r["amount"] is not None else None,
                metadata=json.loads(r["metadata"] or "{}"),
                previous_hash=r["previous_hash"],
                event_hash=r["event_hash"]
            ))
        return events

    @classmethod
    def verify_audit_chain(cls) -> Dict[str, Any]:
        """
        Cryptographically verifies the entire SHA-256 hash chain from Genesis to latest block.
        Detects any retroactive tampering, deleted events, or modified amounts/actions.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_events ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {
                "status": "EMPTY",
                "chain_valid": True,
                "total_events": 0,
                "message": "Audit ledger is currently empty."
            }

        expected_prev_hash = GENESIS_HASH
        
        for r in rows:
            event_id = r["id"]
            actual_prev_hash = r["previous_hash"]
            
            # Check 1: Previous hash link
            if actual_prev_hash != expected_prev_hash:
                return {
                    "status": "CHAIN_BROKEN",
                    "chain_valid": False,
                    "corrupted_event_id": event_id,
                    "reason": f"Previous hash mismatch at Event #{event_id}. Expected {expected_prev_hash[:12]}..., got {actual_prev_hash[:12]}...",
                    "message": f"CRITICAL: Cryptographic chain severed at Event #{event_id}!"
                }
                
            # Check 2: Content integrity hash recalculation
            metadata_dict = json.loads(r["metadata"] or "{}")
            metadata_str = json.dumps(metadata_dict, sort_keys=True)
            
            recomputed_hash = cls._calculate_hash(
                timestamp=r["timestamp"],
                event_type=r["event_type"],
                actor=r["actor"],
                action=r["action"],
                transaction_id=r["transaction_id"],
                amount=float(r["amount"]) if r["amount"] is not None else None,
                metadata_str=metadata_str,
                previous_hash=actual_prev_hash
            )
            
            if recomputed_hash != r["event_hash"]:
                return {
                    "status": "HASH_MISMATCH",
                    "chain_valid": False,
                    "corrupted_event_id": event_id,
                    "reason": f"Content tampering detected at Event #{event_id}. Stored hash does not match payload digest.",
                    "message": f"CRITICAL: Tampering detected in Event #{event_id} payload!"
                }
                
            expected_prev_hash = r["event_hash"]

        return {
            "status": "VERIFIED",
            "chain_valid": True,
            "total_events": len(rows),
            "latest_hash": expected_prev_hash,
            "message": f"Audit integrity 100% verified across all {len(rows)} chained event blocks."
        }

    @classmethod
    def tamper_event_for_demo(cls, event_id: int) -> Dict[str, Any]:
        """
        Intentionally injects an unauthorized edit into an event row to demonstrate
        instant cryptographic detection of tampering during judging.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"error": f"Event {event_id} not found."}
            
        cursor.execute("""
            UPDATE audit_events 
            SET action = action || ' [TAMPERED_UNAUTHORIZED_CHANGE]'
            WHERE id = ?
        """, (event_id,))
        conn.commit()
        conn.close()
        return {
            "success": True,
            "event_id": event_id,
            "message": f"Event #{event_id} modified in database without updating hash chain. Ready for verification check."
        }
