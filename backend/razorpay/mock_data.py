import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from backend.database import get_db_connection

def generate_mock_dataset():
    """
    Generates a deterministic, mathematically precise merchant dataset:
    - 127 total transactions
    - ₹18.4L total attempted revenue (18,40,000.0)
    - ₹16.03L successful revenue (16,03,000.0)
    - ₹2.37L Revenue at Risk (2,37,000.0)
    - ₹1.75L Eligible for Recovery (1,75,000.0)
    - ₹1.42L Expected Recovery (1,42,000.0)
    - 12 High-Value Failures (₹82,000.0)
    - 31 Pending / Abandoned Orders (₹41,000.0)
    - 7 Repeat Failed Customers (₹29,000.0)
    - 17 Standard Failed Orders (₹85,000.0)
    - 60 Successful Orders (₹16,03,000.0)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM transactions")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    random.seed(42)

    customers_data = [
        ("cust_101", "Aarav Sharma", "aarav.sharma@example.com", "+919876543210", 8, 7, 1, 145000.0),
        ("cust_102", "Priya Patel", "priya.patel@example.com", "+919876543211", 5, 4, 1, 85000.0),
        ("cust_103", "Rohan Mehta", "rohan.mehta@example.com", "+919876543212", 6, 4, 2, 92000.0),
        ("cust_104", "Ananya Iyer", "ananya.iyer@example.com", "+919876543213", 12, 10, 2, 210000.0),
        ("cust_105", "Vikram Singh", "vikram.singh@example.com", "+919876543214", 4, 2, 2, 45000.0),
        ("cust_106", "Sneha Reddy", "sneha.reddy@example.com", "+919876543215", 9, 7, 2, 160000.0),
        ("cust_107", "Kabir Joshi", "kabir.joshi@example.com", "+919876543216", 3, 1, 2, 35000.0),
        ("cust_108", "Neha Gupta", "neha.gupta@example.com", "+919876543217", 7, 6, 1, 115000.0),
        ("cust_109", "Rahul Verma", "rahul.verma@example.com", "+919876543218", 10, 9, 1, 190000.0),
        ("cust_110", "Aditi Rao", "aditi.rao@example.com", "+919876543219", 4, 3, 1, 62000.0),
        ("cust_111", "Karan Malhotra", "karan.m@example.com", "+919876543220", 2, 0, 2, 0.0),
        ("cust_112", "Divya Nair", "divya.nair@example.com", "+919876543221", 5, 4, 1, 78000.0),
        ("cust_113", "Arjun Kapoor", "arjun.k@example.com", "+919876543222", 6, 5, 1, 95000.0),
        ("cust_114", "Meera Desai", "meera.d@example.com", "+919876543223", 4, 3, 1, 54000.0),
        ("cust_115", "Siddharth Jain", "sid.jain@example.com", "+919876543224", 8, 7, 1, 130000.0),
    ]

    for cust in customers_data:
        cursor.execute("""
            INSERT INTO customers (id, name, email, phone, total_orders, successful_orders, failed_orders, lifetime_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (*cust, (datetime.now() - timedelta(days=random.randint(10, 60))).isoformat()))

    # 1. High-Value Failed Transactions (12 orders totaling exactly ₹82,000.0)
    high_value_failures = [
        ("pay_hv_01", "order_hv_01", "cust_101", 18500.0, "failed", "BAD_REQUEST_ERROR", "Payment processing failed at issuing bank"),
        ("pay_hv_02", "order_hv_02", "cust_104", 14200.0, "failed", "GATEWAY_ERROR", "Payment gateway timed out during authentication"),
        ("pay_hv_03", "order_hv_03", "cust_106", 9800.0, "failed", "CARD_EXPIRED", "Card expired during checkout verification"),
        ("pay_hv_04", "order_hv_04", "cust_109", 8500.0, "failed", "INSUFFICIENT_FUNDS", "Insufficient balance on customer payment method"),
        ("pay_hv_05", "order_hv_05", "cust_108", 6800.0, "failed", "NETWORK_ERROR", "Network failure between merchant and acquiring bank"),
        ("pay_hv_06", "order_hv_06", "cust_115", 5500.0, "failed", "BAD_REQUEST_ERROR", "3DS verification timeout on customer device"),
        ("pay_hv_07", "order_hv_07", "cust_102", 4600.0, "failed", "GATEWAY_ERROR", "Issuer declined high value transaction limit"),
        ("pay_hv_08", "order_hv_08", "cust_103", 4200.0, "failed", "BAD_REQUEST_ERROR", "OTP validation expired after 3 retries"),
        ("pay_hv_09", "order_hv_09", "cust_112", 3600.0, "failed", "PAYMENT_CANCELLED", "User closed authorization modal"),
        ("pay_hv_10", "order_hv_10", "cust_113", 2800.0, "failed", "BAD_REQUEST_ERROR", "Invalid card CVV verification code"),
        ("pay_hv_11", "order_hv_11", "cust_114", 2100.0, "failed", "GATEWAY_ERROR", "Banking gateway temporary service downtime"),
        ("pay_hv_12", "order_hv_12", "cust_110", 1400.0, "failed", "NETWORK_ERROR", "Connection reset by peer during checkout"),
    ]

    # 2. Repeat Customer Failed Transactions (7 repeat orders totaling exactly ₹29,000.0)
    repeat_failures = [
        ("pay_rep_01", "order_rep_01", "cust_103", 6500.0, "failed", "GATEWAY_ERROR", "Second consecutive failure for loyal customer"),
        ("pay_rep_02", "order_rep_02", "cust_105", 5200.0, "failed", "BAD_REQUEST_ERROR", "Multiple checkout attempts failed"),
        ("pay_rep_03", "order_rep_03", "cust_107", 4800.0, "failed", "INSUFFICIENT_FUNDS", "Payment retried twice without success"),
        ("pay_rep_04", "order_rep_04", "cust_111", 4500.0, "failed", "BAD_REQUEST_ERROR", "Customer attempted 3 retries in 1 hour"),
        ("pay_rep_05", "order_rep_05", "cust_105", 3500.0, "failed", "NETWORK_ERROR", "Repeated timeout during UPI collect request"),
        ("pay_rep_06", "order_rep_06", "cust_107", 2500.0, "failed", "PAYMENT_CANCELLED", "Aborted retry flow on mobile"),
        ("pay_rep_07", "order_rep_07", "cust_111", 2000.0, "failed", "GATEWAY_ERROR", "Bank switch decline on repeat attempt"),
    ]

    # 3. Pending / Abandoned Orders (31 orders totaling exactly ₹41,000.0)
    # Sum: 3200+2800+2500+2400+2100+1900+1800+1700+1600+1500+1400+1300+1300+1200+1200+1100+1100+1000+1000+950+900+850+800+750+700+650+600+550+500+450+200 = 41000.0
    pending_amounts = [
        3200.0, 2800.0, 2500.0, 2400.0, 2100.0, 1900.0, 1800.0, 1700.0, 1600.0, 1500.0,
        1400.0, 1300.0, 1300.0, 1200.0, 1200.0, 1100.0, 1100.0, 1000.0, 1000.0, 950.0,
        900.0, 850.0, 800.0, 750.0, 700.0, 650.0, 600.0, 550.0, 500.0, 450.0, 200.0
    ]
    pending_orders = []
    for i, amt in enumerate(pending_amounts):
        cust_id = f"cust_{101 + (i % 15)}"
        p_id = f"pay_pend_{i+1:02d}"
        o_id = f"order_pend_{i+1:02d}"
        pending_orders.append((p_id, o_id, cust_id, amt, "pending", None, "Order created in checkout; payment authorization pending"))

    # 4. Standard Failures (17 orders totaling exactly ₹85,000.0)
    std_amounts = [
        12000.0, 10000.0, 9000.0, 8000.0, 7500.0, 6500.0, 5500.0, 4500.0, 4000.0, 3800.0,
        3500.0, 3000.0, 2500.0, 2200.0, 1800.0, 1200.0, 1000.0
    ]  # Sum = 85000.0
    standard_failures = []
    for i, amt in enumerate(std_amounts):
        cust_id = f"cust_{101 + ((i+3) % 15)}"
        p_id = f"pay_std_{i+1:02d}"
        o_id = f"order_std_{i+1:02d}"
        standard_failures.append((p_id, o_id, cust_id, amt, "failed", "GATEWAY_ERROR", "Card authorization declined by issuer"))

    # 5. Successful Orders (60 orders totaling exactly ₹16,03,000.0)
    successful_orders = []
    for i in range(60):
        cust_id = f"cust_{101 + (i % 15)}"
        p_id = f"pay_succ_{i+1:02d}"
        o_id = f"order_succ_{i+1:02d}"
        amt = round(random.uniform(8000.0, 45000.0), 2)
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

    all_txs = high_value_failures + repeat_failures + pending_orders + standard_failures + successful_orders
    
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
