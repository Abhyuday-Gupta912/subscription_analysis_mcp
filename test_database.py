#!/usr/bin/env python3
"""
Test script for the corrected database.py
"""

import asyncio
import os
from dotenv import load_dotenv
from database import DatabaseManager

async def test_database():
    """Test all database functions"""
    
    load_dotenv()
    
    # Configuration matching your .env
    config = {
        'db_host': os.getenv('DB_HOST'),
        'db_port': int(os.getenv('DB_PORT', '3306')),
        'db_name': os.getenv('DB_NAME'),
        'db_user': os.getenv('DB_USER'),
        'db_password': os.getenv('DB_PASSWORD')
    }
    
    print("🧪 Testing Enhanced Database Manager")
    print("=" * 50)
    
    # Initialize database manager
    db = DatabaseManager(config)
    
    # Test 1: Database Status
    print("\n1. Testing database status...")
    status = await db.get_database_status()
    print(f"Status: {status.get('status', 'unknown')}")
    
    if 'all_tables' in status:
        print(f"Available tables: {status['all_tables']}")
    
    if 'error' in status:
        print(f"❌ Error: {status['error']}")
        return False
    
    # Test 2: Table existence
    print("\n2. Testing table checks...")
    subscription_exists = await db.check_table_exists('subscription_contract_v2')
    payment_exists = await db.check_table_exists('subscription_payment_details')
    
    print(f"Subscription table exists: {subscription_exists}")
    print(f"Payment table exists: {payment_exists}")
    
    # Test 3: Subscription query
    print("\n3. Testing subscription query...")
    try:
        subs = await db.get_subscriptions_in_last_days(7)
        if 'error' in subs:
            print(f"❌ Subscription query error: {subs['error']}")
            if 'available_tables' in subs:
                print(f"Available tables: {subs['available_tables']}")
        else:
            print(f"✅ Found {subs['new_subscriptions']} new subscriptions in last 7 days")
            if 'date_column_used' in subs:
                print(f"Used date column: {subs['date_column_used']}")
    except Exception as e:
        print(f"❌ Subscription test failed: {e}")
    
    # Test 4: Payment query
    print("\n4. Testing payment query...")
    try:
        payments = await db.get_payment_success_rate_in_last_days(7)
        if 'error' in payments:
            print(f"❌ Payment query error: {payments['error']}")
            if 'available_tables' in payments:
                print(f"Available tables: {payments['available_tables']}")
        else:
            print(f"✅ Found {payments['total_payments']} payments in last 7 days")
            print(f"Success rate: {payments['success_rate']}")
            if 'amount_column_used' in payments:
                print(f"Used amount column: {payments['amount_column_used']}")
    except Exception as e:
        print(f"❌ Payment test failed: {e}")
    
    # Test 5: Summary
    print("\n5. Testing summary...")
    try:
        summary = await db.get_subscription_summary(30)
        if 'error' in summary:
            print(f"❌ Summary error: {summary['error']}")
        else:
            print(f"✅ Summary: {summary['summary']}")
    except Exception as e:
        print(f"❌ Summary test failed: {e}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_database())