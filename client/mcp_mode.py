# ===== client/mcp_mode.py =====
#!/usr/bin/env python3
"""
MCP Mode - FINAL VERSION
Acts as a local MCP server for Claude Desktop that proxies requests to your remote MCP server.
This is what Claude Desktop connects to locally, which then forwards to your remote server.
"""
import asyncio
import logging
import sys
from typing import Dict, List, Any
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "modules"))

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

from modules.remote_client import RemoteMCPClient
from modules.config import load_client_config

logger = logging.getLogger("mcp-mode")

class AnalyticsClientMCPProxy:
    """
    Local MCP server that proxies requests to your remote MCP server.
    Claude Desktop -> This Local MCP Server -> Your Remote MCP Server
    """
    
    def __init__(self):
        self.server = Server("subscription-analytics")
        self.remote_client: RemoteMCPClient = None
        self.available_tools: List[Tool] = []
        self._register_handlers()
    
    async def initialize(self) -> bool:
        """Initialize connection to remote MCP server"""
        try:
            config = load_client_config()
            self.remote_client = RemoteMCPClient(config)
            
            # Connect to your remote MCP server
            await self.remote_client.connect()
            
            # Get available tools from remote server
            tools_data = await self.remote_client.list_tools()
            
            # Convert to MCP Tool objects
            self.available_tools = []
            for tool_data in tools_data:
                tool = Tool(
                    name=tool_data['name'],
                    description=tool_data['description'],
                    inputSchema=tool_data.get('inputSchema', {})
                )
                self.available_tools.append(tool)
            
            logger.info(f"✅ Connected to remote server with {len(self.available_tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize remote connection: {e}")
            return False
    
    def _register_handlers(self):
        """Register MCP protocol handlers for Claude Desktop"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Return tools available from remote server"""
            logger.info("📋 Claude Desktop requesting tool list")
            return self.available_tools
        
        @self.server.call_tool()
        async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Proxy tool calls to remote server"""
            logger.info(f"🎯 Claude Desktop calling tool: '{name}' with args: {arguments}")
            
            try:
                # Forward the tool call to your remote MCP server
                result = await self.remote_client.call_tool(name, arguments)
                
                logger.info(f"✅ Tool call successful, result length: {len(result)}")
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                error_msg = f"❌ Error proxying tool call to remote server: {e}"
                logger.error(error_msg, exc_info=True)
                return [TextContent(type="text", text=error_msg)]

    async def cleanup(self):
        """Cleanup remote connection"""
        if self.remote_client:
            await self.remote_client.disconnect()

async def run_mcp_mode():
    """Run the local MCP proxy server for Claude Desktop"""
    logger.info("🔌 Starting local MCP proxy server for Claude Desktop")
    
    proxy = AnalyticsClientMCPProxy()
    
    # Initialize connection to your remote server
    if not await proxy.initialize():
        print("❌ Could not connect to the remote analytics server.")
        print("🔧 Please run 'python analytics_client.py --setup' to configure connection.")
        print("🔧 Make sure your remote MCP server is running and accessible.")
        sys.exit(1)
    
    try:
        # Start the stdio MCP server for Claude Desktop
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("🚀 Local MCP proxy server running. Ready for Claude Desktop connections.")
            await proxy.server.run(
                read_stream,
                write_stream,
                proxy.server.create_initialization_options()
            )
    
    except KeyboardInterrupt:
        logger.info("🛑 MCP proxy server interrupted by user")
    
    except Exception as e:
        logger.error(f"❌ MCP proxy server error: {e}")
        raise
    
    finally:
        logger.info("🧹 Cleaning up proxy server...")
        await proxy.cleanup()
        logger.info("👋 MCP proxy server shutdown complete")

if __name__ == "__main__":
    asyncio.run(run_mcp_mode())