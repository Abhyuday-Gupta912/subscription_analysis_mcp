#!/usr/bin/env python3
"""
Result formatters for Analytics Client
Handles different output formats and styling
"""

import json
from typing import Any, Dict, List, Union
from datetime import datetime

class ResultFormatter:
    """Handles formatting of analytics results"""
    
    def __init__(self, format_type: str = "formatted"):
        self.format_type = format_type  # formatted, json, compact
    
    def format_result(self, result: Any, query: str = "") -> str:
        """Format result based on configured format type"""
        if self.format_type == "json":
            return self._format_json(result)
        elif self.format_type == "compact":
            return self._format_compact(result, query)
        else:
            return self._format_detailed(result, query)
    
    def _format_json(self, result: Any) -> str:
        """Format as JSON"""
        if isinstance(result, str):
            # Try to parse if it's already formatted
            return json.dumps({"result": result}, indent=2)
        elif isinstance(result, dict):
            return json.dumps(result, indent=2)
        else:
            return json.dumps({"data": result}, indent=2)
    
    def _format_compact(self, result: Any, query: str = "") -> str:
        """Format in compact mode"""
        if isinstance(result, str):
            # Remove emoji and extra formatting for compact mode
            clean_result = result
            # Remove common formatting
            clean_result = clean_result.replace("**", "")
            clean_result = clean_result.replace("📊", "")
            clean_result = clean_result.replace("📈", "")
            clean_result = clean_result.replace("💳", "")
            clean_result = clean_result.replace("🗄️", "")
            clean_result = clean_result.replace("✅", "")
            clean_result = clean_result.replace("❌", "")
            
            # Compress multiple newlines
            lines = [line.strip() for line in clean_result.split('\n') if line.strip()]
            return ' | '.join(lines)
        
        return str(result)
    
    def _format_detailed(self, result: Any, query: str = "") -> str:
        """Format in detailed mode with nice styling"""
        if isinstance(result, str):
            # Already formatted string
            formatted = result
            
            # Add query context if provided
            if query:
                formatted = f"🎯 **Query**: {query}\n\n{formatted}"
            
            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted += f"\n\n⏰ *Generated at {timestamp}*"
            
            return formatted
        
        elif isinstance(result, dict):
            return self._format_dict_detailed(result, query)
        
        else:
            return str(result)
    
    def _format_dict_detailed(self, data: Dict[str, Any], query: str = "") -> str:
        """Format dictionary data in detailed mode"""
        if "error" in data:
            return f"❌ **Error**: {data['error']}"
        
        # Try to detect data type and format accordingly
        if self._is_database_status(data):
            return self._format_database_status(data)
        elif self._is_subscription_data(data):
            return self._format_subscription_data(data)
        elif self._is_payment_data(data):
            return self._format_payment_data(data)
        else:
            return self._format_generic_data(data, query)
    
    def _is_database_status(self, data: Dict[str, Any]) -> bool:
        """Check if data is database status"""
        return 'status' in data and 'total_subscriptions' in data
    
    def _is_subscription_data(self, data: Dict[str, Any]) -> bool:
        """Check if data is subscription metrics"""
        return 'new_subscriptions' in data or 'active_subscriptions' in data
    
    def _is_payment_data(self, data: Dict[str, Any]) -> bool:
        """Check if data is payment metrics"""
        return 'total_payments' in data or 'success_rate' in data
    
    def _format_database_status(self, data: Dict[str, Any]) -> str:
        """Format database status data"""
        result = "🗄️ **DATABASE STATUS**\n"
        result += f"📊 Status: {data.get('status', 'unknown').upper()}\n"
        result += f"🏢 Database: {data.get('database', 'unknown')}\n"
        result += f"🌐 Host: {data.get('host', 'unknown')}\n"
        result += f"👥 Total Users: {data.get('unique_users', 0):,}\n"
        result += f"📝 Total Subscriptions: {data.get('total_subscriptions', 0):,}\n"
        result += f"💳 Total Payments: {data.get('total_payments', 0):,}\n"
        result += f"📈 Overall Success Rate: {data.get('overall_success_rate', '0%')}"
        
        if data.get('latest_subscription'):
            result += f"\n📅 Latest Subscription: {data['latest_subscription']}"
        if data.get('latest_payment'):
            result += f"\n💰 Latest Payment: {data['latest_payment']}"
        
        return result
    
    def _format_subscription_data(self, data: Dict[str, Any]) -> str:
        """Format subscription metrics data"""
        period = data.get('period_days', 'unknown')
        date_range = data.get('date_range', {})
        
        result = f"📈 **SUBSCRIPTION METRICS ({period} days)**\n"
        
        if date_range:
            result += f"📅 Period: {date_range.get('start')} to {date_range.get('end')}\n"
        
        result += f"🆕 New Subscriptions: {data.get('new_subscriptions', 0):,}\n"
        result += f"✅ Currently Active: {data.get('active_subscriptions', 0):,}\n"
        result += f"❌ Cancelled: {data.get('cancelled_subscriptions', 0):,}\n"
        
        # Calculate percentages
        new_subs = data.get('new_subscriptions', 0)
        active = data.get('active_subscriptions', 0)
        cancelled = data.get('cancelled_subscriptions', 0)
        
        if new_subs > 0:
            retention_rate = (active / new_subs) * 100
            churn_rate = (cancelled / new_subs) * 100
            result += f"📊 Retention Rate: {retention_rate:.1f}%\n"
            result += f"📉 Churn Rate: {churn_rate:.1f}%"
        
        return result
    
    def _format_payment_data(self, data: Dict[str, Any]) -> str:
        """Format payment metrics data"""
        period = data.get('period_days', 'unknown')
        date_range = data.get('date_range', {})
        
        result = f"💳 **PAYMENT METRICS ({period} days)**\n"
        
        if date_range:
            result += f"📅 Period: {date_range.get('start')} to {date_range.get('end')}\n"
        
        result += f"📊 Total Payments: {data.get('total_payments', 0):,}\n"
        result += f"✅ Successful: {data.get('successful_payments', 0):,}\n"
        result += f"❌ Failed: {data.get('failed_payments', 0):,}\n"
        result += f"📈 Success Rate: {data.get('success_rate', '0%')}\n"
        result += f"📉 Failure Rate: {data.get('failure_rate', '0%')}\n"
        result += f"💰 Total Revenue: {data.get('total_revenue', '$0.00')}\n"
        result += f"💸 Lost Revenue: {data.get('lost_revenue', '$0.00')}"
        
        # Calculate average transaction
        successful = data.get('successful_payments', 0)
        revenue_str = data.get('total_revenue', '$0.00')
        if successful > 0 and revenue_str.startswith('$'):
            try:
                revenue = float(revenue_str.replace('$', '').replace(',', ''))
                avg_transaction = revenue / successful
                result += f"\n📊 Average Transaction: ${avg_transaction:.2f}"
            except (ValueError, ZeroDivisionError):
                pass
        
        return result
    
    def _format_generic_data(self, data: Dict[str, Any], query: str = "") -> str:
        """Format generic data"""
        result = f"📊 **ANALYTICS RESULT**\n"
        
        if query:
            result += f"🎯 Query: {query}\n\n"
        
        for key, value in data.items():
            if key == 'error':
                continue
            
            formatted_key = key.replace('_', ' ').title()
            
            if isinstance(value, dict):
                result += f"**{formatted_key}**:\n"
                for sub_key, sub_value in value.items():
                    sub_formatted = sub_key.replace('_', ' ').title()
                    result += f"  • {sub_formatted}: {sub_value}\n"
            elif isinstance(value, list):
                result += f"**{formatted_key}** ({len(value)} items):\n"
                for i, item in enumerate(value[:5], 1):  # Show first 5 items
                    result += f"  {i}. {item}\n"
                if len(value) > 5:
                    result += f"  ... and {len(value) - 5} more\n"
            else:
                result += f"• {formatted_key}: {value}\n"
        
        return result.rstrip()

