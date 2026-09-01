import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.config import settings

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Customers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            total_orders INTEGER DEFAULT 0,
            successful_orders INTEGER DEFAULT 0,
            failed_orders INTEGER DEFAULT 0,
            lifetime_value REAL DEFAULT 0.0,
            created_at TEXT NOT NULL
        )
    """)
    
    # 2. Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'INR',
            status TEXT NOT NULL,
            error_code TEXT,
            error_description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    """)
    
    # 3. Leaks Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leaks (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT NOT NULL,
            amount_at_risk REAL NOT NULL,
            eligible_amount REAL NOT NULL,
            expected_recovery REAL NOT NULL,
            affected_count INTEGER NOT NULL,
            confidence TEXT DEFAULT 'High',
            sample_transaction_ids TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # 4. Actions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id TEXT PRIMARY KEY,
            leak_id TEXT NOT NULL,
            transaction_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            idempotency_key TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES transactions (id)
        )
    """)
    
    # 5. Approvals Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY,
            action_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            approved_by TEXT NOT NULL,
            approved_at TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (action_id) REFERENCES actions (id)
        )
    """)
    
    # 6. Audit Events Table (SHA-256 Hash Chained)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            transaction_id TEXT,
            amount REAL,
            metadata TEXT,
            previous_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

def reset_db():
    if os.path.exists(settings.DATABASE_PATH):
        try:
            os.remove(settings.DATABASE_PATH)
        except Exception:
            pass
    init_db()
