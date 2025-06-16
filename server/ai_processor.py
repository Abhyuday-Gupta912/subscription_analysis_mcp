#!/usr/bin/env python3
"""
Complete AI Processor for Subscription Analytics MCP Server
Enhanced with multi-query support and robust regex parsing
"""
import logging
import re
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultiQueryGeminiProcessor:
    def __init__(self, api_key: str, database_manager: Optional[Any] = None):
        # For now, just use regex parsing (more reliable)
        self.database_manager = database_manager
        self.available_tools = self._get_explicit_tool_definitions()
        logger.info(f"🔍 AI Processor initialized with {len(self.available_tools)} tools (enhanced regex parsing)")

    def _get_explicit_tool_definitions(self) -> List[Dict[str, Any]]:
        """Define available tools"""
        return [
            {
                "name": "get_database_status",
                "description": "Check database connection and statistics",
                "parameters": {"type": "object", "properties": {}, "required": []}
            },
            {
                "name": "get_subscriptions_in_last_days",
                "description": "Get subscription statistics for recent period",
                "parameters": {
                    "type": "object",
                    "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 365}},
                    "required": ["days"]
                }
            },
            {
                "name": "get_payment_success_rate_in_last_days",
                "description": "Get payment statistics for recent period",
                "parameters": {
                    "type": "object",
                    "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 365}},
                    "required": ["days"]
                }
            },
            {
                "name": "get_subscription_summary",
                "description": "Get combined subscription and payment metrics",
                "parameters": {
                    "type": "object",
                    "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 365, "default": 30}},
                    "required": []
                }
            }
        ]

    async def parse_natural_language_query(self, user_query: str) -> List[Dict[str, Any]]:
        """Parse query using enhanced regex patterns with multi-query support"""
        logger.info(f"🔍 Parsing query: '{user_query}'")
        
        query_lower = user_query.lower()
        
        # Check for multi-query indicators
        has_and = ' and ' in query_lower
        has_vs = ' vs ' in query_lower or ' versus ' in query_lower
        has_compare = 'compare' in query_lower
        
        if has_and or has_vs or has_compare:
            logger.info("🔍 Detected multi-query request")
            return self._parse_multi_query(query_lower, user_query)
        else:
            return self._parse_single_query(query_lower)

    def _parse_multi_query(self, query_lower: str, original_query: str) -> List[Dict[str, Any]]:
        """Parse multiple queries separated by 'and', 'vs', or comparison terms"""
        results = []
        
        # Handle comparison queries like "compare 7 days vs 30 days"
        if 'compare' in query_lower:
            logger.info("🔍 Processing comparison query")
            
            # Extract all numbers for comparison
            day_matches = re.findall(r'(\d+)\s*days?', query_lower)
            week_matches = re.findall(r'(\d+)\s*weeks?', query_lower)
            month_matches = re.findall(r'(\d+)\s*months?', query_lower)
            
            periods = []
            for day in day_matches:
                periods.append(int(day))
            for week in week_matches:
                periods.append(int(week) * 7)
            for month in month_matches:
                periods.append(int(month) * 30)
            
            periods = sorted(list(set(periods))) if periods else [7, 30]  # Default comparison
            logger.info(f"🔍 Comparison periods: {periods}")
            
            # Create summary queries for each period
            for period in periods:
                results.append({
                    'tool': 'get_subscription_summary',
                    'parameters': {'days': period}
                })
        
        else:
            # Split on 'and' or 'vs'
            if ' and ' in query_lower:
                parts = query_lower.split(' and ')
            elif ' vs ' in query_lower:
                parts = query_lower.split(' vs ')
            elif ' versus ' in query_lower:
                parts = query_lower.split(' versus ')
            else:
                parts = [query_lower]
            
            logger.info(f"🔍 Split into {len(parts)} parts: {parts}")
            
            for i, part in enumerate(parts):
                part = part.strip()
                logger.info(f"🔍 Processing part {i+1}: '{part}'")
                
                # Parse each part as a single query
                single_result = self._parse_single_query(part)
                if single_result:
                    results.extend(single_result)
        
        logger.info(f"🔧 Multi-query result: {results}")
        return results if results else self._parse_single_query(query_lower)

    def _parse_single_query(self, query_lower: str) -> List[Dict[str, Any]]:
        """Parse a single query with enhanced pattern matching"""
        
        # Check for keywords
        has_database = any(word in query_lower for word in ['database', 'db', 'status', 'health', 'connection'])
        has_payment = any(word in query_lower for word in ['payment', 'pay', 'rate', 'success', 'revenue', 'money'])
        has_subscription = any(word in query_lower for word in ['subscription', 'subs', 'sub', 'performance', 'customer'])
        has_summary = any(word in query_lower for word in ['summary', 'overview', 'metrics', 'stats', 'statistics', 'combined'])
        
        # Extract time periods with multiple patterns
        days = self._extract_time_period(query_lower)
        
        # Determine tool to use with priority
        if has_database:
            tool = 'get_database_status'
            params = {}
            logger.info(f"🔧 Chose database tool")
            
        elif has_payment and not has_summary and not has_subscription:
            # Pure payment query
            tool = 'get_payment_success_rate_in_last_days'
            params = {'days': days}
            logger.info(f"🔧 Chose payment tool with {days} days")
            
        elif has_subscription and not has_summary and not has_payment:
            # Pure subscription query
            tool = 'get_subscriptions_in_last_days'
            params = {'days': days}
            logger.info(f"🔧 Chose subscription tool with {days} days")
            
        else:
            # Default to summary (combined metrics)
            tool = 'get_subscription_summary'
            params = {'days': days}
            logger.info(f"🔧 Chose summary tool with {days} days")
        
        result = [{'tool': tool, 'parameters': params}]
        logger.info(f"🔧 Single query result: {result}")
        return result

    def _extract_time_period(self, query_lower: str) -> int:
        """Extract time period from query with multiple patterns"""
        days = 30  # default
        
        # Pattern 1: "X days"
        day_matches = re.findall(r'(\d+)\s*days?', query_lower)
        if day_matches:
            days = int(day_matches[-1])  # Use last match
            logger.info(f"🔍 Found days pattern: {days}")
            return days
        
        # Pattern 2: "last X days"
        last_days_match = re.search(r'last\s+(\d+)\s*days?', query_lower)
        if last_days_match:
            days = int(last_days_match.group(1))
            logger.info(f"🔍 Found 'last X days': {days}")
            return days
        
        # Pattern 3: "for X days", "for last X days"
        for_match = re.search(r'for\s+(?:last\s+)?(\d+)\s*days?', query_lower)
        if for_match:
            days = int(for_match.group(1))
            logger.info(f"🔍 Found 'for X days': {days}")
            return days
        
        # Pattern 4: "X weeks"
        week_matches = re.findall(r'(\d+)\s*weeks?', query_lower)
        if week_matches:
            days = int(week_matches[-1]) * 7
            logger.info(f"🔍 Found weeks pattern: {days} days")
            return days
        
        # Pattern 5: "X months"
        month_matches = re.findall(r'(\d+)\s*months?', query_lower)
        if month_matches:
            days = int(month_matches[-1]) * 30
            logger.info(f"🔍 Found months pattern: {days} days")
            return days
        
        # Pattern 6: "past X days/weeks/months"
        past_match = re.search(r'past\s+(\d+)\s*(days?|weeks?|months?)', query_lower)
        if past_match:
            num, unit = int(past_match.group(1)), past_match.group(2).lower()
            if 'week' in unit:
                days = num * 7
            elif 'month' in unit:
                days = num * 30
            else:
                days = num
            logger.info(f"🔍 Found 'past X {unit}': {days} days")
            return days
        
        # Pattern 7: "recent" = 7 days, "this month" = 30 days
        if 'recent' in query_lower or 'recently' in query_lower:
            days = 7
            logger.info(f"🔍 Found 'recent': {days} days")
        elif 'this month' in query_lower or 'monthly' in query_lower:
            days = 30
            logger.info(f"🔍 Found 'this month': {days} days")
        elif 'this week' in query_lower or 'weekly' in query_lower:
            days = 7
            logger.info(f"🔍 Found 'this week': {days} days")
        
        logger.info(f"🔍 Final extracted period: {days} days")
        return days

# Test the AI processor
async def test_ai_processor():
    """Test the AI processor with various queries"""
    processor = MultiQueryGeminiProcessor("dummy_key")
    
    test_queries = [
        "database status",
        "subscription summary for 7 days",
        "payment success rate for last 30 days",
        "subscription performance for 7 days and payment rate for 15 days",
        "compare 7 days vs 30 days performance",
        "subscription metrics for last 2 weeks",
        "payment data for 3 months",
        "recent subscription activity",
        "monthly payment summary"
    ]
    
    print("🧪 Testing AI Processor")
    print("="*50)
    
    for query in test_queries:
        print(f"\n🎯 Query: '{query}'")
        result = await processor.parse_natural_language_query(query)
        print(f"📋 Result: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ai_processor())