#!/usr/bin/env python3
"""
Complete Database operations for Subscription Analytics MCP Server
Enhanced version with connection pooling and true non-blocking async operations.
"""

import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import mysql.connector
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages all database operations for subscription analytics.

    This version is enhanced with:
    1.  Connection Pooling: Reuses database connections for improved performance.
    2.  True Async Operations: Uses `asyncio.to_thread` to run blocking database
        calls in a separate thread, preventing the main event loop from stalling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.db_config = {
            'host': config['db_host'],
            'port': config['db_port'],
            'database': config['db_name'],
            'user': config['db_user'],
            'password': config['db_password'],
            'autocommit': True,
            'connect_timeout': 30,
            'raise_on_warnings': False
        }
        
        # Cache for table existence and column checks
        self.table_cache = {}
        self.column_cache = {}
        
        # Initialize the connection pool
        try:
            pool_config = {**self.db_config, 'pool_name': 'mcp_pool', 'pool_size': 5}
            self.pool = MySQLConnectionPool(**pool_config)
            logger.info(f"✅ Database connection pool initialized for {self.db_config['host']}:{self.db_config['port']}")
        except Error as e:
            logger.error(f"❌ Failed to create database connection pool: {e}")
            raise

    def get_connection(self):
        """Get a connection from the pool."""
        try:
            return self.pool.get_connection()
        except Error as e:
            logger.error(f"❌ Could not get connection from pool: {e}")
            return None

    def validate_date_format(self, date_string: str, date_name: str) -> datetime.date:
        """Validate and parse date string. This is a synchronous helper."""
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except ValueError as e:
            raise ValueError(f"Invalid {date_name} format. Use YYYY-MM-DD. Error: {str(e)}")

    def find_column(self, columns: List[str], possible_names: List[str]) -> Optional[str]:
        """Find a column from a list of possible names. This is a synchronous helper."""
        for possible_name in possible_names:
            if possible_name in columns:
                return possible_name
        return None

    # --- Internal Synchronous Methods (Core Logic) ---
    # These methods contain the actual blocking database logic.

    def _check_table_exists_sync(self, table_name: str) -> bool:
        if table_name in self.table_cache:
            return self.table_cache[table_name]
        
        try:
            with self.get_connection() as connection:
                if not connection: return False
                with connection.cursor() as cursor:
                    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                    exists = cursor.fetchone() is not None
                    self.table_cache[table_name] = exists
                    if not exists:
                        logger.warning(f"Table '{table_name}' does not exist.")
                    return exists
        except Error as e:
            logger.error(f"Error checking table '{table_name}': {e}")
            return False

    def _get_table_columns_sync(self, table_name: str) -> List[str]:
        if table_name in self.column_cache:
            return self.column_cache[table_name]
        
        try:
            with self.get_connection() as connection:
                if not connection: return []
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = [col['Field'] for col in cursor.fetchall()]
                    self.column_cache[table_name] = columns
                    return columns
        except Error as e:
            logger.error(f"Error getting columns for '{table_name}': {e}")
            return []
            
    # --- Public Asynchronous Methods (API Wrappers) ---
    # These are the methods called by the rest of the application.

    async def check_table_exists(self, table_name: str) -> bool:
        """Asynchronously check if a table exists in the database."""
        return await asyncio.to_thread(self._check_table_exists_sync, table_name)

    async def get_table_columns(self, table_name: str) -> List[str]:
        """Asynchronously get list of columns in a table."""
        return await asyncio.to_thread(self._get_table_columns_sync, table_name)

    async def get_available_tables(self) -> List[str]:
        """Asynchronously get a list of all available tables."""
        def _sync_logic():
            try:
                with self.get_connection() as connection:
                    if not connection: return []
                    with connection.cursor() as cursor:
                        cursor.execute("SHOW TABLES")
                        return [table[0] for table in cursor.fetchall()]
            except Error as e:
                logger.error(f"Error listing tables: {e}")
                return []
        return await asyncio.to_thread(_sync_logic)

    async def get_subscriptions_in_last_days(self, days: int) -> Dict[str, Any]:
        """Asynchronously get subscription data for the last x days."""
        if not isinstance(days, int) or not (1 <= days <= 365):
            return {"error": "Days must be an integer between 1 and 365"}
        
        if not await self.check_table_exists('subscription_contract_v2'):
            return {"error": "Table 'subscription_contract_v2' not found."}

        return await asyncio.to_thread(self._get_subscriptions_in_last_days_sync, days)
    
    def _get_subscriptions_in_last_days_sync(self, days: int) -> Dict[str, Any]:
        try:
            with self.get_connection() as connection:
                if not connection: return {"error": "Database connection failed"}
                with connection.cursor(dictionary=True) as cursor:
                    today, start_date = datetime.now().date(), datetime.now().date() - timedelta(days=days)
                    columns = self._get_table_columns_sync('subscription_contract_v2')
                    date_column = self.find_column(columns, ['subcription_start_date', 'subscription_start_date', 'start_date', 'created_date', 'created_at'])
                    if not date_column: return {"error": f"No date column found. Available: {columns}"}
                    
                    query = f"""
                        SELECT COUNT(*) as new_subs,
                               SUM(CASE WHEN status IN ('ACTIVE', 'active') THEN 1 ELSE 0 END) as active,
                               SUM(CASE WHEN status IN ('CLOSED', 'REJECT', 'CANCELLED', 'INACTIVE') THEN 1 ELSE 0 END) as cancelled
                        FROM subscription_contract_v2 WHERE {date_column} BETWEEN %s AND %s
                    """
                    cursor.execute(query, (start_date, today))
                    result = cursor.fetchone()
                    if not result: return {"error": "No data returned"}
                    
                    return {"new_subscriptions": result['new_subs'] or 0, "active_subscriptions": result['active'] or 0, "cancelled_subscriptions": result['cancelled'] or 0,
                            "period_days": days, "date_range": {"start": str(start_date), "end": str(today)}, "date_column_used": date_column}
        except Error as e: return {"error": f"DB query failed: {e}"}
        except Exception as e: return {"error": f"Unexpected error: {e}"}

    async def get_payment_success_rate_in_last_days(self, days: int) -> Dict[str, Any]:
        """Asynchronously get payment success rate for the last x days."""
        if not isinstance(days, int) or not (1 <= days <= 365):
            return {"error": "Days must be an integer between 1 and 365"}
        
        if not await self.check_table_exists('subscription_payment_details'):
            return {"error": "Table 'subscription_payment_details' not found."}
            
        return await asyncio.to_thread(self._get_payment_success_rate_in_last_days_sync, days)

    def _get_payment_success_rate_in_last_days_sync(self, days: int) -> Dict[str, Any]:
        try:
            with self.get_connection() as connection:
                if not connection: return {"error": "Database connection failed"}
                with connection.cursor(dictionary=True) as cursor:
                    today, start_date = datetime.now().date(), datetime.now().date() - timedelta(days=days)
                    columns = self._get_table_columns_sync('subscription_payment_details')
                    amount_col = self.find_column(columns, ['trans_amount_decimal', 'amount', 'transaction_amount']) or "0"

                    query = f"""
                        SELECT COUNT(*) as total, SUM(CASE WHEN status IN ('ACTIVE','SUCCESS','active','success') THEN 1 ELSE 0 END) as successful,
                               SUM(CASE WHEN status IN ('ACTIVE','SUCCESS','active','success') THEN {amount_col} ELSE 0 END) as revenue
                        FROM subscription_payment_details WHERE created_date BETWEEN %s AND %s
                    """
                    cursor.execute(query, (start_date, today))
                    res = cursor.fetchone()
                    if not res: return {"error": "No data returned"}

                    total = res['total'] or 0
                    success_rate = (res['successful'] / total * 100) if total > 0 else 0

                    return {"success_rate": f"{success_rate:.2f}%", "total_payments": total, "successful_payments": res['successful'] or 0,
                            "total_revenue": f"${float(res['revenue'] or 0):.2f}", "period_days": days,
                            "date_range": {"start": str(start_date), "end": str(today)}, "amount_column_used": amount_col if amount_col != "0" else "N/A"}
        except Error as e: return {"error": f"DB query failed: {e}"}
        except Exception as e: return {"error": f"Unexpected error: {e}"}

    async def get_subscription_summary(self, days: int = 30) -> Dict[str, Any]:
        """Concurrently get a comprehensive subscription and payment summary."""
        subs_task = self.get_subscriptions_in_last_days(days)
        payment_task = self.get_payment_success_rate_in_last_days(days)
        subscription_data, payment_data = await asyncio.gather(subs_task, payment_task)
        
        if "error" in subscription_data or "error" in payment_data:
            return {"error": "Failed to fetch full summary", "subscription_error": subscription_data.get("error"), "payment_error": payment_data.get("error")}
        
        return {"period_days": days, "subscriptions": subscription_data, "payments": payment_data}

    async def get_database_status(self) -> Dict[str, Any]:
        """Asynchronously check database connection and get basic statistics."""
        return await asyncio.to_thread(self._get_database_status_sync)

    def _get_database_status_sync(self) -> Dict[str, Any]:
        try:
            with self.get_connection() as connection:
                if not connection: return {"status": "disconnected", "error": "Cannot connect to database"}
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute("SELECT 1 as test")
                    if not cursor.fetchone(): return {"status": "error", "error": "Test query failed"}

                    status = {"status": "connected", "database": self.db_config['database']}
                    if self._check_table_exists_sync('subscription_contract_v2'):
                        cursor.execute("SELECT COUNT(*) as c FROM subscription_contract_v2")
                        status['total_subscriptions'] = cursor.fetchone()['c']
                    if self._check_table_exists_sync('subscription_payment_details'):
                        cursor.execute("SELECT COUNT(*) as c FROM subscription_payment_details")
                        status['total_payments'] = cursor.fetchone()['c']
                    return status
        except Error as e: return {"status": "error", "error": f"DB check failed: {e}"}

    async def get_user_payment_history(self, merchant_user_id: str, days: int = 90) -> Dict[str, Any]:
        """Asynchronously get payment history for a specific user."""
        if not all([await self.check_table_exists('subscription_contract_v2'), await self.check_table_exists('subscription_payment_details')]):
            return {"error": "Required tables not found."}
            
        return await asyncio.to_thread(self._get_user_payment_history_sync, merchant_user_id, days)

    def _get_user_payment_history_sync(self, merchant_user_id: str, days: int) -> Dict[str, Any]:
        try:
            with self.get_connection() as connection:
                if not connection: return {"error": "Database connection failed"}
                with connection.cursor(dictionary=True) as cursor:
                    today, start_date = datetime.now().date(), datetime.now().date() - timedelta(days=days)
                    payment_cols = self._get_table_columns_sync('subscription_payment_details')
                    amount_col = self.find_column(payment_cols, ['trans_amount_decimal', 'amount']) or "0"
                    
                    query = f"""
                        SELECT spd.created_date, spd.{amount_col} as amount, spd.status
                        FROM subscription_payment_details as spd
                        JOIN subscription_contract_v2 as scv ON spd.subscription_id = scv.subscription_id
                        WHERE scv.merchant_user_id = %s AND spd.created_date BETWEEN %s AND %s
                        ORDER BY spd.created_date DESC
                    """
                    cursor.execute(query, (merchant_user_id, start_date, today))
                    payments = cursor.fetchall()
                    if not payments: return {"message": f"No payments found for user {merchant_user_id}"}

                    successful = sum(1 for p in payments if p['status'] in ['ACTIVE','SUCCESS','active','success'])
                    return {"merchant_user_id": merchant_user_id, "total_payments": len(payments), "successful_payments": successful,
                            "payments": [{"date": str(p['created_date']), "amount": f"${float(p['amount'] or 0):.2f}", "status": p['status']} for p in payments]}
        except Error as e: return {"error": f"DB query failed: {e}"}


    async def get_analytics_by_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Concurrently get comprehensive analytics for a specific date range."""
        try:
            start_dt, end_dt = self.validate_date_format(start_date, "start_date"), self.validate_date_format(end_date, "end_date")
            if start_dt > end_dt: return {"error": "Start date cannot be after end date"}

            subs_task = self.get_subscriptions_by_date_range(start_date, end_date)
            payment_task = self.get_payments_by_date_range(start_date, end_date)
            subscription_data, payment_data = await asyncio.gather(subs_task, payment_task)
            
            if "error" in subscription_data or "error" in payment_data:
                return {"error": "Failed to fetch range data", "sub_error": subscription_data.get("error"), "pay_error": payment_data.get("error")}
            return {"start_date": start_date, "end_date": end_date, "subscriptions": subscription_data, "payments": payment_data}
        except ValueError as e: return {"error": str(e)}

    # The two helper methods for the above function
    async def get_subscriptions_by_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Asynchronously get subscription data for a specific date range."""
        # This method is very similar to get_subscriptions_in_last_days, could be refactored
        # For now, we implement it directly following the async pattern
        if not await self.check_table_exists('subscription_contract_v2'):
            return {"error": "Table 'subscription_contract_v2' not found."}
        return await asyncio.to_thread(self._get_subscriptions_by_date_range_sync, start_date, end_date)

    def _get_subscriptions_by_date_range_sync(self, start_date_str: str, end_date_str: str) -> Dict[str, Any]:
        try:
            with self.get_connection() as connection:
                if not connection: return {"error": "Database connection failed"}
                with connection.cursor(dictionary=True) as cursor:
                    columns = self._get_table_columns_sync('subscription_contract_v2')
                    date_column = self.find_column(columns, ['subcription_start_date', 'subscription_start_date', 'start_date', 'created_date', 'created_at'])
                    if not date_column: return {"error": f"No date column found. Available: {columns}"}
                    
                    query = f"SELECT COUNT(*) as new_subs FROM subscription_contract_v2 WHERE {date_column} BETWEEN %s AND %s"
                    cursor.execute(query, (start_date_str, end_date_str))
                    result = cursor.fetchone()
                    return {"new_subscriptions": result['new_subs'] or 0} if result else {"error": "No data"}
        except Error as e: return {"error": f"DB query failed: {e}"}

    async def get_payments_by_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Asynchronously get payment data for a specific date range."""
        if not await self.check_table_exists('subscription_payment_details'):
            return {"error": "Table 'subscription_payment_details' not found."}
        return await asyncio.to_thread(self._get_payments_by_date_range_sync, start_date, end_date)

    def _get_payments_by_date_range_sync(self, start_date_str: str, end_date_str: str) -> Dict[str, Any]:
        try:
             with self.get_connection() as connection:
                if not connection: return {"error": "Database connection failed"}
                with connection.cursor(dictionary=True) as cursor:
                    # Logic is identical to the _in_last_days sync method, just with different date params
                    # This could also be a refactoring opportunity to a single private method
                    columns = self._get_table_columns_sync('subscription_payment_details')
                    amount_col = self.find_column(columns, ['trans_amount_decimal', 'amount']) or "0"
                    query = f"""
                        SELECT COUNT(*) as total, SUM(CASE WHEN status IN ('ACTIVE','SUCCESS','active','success') THEN 1 ELSE 0 END) as successful,
                               SUM(CASE WHEN status IN ('ACTIVE','SUCCESS','active','success') THEN {amount_col} ELSE 0 END) as revenue
                        FROM subscription_payment_details WHERE created_date BETWEEN %s AND %s
                    """
                    cursor.execute(query, (start_date_str, end_date_str))
                    res = cursor.fetchone()
                    if not res: return {"error": "No data returned"}

                    total = res['total'] or 0
                    success_rate = (res['successful'] / total * 100) if total > 0 else 0
                    return {"success_rate": f"{success_rate:.2f}%", "total_payments": total, "successful_payments": res['successful'] or 0,
                            "total_revenue": f"${float(res['revenue'] or 0):.2f}"}
        except Error as e: return {"error": f"DB query failed: {e}"}

# Test the database manager
async def test_database_manager():
    """Test the database manager functionality"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    config = {
        'db_host': os.getenv('DB_HOST', 'localhost'),
        'db_port': int(os.getenv('DB_PORT', '3306')),
        'db_name': os.getenv('DB_NAME', 'test'),
        'db_user': os.getenv('DB_USER', 'root'),
        'db_password': os.getenv('DB_PASSWORD', '')
    }
    
    print("🧪 Testing Complete Database Manager")
    print("=" * 50)
    
    try:
        db_manager = DatabaseManager(config)
    except Exception as e:
        print(f"❌ Failed to initialize DatabaseManager: {e}")
        return

    # Test database status
    print("1. Testing database status...")
    status = await db_manager.get_database_status()
    print(f"   Status: {status.get('status', 'unknown')}")
    
    if 'all_tables' in status:
        print(f"   Available tables: {status['all_tables']}")
    
    if status.get('status') == 'connected':
        print("   ✅ Database connection successful!")
        
        # Test table checks
        print("\n2. Testing table existence...")
        subscription_exists = await db_manager.check_table_exists('subscription_contract_v2')
        payment_exists = await db_manager.check_table_exists('subscription_payment_details')
        
        print(f"   Subscription table exists: {subscription_exists}")
        print(f"   Payment table exists: {payment_exists}")
        
        # Test subscription query
        print("\n3. Testing subscription query...")
        subs = await db_manager.get_subscriptions_in_last_days(7)
        if 'error' in subs:
            print(f"   ❌ Error: {subs['error']}")
        else:
            print(f"   ✅ Found {subs.get('new_subscriptions')} new subscriptions in last 7 days")
        
        # Test payment query
        print("\n4. Testing payment query...")
        payments = await db_manager.get_payment_success_rate_in_last_days(7)
        if 'error' in payments:
            print(f"   ❌ Error: {payments['error']}")
        else:
            print(f"   ✅ Found {payments.get('total_payments')} payments in last 7 days")
        
        # Test summary
        print("\n5. Testing subscription summary...")
        summary = await db_manager.get_subscription_summary(30)
        if 'error' in summary:
            print(f"   ❌ Error: {summary['error']}")
        else:
            print(f"   ✅ Summary fetched for {summary.get('period_days')} days.")
        
    else:
        print("   ❌ Database connection failed")
        if 'error' in status:
            print(f"   Error: {status['error']}")
    
    print("\n" + "=" * 50)
    print("Database testing complete!")

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_database_manager())