#!/usr/bin/env python3
"""
Complete Fixed MCP Server for Subscription Analytics
WebSocket-based MCP server with proper debugging and formatting
"""
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / '.env', override=True)
import asyncio
import logging
import sys
import websockets
import json
import os
from pathlib import Path
from typing import Dict, Any, List

# MCP imports
try:
    import mcp
    from mcp import types
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    import mcp.server.stdio
except ImportError:
    print("❌ MCP not installed. Run: pip install mcp")
    sys.exit(1)

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Force load .env file first
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)

from ai_processor import MultiQueryGeminiProcessor
from database import DatabaseManager
from config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp-analytics-server")

class SubscriptionAnalyticsMCPServer:
    """Complete MCP Server for subscription analytics"""
    
    def __init__(self):
        self.server = Server("subscription-analytics")
        self.config = load_config()
        self.db_manager = DatabaseManager(self.config)
        self.ai_processor = MultiQueryGeminiProcessor(
            api_key=self.config['gemini_api_key'], 
            database_manager=self.db_manager
        )
        
        # Define available tools for clients
        self.tools = [
            Tool(
                name="natural_language_query",
                description="Process natural language queries about subscription analytics using AI",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query about subscription data"
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="get_database_status",
                description="Check database connection and get basic statistics",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_subscriptions_in_last_days",
                description="Get subscription statistics for the last N days",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to look back",
                            "minimum": 1,
                            "maximum": 365
                        }
                    },
                    "required": ["days"]
                }
            ),
            Tool(
                name="get_payment_success_rate_in_last_days",
                description="Get payment success rate statistics for the last N days",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to look back",
                            "minimum": 1,
                            "maximum": 365
                        }
                    },
                    "required": ["days"]
                }
            ),
            Tool(
                name="get_subscription_summary",
                description="Get comprehensive subscription and payment summary",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to look back (default: 30)",
                            "minimum": 1,
                            "maximum": 365,
                            "default": 30
                        }
                    },
                    "required": []
                }
            )
        ]
    
    async def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return formatted result - DEBUG VERSION"""
        
        logger.info(f"🔧 EXECUTING TOOL: {name}")
        logger.info(f"🔧 ARGUMENTS: {arguments}")
        
        if name == "natural_language_query":
            return await self._handle_natural_language_query(arguments)
        
        # For direct database tools, call the database manager
        if hasattr(self.db_manager, name):
            logger.info(f"🔧 Calling database method: {name}")
            db_method = getattr(self.db_manager, name)
            
            try:
                result = await db_method(**arguments)
                logger.info(f"🔧 RAW DATABASE RESULT: {result}")
                logger.info(f"🔧 RESULT TYPE: {type(result)}")
                
                formatted = self._format_result(name, result)
                logger.info(f"🔧 FORMATTED RESULT: {formatted}")
                
                return formatted
            except Exception as e:
                error_msg = f"Database method {name} failed: {str(e)}"
                logger.error(error_msg)
                import traceback
                traceback.print_exc()
                return f"❌ Error: {error_msg}"
        
        return f"❌ Unknown tool: {name}"
    
    async def _handle_natural_language_query(self, arguments: Dict[str, Any]) -> str:
        """Handle natural language queries using AI processor"""
        query = arguments.get("query", "")
        logger.info(f"🤖 Processing natural language query: '{query}'")
        
        try:
            # Parse query with AI
            tool_calls = await self.ai_processor.parse_natural_language_query(query)
            
            if not tool_calls:
                return "I couldn't understand your query. Please try rephrasing it."
            
            # Execute the suggested tool calls
            results = []
            for tool_call in tool_calls:
                tool_name = tool_call['tool']
                parameters = tool_call.get('parameters', {})
                
                logger.info(f"🔧 Executing suggested tool: {tool_name} with params: {parameters}")
                
                if hasattr(self.db_manager, tool_name):
                    db_method = getattr(self.db_manager, tool_name)
                    result = await db_method(**parameters)
                    formatted_result = self._format_result(tool_name, result)
                    results.append(formatted_result)
            
            if len(results) == 1:
                return results[0]
            else:
                return f"🔍 **Combined Analysis for:** '{query}'\n\n" + "\n\n---\n\n".join(results)
        
        except Exception as e:
            logger.error(f"Natural language query failed: {e}")
            import traceback
            traceback.print_exc()
            return f"❌ Query processing failed: {str(e)}"
    
    def _format_result(self, tool_name: str, data: Any) -> str:
        """Format results for display - DEBUG VERSION"""
        
        # Debug logging
        logger.info(f"🎨 Formatting result for {tool_name}")
        logger.info(f"🎨 Data type: {type(data)}")
        logger.info(f"🎨 Data content: {data}")
        
        if isinstance(data, dict) and "error" in data:
            return f"❌ **{tool_name.replace('_', ' ').title()}**: {data['error']}"
        
        if not isinstance(data, dict):
            return str(data)
        
        # Format based on tool type
        if tool_name == "get_database_status":
            return self._format_database_status(data)
        elif tool_name == "get_subscription_summary":
            return self._format_subscription_summary(data)
        elif "subscription" in tool_name:
            return self._format_subscription_data(data)
        elif "payment" in tool_name:
            return self._format_payment_data(data)
        else:
            return self._format_generic_data(data, tool_name)
    
    def _format_database_status(self, data: Dict[str, Any]) -> str:
        """Format database status"""
        lines = ["🗄️ **DATABASE STATUS**"]
        lines.append(f"📊 Status: {data.get('status', 'unknown').upper()}")
        
        if 'total_subscriptions' in data:
            lines.append(f"📝 Total Subscriptions: {data['total_subscriptions']:,}")
        if 'total_payments' in data:
            lines.append(f"💳 Total Payments: {data['total_payments']:,}")
        
        return "\n".join(lines)
    
    def _format_subscription_summary(self, data: Dict[str, Any]) -> str:
        """Format subscription summary data specifically"""
        logger.info(f"🎨 Formatting subscription summary: {data}")
        
        lines = []
        period = data.get('period_days', 'unknown')
        lines.append(f"📈 **SUBSCRIPTION SUMMARY ({period} days)**")
        
        # Handle subscription data
        if 'subscriptions' in data:
            sub_data = data['subscriptions']
            lines.append(f"🆕 New Subscriptions: {sub_data.get('new_subscriptions', 0):,}")
            lines.append(f"✅ Active Subscriptions: {sub_data.get('active_subscriptions', 0):,}")
            lines.append(f"❌ Cancelled Subscriptions: {sub_data.get('cancelled_subscriptions', 0):,}")
        
        # Handle payment data
        if 'payments' in data:
            pay_data = data['payments']
            lines.append(f"💳 Total Payments: {pay_data.get('total_payments', 0):,}")
            lines.append(f"📈 Success Rate: {pay_data.get('success_rate', '0%')}")
            lines.append(f"💰 Total Revenue: {pay_data.get('total_revenue', '$0.00')}")
        
        # Show summary if available
        if 'summary' in data:
            lines.append(f"\n📝 Summary: {data['summary']}")
        
        return "\n".join(lines)
    
    def _format_subscription_data(self, data: Dict[str, Any]) -> str:
        """Format subscription data"""
        period = data.get('period_days', 'unknown')
        lines = [f"📈 **SUBSCRIPTION METRICS ({period} days)**"]
        
        if 'new_subscriptions' in data:
            lines.append(f"🆕 New Subscriptions: {data['new_subscriptions']:,}")
        if 'active_subscriptions' in data:
            lines.append(f"✅ Active Subscriptions: {data['active_subscriptions']:,}")
        if 'cancelled_subscriptions' in data:
            lines.append(f"❌ Cancelled Subscriptions: {data['cancelled_subscriptions']:,}")
        
        return "\n".join(lines)
    
    def _format_payment_data(self, data: Dict[str, Any]) -> str:
        """Format payment data"""
        period = data.get('period_days', 'unknown')
        lines = [f"💳 **PAYMENT METRICS ({period} days)**"]
        
        if 'total_payments' in data:
            lines.append(f"📊 Total Payments: {data['total_payments']:,}")
        if 'successful_payments' in data:
            lines.append(f"✅ Successful: {data['successful_payments']:,}")
        if 'success_rate' in data:
            lines.append(f"📈 Success Rate: {data['success_rate']}")
        if 'total_revenue' in data:
            lines.append(f"💰 Total Revenue: {data['total_revenue']}")
        
        return "\n".join(lines)
    
    def _format_generic_data(self, data: Dict[str, Any], tool_name: str) -> str:
        """Format generic data"""
        title = tool_name.replace('_', ' ').title()
        lines = [f"📊 **{title}**"]
        
        for key, value in data.items():
            if key not in ['error']:
                formatted_key = key.replace('_', ' ').title()
                lines.append(f"• {formatted_key}: {value}")
        
        return "\n".join(lines)

# Authentication function
def authenticate_client(api_key: str) -> bool:
    """Authenticate client API key"""
    # Get API keys from environment
    valid_keys = set()
    
    # Primary API key
    main_key = os.getenv('ANALYTICS_API_KEY')
    if main_key:
        valid_keys.add(main_key)
    
    # Additional API keys (for multiple clients)
    for i in range(1, 6):
        extra_key = os.getenv(f'ANALYTICS_API_KEY_{i}')
        if extra_key:
            valid_keys.add(extra_key)
    
    # Fallback for local development only
    if not valid_keys:
        valid_keys.add('test_key_123')
        logger.warning("⚠️ No API keys found in .env, using fallback test key")
    
    logger.info(f"🔑 Configured API keys: {[key[:8] + '...' for key in valid_keys]}")
    return api_key in valid_keys

# WebSocket handler
async def handle_websocket_client(websocket):
    """Handle WebSocket connections - FIXED to stay connected"""
    logger.info(f"🔌 New WebSocket connection from {websocket.remote_address}")
    
    server_instance = None
    
    try:
        # First message should be authentication
        auth_message = await websocket.recv()
        auth_data = json.loads(auth_message)
        
        if not authenticate_client(auth_data.get('api_key', '')):
            await websocket.send(json.dumps({"error": "Authentication failed"}))
            return
        
        logger.info("✅ Client authenticated successfully")
        await websocket.send(json.dumps({"status": "authenticated"}))
        
        # Create server instance ONCE for this connection
        server_instance = SubscriptionAnalyticsMCPServer()
        logger.info("🔧 Server instance created")
        
        # Proper message loop that stays connected
        while True:
            try:
                # Wait for next message
                message = await websocket.recv()
                logger.info(f"📨 Received message: {message}")
                
                data = json.loads(message)
                
                if data.get('method') == 'tools/list':
                    tools_data = []
                    for tool in server_instance.tools:
                        tools_data.append({
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        })
                    response = {"result": tools_data}
                
                elif data.get('method') == 'tools/call':
                    params = data.get('params', {})
                    name = params.get('name')
                    arguments = params.get('arguments', {})
                    
                    logger.info(f"🔧 Executing tool: {name} with args: {arguments}")
                    result = await server_instance._execute_tool(name, arguments)
                    response = {"result": result}
                
                else:
                    response = {"error": "Unknown method"}
                
                logger.info(f"📤 Sending response: {str(response)[:200]}...")
                await websocket.send(json.dumps(response))
                logger.info("✅ Response sent successfully")
                
            except websockets.exceptions.ConnectionClosed:
                logger.info("🔌 Client disconnected normally")
                break
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON: {e}")
                await websocket.send(json.dumps({"error": "Invalid JSON"}))
            except Exception as e:
                logger.error(f"❌ Error handling message: {e}")
                import traceback
                traceback.print_exc()
                await websocket.send(json.dumps({"error": str(e)}))
    
    except websockets.exceptions.ConnectionClosed:
        logger.info("🔌 WebSocket connection closed during auth")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("🧹 Cleaning up connection")

# WebSocket mode for remote clients
async def run_websocket_mode():
    """Run MCP server in WebSocket mode for remote clients"""
    host = os.getenv('MCP_HOST', '0.0.0.0')
    port = int(os.getenv('MCP_PORT', '8765'))
    
    # Get configured API key for display
    configured_key = os.getenv('ANALYTICS_API_KEY', 'test_key_123')
    
    logger.info(f"🌐 Starting MCP server on WebSocket ws://{host}:{port}")
    
    async with websockets.serve(handle_websocket_client, host, port):
        logger.info("✅ MCP server is running and ready for connections")
        logger.info(f"🔗 Clients can connect to: ws://{host}:{port}")
        logger.info(f"🔑 Configured API key: {configured_key[:8]}...")
        await asyncio.Future()  # Run forever

async def main():
    """Main entry point"""
    logger.info("🚀 Starting Subscription Analytics MCP Server")
    await run_websocket_mode()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)