# Utility functions
def format_number(num: Union[int, float]) -> str:
    """Format numbers with commas"""
    if isinstance(num, (int, float)):
        return f"{num:,}"
    return str(num)

def format_percentage(num: Union[int, float], decimals: int = 1) -> str:
    """Format percentage"""
    if isinstance(num, (int, float)):
        return f"{num:.{decimals}f}%"
    return str(num)

def format_currency(amount: Union[int, float]) -> str:
    """Format currency amount"""
    if isinstance(amount, (int, float)):
        return f"${amount:,.2f}"
    return str(amount)

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

# Test the formatter
if __name__ == "__main__":
    # Test data
    test_data = {
        "new_subscriptions": 150,
        "active_subscriptions": 120,
        "cancelled_subscriptions": 30,
        "period_days": 7,
        "date_range": {
            "start": "2024-06-07",
            "end": "2024-06-13"
        }
    }
    
    # Test different formats
    formatter = ResultFormatter("formatted")
    print("=== FORMATTED ===")
    print(formatter.format_result(test_data, "subscription metrics for last 7 days"))
    
    print("\n=== JSON ===")
    formatter = ResultFormatter("json")
    print(formatter.format_result(test_data))
    
    print("\n=== COMPACT ===")
    formatter = ResultFormatter("compact")
    print(formatter.format_result(test_data, "subscription metrics"))