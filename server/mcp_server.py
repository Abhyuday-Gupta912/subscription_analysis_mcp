#!/usr/bin/env python3
"""
Remote WebSocket MCP Server for Subscription Analytics
Enhanced for production deployment with proper error handling
"""
from dotenv import load_dotenv
from pathlib import Path

# Load environment first
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)

import asyncio
import logging
import sys
import websockets
import json
import os
import signal
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

from ai_processor import MultiQueryGeminiProcessor
from database import DatabaseManager
from config import load_config

# Enhanced logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/mcp_server.log') if os.path.exists('/tmp') else logging.NullHandler()
    ]
)
logger = logging.getLogger("remote-mcp-server")

class RemoteSubscriptionAnalyticsMCPServer:
    """Remote WebSocket MCP Server for subscription analytics"""
    
    def __init__(self):
        self.server = Server("subscription-analytics")
        self.config = load_config()
        self.db_manager = DatabaseManager(self.config)
        self.ai_processor = MultiQueryGeminiProcessor(
            api_key=self.config['gemini_api_key'], 
            database_manager=self.db_manager
        )
        
        # Define available tools for remote clients
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
            ),
            Tool(
                name="get_analytics_by_date_range",
                description="Get comprehensive analytics for a specific date range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format"
                        }
                    },
                    "required": ["start_date", "end_date"]
                }
            )
        ]
        
        logger.info(f"🔧 Remote MCP server initialized with {len(self.tools)} tools")
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return formatted result"""
        logger.info(f"🔧 Executing tool: {name} with args: {arguments}")
        
        try:
            if name == "natural_language_query":
                return await self._handle_natural_language_query(arguments)
            
            # For direct database tools, call the database manager
            if hasattr(self.db_manager, name):
                db_method = getattr(self.db_manager, name)
                result = await db_method(**arguments)
                formatted = self._format_result(name, result)
                logger.info(f"✅ Tool {name} completed successfully")
                return formatted
            
            return f"❌ Unknown tool: {name}"
            
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return f"❌ Error: {error_msg}"
    
    async def _handle_natural_language_query(self, arguments: Dict[str, Any]) -> str:
        """Handle natural language queries using AI processor"""
        query = arguments.get("query", "")
        logger.info(f"🤖 Processing NL query: '{query}'")
        
        try:
            # Parse query with AI
            tool_calls = await self.ai_processor.parse_natural_language_query(query)
            
            if not tool_calls:
                return "❌ I couldn't understand your query. Please try rephrasing it."
            
            # Execute the suggested tool calls
            results = []
            for tool_call in tool_calls:
                tool_name = tool_call['tool']
                parameters = tool_call.get('parameters', {})
                
                logger.info(f"🔧 Executing AI-suggested tool: {tool_name}")
                
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
            logger.error(f"❌ Natural language query failed: {e}", exc_info=True)
            return f"❌ Query processing failed: {str(e)}"
    
    def _format_result(self, tool_name: str, data: Any) -> str:
        """Format results for display"""
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
        elif "analytics" in tool_name:
            return self._format_analytics_data(data)
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
        if 'database' in data:
            lines.append(f"🏢 Database: {data['database']}")
        
        return "\n".join(lines)
    
    def _format_subscription_summary(self, data: Dict[str, Any]) -> str:
        """Format subscription summary data"""
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
    
    def _format_analytics_data(self, data: Dict[str, Any]) -> str:
        """Format analytics data for date ranges"""
        lines = []
        start_date = data.get('start_date', 'unknown')
        end_date = data.get('end_date', 'unknown')
        lines.append(f"📊 **ANALYTICS REPORT ({start_date} to {end_date})**")
        
        if 'subscriptions' in data:
            sub_data = data['subscriptions']
            lines.append(f"📈 **Subscriptions:**")
            lines.append(f"   🆕 New: {sub_data.get('new_subscriptions', 0):,}")
        
        if 'payments' in data:
            pay_data = data['payments']
            lines.append(f"💳 **Payments:**")
            lines.append(f"   📊 Total: {pay_data.get('total_payments', 0):,}")
            lines.append(f"   📈 Success Rate: {pay_data.get('success_rate', '0%')}")
            lines.append(f"   💰 Revenue: {pay_data.get('total_revenue', '$0.00')}")
        
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

def authenticate_client(api_key: str) -> bool:
    """Authenticate client API key"""
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
    
    # Development fallback
    if not valid_keys and os.getenv('ENVIRONMENT', 'production') == 'development':
        valid_keys.add('test_key_123')
        logger.warning("⚠️ Using development fallback API key")
    
    is_valid = api_key in valid_keys
    logger.info(f"🔑 Authentication attempt: {'✅ Success' if is_valid else '❌ Failed'}")
    return is_valid

async def handle_websocket_client(websocket, path):
    """Handle WebSocket connections from remote clients"""
    client_addr = websocket.remote_address if hasattr(websocket, 'remote_address') else 'unknown'
    logger.info(f"🔌 New WebSocket connection from {client_addr}")
    
    server_instance = None
    
    try:
        # Authentication handshake
        auth_message = await websocket.recv()
        auth_data = json.loads(auth_message)
        
        if not authenticate_client(auth_data.get('api_key', '')):
            await websocket.send(json.dumps({"error": "Authentication failed"}))
            logger.warning(f"❌ Authentication failed for {client_addr}")
            return
        
        logger.info(f"✅ Client {client_addr} authenticated successfully")
        await websocket.send(json.dumps({"status": "authenticated", "server": "remote-mcp-analytics"}))
        
        # Create server instance for this connection
        server_instance = RemoteSubscriptionAnalyticsMCPServer()
        logger.info(f"🔧 Server instance created for {client_addr}")
        
        # Main message loop
        async for message in websocket:
            try:
                logger.info(f"📨 Received from {client_addr}: {message[:100]}...")
                
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
                    
                    logger.info(f"🔧 {client_addr} executing: {name}")
                    result = await server_instance.execute_tool(name, arguments)
                    response = {"result": result}
                
                elif data.get('method') == 'ping':
                    response = {"result": "pong", "timestamp": data.get('timestamp')}
                
                else:
                    response = {"error": f"Unknown method: {data.get('method')}"}
                
                await websocket.send(json.dumps(response))
                logger.info(f"📤 Response sent to {client_addr}")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON from {client_addr}: {e}")
                await websocket.send(json.dumps({"error": "Invalid JSON"}))
            except Exception as e:
                logger.error(f"❌ Error handling message from {client_addr}: {e}", exc_info=True)
                await websocket.send(json.dumps({"error": str(e)}))
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"🔌 Client {client_addr} disconnected normally")
    except Exception as e:
        logger.error(f"❌ WebSocket error with {client_addr}: {e}", exc_info=True)
    finally:
        logger.info(f"🧹 Cleaning up connection for {client_addr}")

async def run_remote_websocket_server():
    """Run the remote WebSocket MCP server"""
    # Get configuration from environment
    host = os.getenv('MCP_HOST', '0.0.0.0')
    port = int(os.getenv('PORT', os.getenv('MCP_PORT', '8765')))
    
    # Verify required environment variables
    required_vars = ['DB_HOST', 'DB_PASSWORD', 'GEMINI_API_KEY', 'ANALYTICS_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    configured_key = os.getenv('ANALYTICS_API_KEY', 'NOT_SET')
    
    logger.info("🚀 Starting Remote WebSocket MCP Server")
    logger.info(f"🌐 Host: {host}:{port}")
    logger.info(f"🔑 API Key: {configured_key[:8]}...")
    logger.info(f"🗄️  Database: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")
    
    # Setup graceful shutdown
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("🛑 Received shutdown signal")
        stop_event.set()
    
    # Register signal handlers
    for sig in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(sig, lambda s, f: signal_handler())
    
    try:
        # Start WebSocket server
        async with websockets.serve(
            handle_websocket_client, 
            host, 
            port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        ):
            logger.info("✅ Remote MCP server is running and ready for connections")
            logger.info(f"🔗 Clients can connect to: ws://{host}:{port}")
            logger.info("📋 Available tools: natural_language_query, get_database_status, get_subscription_summary, etc.")
            
            # Wait for shutdown signal
            await stop_event.wait()
            
    except Exception as e:
        logger.error(f"❌ Server startup failed: {e}", exc_info=True)
        sys.exit(1)

async def main():
    """Main entry point for remote WebSocket MCP server"""
    logger.info("🚀 Initializing Remote Subscription Analytics MCP Server")
    
    try:
        # Test database connection on startup
        config = load_config()
        db_manager = DatabaseManager(config)
        db_status = await db_manager.get_database_status()
        
        if db_status.get('status') == 'connected':
            logger.info("✅ Database connection verified")
        else:
            logger.warning(f"⚠️ Database connection issue: {db_status.get('error', 'Unknown')}")
        
        # Start the server
        await run_remote_websocket_server()
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("👋 Remote MCP server shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())