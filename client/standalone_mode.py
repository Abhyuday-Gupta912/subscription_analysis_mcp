# ===== client/standalone_mode.py =====
#!/usr/bin/env python3
"""
Standalone Mode - CLI Interface for Analytics Client - FINAL VERSION
Provides interactive and single-query modes for direct user interaction.
Connects to your remote MCP server for analytics.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from modules.config import load_client_config
from modules.remote_client import RemoteMCPClient
from modules.formatters import ResultFormatter

logger = logging.getLogger("standalone-mode")

class StandaloneAnalyticsClient:
    """Standalone CLI client for subscription analytics"""
    
    def __init__(self):
        self.config = load_client_config()
        self.client: Optional[RemoteMCPClient] = None
        self.formatter = ResultFormatter("formatted")
        
    async def initialize(self) -> bool:
        """Initialize connection to remote MCP server"""
        try:
            self.client = RemoteMCPClient(self.config)
            await self.client.connect()
            logger.info("✅ Connected to remote MCP server")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.disconnect()
    
    async def execute_query(self, query: str) -> str:
        """Execute a single query and return formatted result"""
        if not self.client:
            raise RuntimeError("Client not initialized")
        
        try:
            result = await self.client.natural_language_query(query)
            return self.formatter.format_result(result, query)
        except Exception as e:
            return f"❌ Query failed: {str(e)}"
    
    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from remote server"""
        if not self.client:
            raise RuntimeError("Client not initialized")
        
        return await self.client.list_tools()

async def run_interactive_mode():
    """Run interactive CLI mode"""
    print("✨ SUBSCRIPTION ANALYTICS - INTERACTIVE MODE")
    print("=" * 60)
    print("Connecting to your remote analytics server...")
    
    client = StandaloneAnalyticsClient()
    
    # Initialize connection
    print("🔌 Connecting to remote MCP server...")
    if not await client.initialize():
        print("❌ Could not connect to remote server.")
        print("🔧 Please run 'python analytics_client.py --setup' to configure connection.")
        print("🔧 Make sure your remote MCP server is running and accessible.")
        return
    
    print("✅ Connected successfully!")
    
    # Show available tools
    try:
        tools = await client.list_available_tools()
        print(f"\n📋 Available tools: {len(tools)}")
        for tool in tools[:3]:  # Show first 3
            print(f"  • {tool.get('name', 'Unknown')}")
        if len(tools) > 3:
            print(f"  • ... and {len(tools) - 3} more")
    except Exception as e:
        logger.warning(f"Could not fetch tools: {e}")
    
    print("\n💬 Enter your queries in natural language (or 'quit' to exit):")
    print("📚 Examples:")
    print("  • 'database status'")
    print("  • 'subscription performance for last 7 days'")
    print("  • 'compare 7 days vs 30 days'")
    print("  • 'analytics from June 1st to today'")
    
    try:
        while True:
            try:
                query = input("\n🎯 Your query: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q', 'bye']:
                    print("👋 Goodbye!")
                    break
                
                if not query:
                    continue
                
                if query.lower() in ['help', 'h']:
                    print("\n📚 You can ask anything in natural language!")
                    print("  • Time periods: 'last 7 days', 'past 2 weeks', 'this month'")
                    print("  • Metrics: 'subscriptions', 'payments', 'success rates'")
                    print("  • Comparisons: 'compare X and Y', 'X versus Y'")
                    print("  • Date ranges: 'from June 1st to today', 'between May 15 and June 30'")
                    print("  • Database: 'database status', 'db health'")
                    continue
                
                if query.lower() == 'tools':
                    print("\n🔧 Available tools:")
                    try:
                        tools = await client.list_available_tools()
                        for tool in tools:
                            print(f"  • {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
                    except Exception as e:
                        print(f"  ❌ Could not fetch tools: {e}")
                    continue
                
                if query.lower() == 'clear':
                    # Clear screen
                    import os
                    os.system('clear' if os.name == 'posix' else 'cls')
                    continue
                
                print("\n🔄 Processing query with remote server...")
                result = await client.execute_query(query)
                print("\n" + result)
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error processing query: {e}")
                logger.exception("Error in interactive mode")
    
    finally:
        await client.cleanup()

async def run_single_query(query: str):
    """Run single query mode"""
    client = StandaloneAnalyticsClient()
    
    try:
        # Initialize connection
        if not await client.initialize():
            print("❌ Could not connect to remote server.")
            print("🔧 Please run 'python analytics_client.py --setup' to configure connection.")
            print("🔧 Make sure your remote MCP server is running and accessible.")
            sys.exit(1)
        
        # Execute query
        result = await client.execute_query(query)
        print(result)
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Query execution failed: {e}")
        logger.exception("Single query mode error")
        sys.exit(1)
    
    finally:
        await client.cleanup()

if __name__ == "__main__":
    # For testing standalone mode directly
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            asyncio.run(test_connection())
        elif sys.argv[1] == "--examples":
            show_examples()
        elif sys.argv[1] == "--status":
            show_status()
        elif sys.argv[1] == "--version":
            show_version()
        else:
            # Single query
            query = " ".join(sys.argv[1:])
            asyncio.run(run_single_query(query))
    else:
        # Interactive mode
        asyncio.run(run_interactive_mode())