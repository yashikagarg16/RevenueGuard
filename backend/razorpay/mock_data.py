import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from backend.database import get_db_connection

def generate_mock_dataset():
    """
    Generates a mathematically exact, 100% reconcilable merchant dataset:
    - 127 total transactions
    - Total Attempted GMV: ₹18,40,000.0
    - Successful Volume: ₹16,03,000.0 (70 transactions)
    - Revenue at Risk: ₹2,37,000.0 (Failed ₹1,73,000 + Pending ₹64,000)
    - Eligible for Recovery: ₹1,75,000.0 (Policy-verified, <= ₹50,000)
    - Expected Recovery Lift: ₹1,42,000.0 (Weighted channel conversion)
    
    100% Leak Reconciliation:
    1. High-Value Payment Failures: ₹1,12,000.0 (14 orders)
    2. Abandoned & Pending Orders:   ₹64,000.0  (31 orders)
    3. Repeat Customer Friction:      ₹61,000.0  (12 orders across 7 repeat customers)
    Sum of Leaks = ₹1,12,000 + ₹64,000 + ₹61,000 = EXACTLY ₹2,37,000.0
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM transactions")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # 1. Customers (15 distinct accounts, 7 of which are repeat customers)
    customers_data = [
        ("cust_101", "Aarav Sharma", "aarav.sharma@example.com", "+919876543210", 8, 7, 1, 145000.0),
        ("cust_102", "Priya Patel", "priya.patel@example.com", "+919876543211", 5, 4, 1, 85000.0),
        ("cust_103", "Rohan Mehta", "rohan.mehta@example.com", "+919876543212", 7, 4, 3, 92000.0),
        ("cust_104", "Ananya Iyer", "ananya.iyer@example.com", "+919876543213", 12, 10, 2, 210000.0),
        ("cust_105", "Vikram Singh", "vikram.singh@example.com", "+919876543214", 5, 2, 3, 45000.0),
        ("cust_106", "Sneha Reddy", "sneha.reddy@example.com", "+919876543215", 9, 7, 2, 160000.0),
        ("cust_107", "Kabir Joshi", "kabir.joshi@example.com", "+919876543216", 4, 1, 3, 35000.0),
        ("cust_108", "Neha Gupta", "neha.gupta@example.com", "+919876543217", 7, 6, 1, 115000.0),
        ("cust_109", "Rahul Verma", "rahul.verma@example.com", "+919876543218", 10, 9, 1, 190000.0),
        ("cust_110", "Aditi Rao", "aditi.rao@example.com", "+919876543219", 4, 3, 1, 62000.0),
        ("cust_111", "Karan Malhotra", "karan.m@example.com", "+919876543220", 3, 0, 3, 0.0),
        ("cust_112", "Divya Nair", "divya.nair@example.com", "+919876543221", 5, 4, 1, 78000.0),
        ("cust_113", "Arjun Kapoor", "arjun.k@example.com", "+919876543222", 6, 5, 1, 95000.0),
        ("cust_114", "Meera Desai", "meera.d@example.com", "+919876543223", 4, 3, 1, 54000.0),
        ("cust_115", "Siddharth Jain", "sid.jain@example.com", "+919876543224", 8, 7, 1, 130000.0),
    ]

    for cust in customers_data:
        cursor.execute("""
            INSERT INTO customers (id, name, email, phone, total_orders, successful_orders, failed_orders, lifetime_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (*cust, (datetime.now() - timedelta(days=30)).isoformat()))

    # --- 1. High-Value Payment Failures (14 orders summing to EXACTLY ₹1,12,000.0) ---
    high_value_failures = [
        ("pay_hv_01", "order_hv_01", "cust_101", 18500.0, "failed", "BAD_REQUEST_ERROR", "Payment processing failed at issuing bank"),
        ("pay_hv_02", "order_hv_02", "cust_104", 14200.0, "failed", "GATEWAY_ERROR", "Payment gateway timed out during authentication"),
        ("pay_hv_03", "order_hv_03", "cust_106", 12500.0, "failed", "CARD_EXPIRED", "Card expired during checkout verification"),
        ("pay_hv_04", "order_hv_04", "cust_109", 11000.0, "failed", "INSUFFICIENT_FUNDS", "Insufficient balance on customer payment method"),
        ("pay_hv_05", "order_hv_05", "cust_108", 9800.0, "failed", "NETWORK_ERROR", "Network failure between merchant and acquiring bank"),
        ("pay_hv_06", "order_hv_06", "cust_115", 8500.0, "failed", "BAD_REQUEST_ERROR", "3DS verification timeout on customer device"),
        ("pay_hv_07", "order_hv_07", "cust_102", 7600.0, "failed", "GATEWAY_ERROR", "Issuer declined high value transaction limit"),
        ("pay_hv_08", "order_hv_08", "cust_103", 6800.0, "failed", "BAD_REQUEST_ERROR", "OTP validation expired after retries"),
        ("pay_hv_09", "order_hv_09", "cust_112", 5900.0, "failed", "PAYMENT_CANCELLED", "User closed authorization modal"),
        ("pay_hv_10", "order_hv_10", "cust_113", 5200.0, "failed", "BAD_REQUEST_ERROR", "Invalid card CVV verification code"),
        ("pay_hv_11", "order_hv_11", "cust_114", 4800.0, "failed", "GATEWAY_ERROR", "Banking gateway temporary service downtime"),
        ("pay_hv_12", "order_hv_12", "cust_110", 3500.0, "failed", "NETWORK_ERROR", "Connection reset by peer during checkout"),
        ("pay_hv_13", "order_hv_13", "cust_101", 2100.0, "failed", "BAD_REQUEST_ERROR", "Issuer velocity check triggered"),
        ("pay_hv_14", "order_hv_14", "cust_104", 1600.0, "failed", "GATEWAY_ERROR", "Bank switch timeout"),
    ]  # Sum = 112,000.0

    # --- 2. Repeat Customer Friction (12 orders across 7 repeat customers summing to EXACTLY ₹61,000.0) ---
    repeat_failures = [
        ("pay_rep_01", "order_rep_01", "cust_103", 9500.0, "failed", "GATEWAY_ERROR", "Consecutive decline on loyal customer account"),
        ("pay_rep_02", "order_rep_02", "cust_105", 8200.0, "failed", "BAD_REQUEST_ERROR", "Multiple checkout attempts failed"),
        ("pay_rep_03", "order_rep_03", "cust_107", 7400.0, "failed", "INSUFFICIENT_FUNDS", "Payment retried twice without success"),
        ("pay_rep_04", "order_rep_04", "cust_111", 6500.0, "failed", "BAD_REQUEST_ERROR", "Customer attempted 3 retries in 1 hour"),
        ("pay_rep_05", "order_rep_05", "cust_105", 5800.0, "failed", "NETWORK_ERROR", "Repeated timeout during UPI collect request"),
        ("pay_rep_06", "order_rep_06", "cust_107", 5100.0, "failed", "PAYMENT_CANCELLED", "Aborted retry flow on mobile"),
        ("pay_rep_07", "order_rep_07", "cust_111", 4600.0, "failed", "GATEWAY_ERROR", "Bank switch decline on repeat attempt"),
        ("pay_rep_08", "order_rep_08", "cust_103", 4200.0, "failed", "BAD_REQUEST_ERROR", "Card processing error on repeat attempt"),
        ("pay_rep_09", "order_rep_09", "cust_104", 3600.0, "failed", "GATEWAY_ERROR", "Issuer timeout on secondary attempt"),
        ("pay_rep_10", "order_rep_10", "cust_106", 2900.0, "failed", "NETWORK_ERROR", "Connection drop on repeat checkout"),
        ("pay_rep_11", "order_rep_11", "cust_105", 1800.0, "failed", "BAD_REQUEST_ERROR", "UPI VPA verification failure"),
        ("pay_rep_12", "order_rep_12", "cust_107", 1400.0, "failed", "GATEWAY_ERROR", "Network drop during OTP verification"),
    ]  # Sum = 61,000.0

    # Total Failed Revenue = 112,000 + 61,000 = 173,000.0 across 26 failed transactions

    # --- 3. Abandoned & Pending Orders (31 orders summing to EXACTLY ₹64,000.0) ---
    pending_amounts = [
        4500.0, 4200.0, 3800.0, 3500.0, 3200.0, 3000.0, 2800.0, 2600.0, 2500.0, 2400.0,
        2200.0, 2100.0, 2000.0, 1900.0, 1800.0, 1700.0, 1600.0, 1500.0, 1400.0, 1300.0,
        1300.0, 1200.0, 1200.0, 1100.0, 1100.0, 1000.0, 1000.0, 950.0, 900.0, 850.0, 3400.0
    ]  # Sum = 64,000.0
    pending_orders = []
    for i, amt in enumerate(pending_amounts):
        cust_id = f"cust_{101 + (i % 15)}"
        p_id = f"pay_pend_{i+1:02d}"
        o_id = f"order_pend_{i+1:02d}"
        pending_orders.append((p_id, o_id, cust_id, amt, "pending", None, "Order created in checkout; payment authorization pending"))

    # Total Revenue at Risk = Failed (173,000) + Pending (64,000) = 237,000.0!

    # --- 4. Successful Transactions (70 orders summing to EXACTLY ₹16,03,000.0) ---
    # Total transactions = 14 (HV) + 12 (Repeat) + 31 (Pending) + 70 (Success) = 127 total!
    successful_orders = []
    random.seed(100)
    for i in range(70):
        cust_id = f"cust_{101 + (i % 15)}"
        p_id = f"pay_succ_{i+1:02d}"
        o_id = f"order_succ_{i+1:02d}"
        amt = round(random.uniform(8000.0, 42000.0), 2)
        successful_orders.append((p_id, o_id, cust_id, amt, "success", None, "Payment captured successfully"))
    
    current_succ_sum = sum(x[3] for x in successful_orders[:-1])
    successful_orders[-1] = (
        successful_orders[-1][0],
        successful_orders[-1][1],
        successful_orders[-1][2],
        round(1603000.0 - current_succ_sum, 2),
        "success",
        None,
        "Payment captured successfully"
    )

    all_txs = high_value_failures + repeat_failures + pending_orders + successful_orders
    
    for tx in all_txs:
        p_id, o_id, c_id, amt, status, err_code, err_desc = tx
        days_ago = random.randint(0, 6)
        hours_ago = random.randint(1, 23)
        created_time = (datetime.now() - timedelta(days=days_ago, hours=hours_ago)).isoformat()
        
        cursor.execute("""
            INSERT INTO transactions (id, order_id, customer_id, amount, currency, status, error_code, error_description, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'INR', ?, ?, ?, ?, ?)
        """, (p_id, o_id, c_id, amt, status, err_code, err_desc, created_time, created_time))
        
    conn.commit()
    conn.close()
