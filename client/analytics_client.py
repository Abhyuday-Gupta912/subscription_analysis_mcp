import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "modules"))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("analytics-client")

async def main():
    """Main entry point with mode detection"""
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            show_help()
            return
        
        elif sys.argv[1] == '--mcp':
            # MCP mode for Claude Desktop - acts as MCP server that proxies to your remote server
            logger.info("🔌 Starting in MCP mode for Claude Desktop")
            from mcp_mode import run_mcp_mode
            await run_mcp_mode()
            return
        
        elif sys.argv[1] == '--version':
            print("Subscription Analytics Client v1.0.0")
            return
        
        elif sys.argv[1] == '--setup':
            # Setup wizard
            logger.info("🔧 Starting setup wizard")
            from modules.config import setup_wizard
            await setup_wizard()
            return
        
        elif sys.argv[1] == '--test':
            # Test connection to remote MCP server
            logger.info("🧪 Testing connection")
            from modules.config import test_connection
            success = await test_connection()
            sys.exit(0 if success else 1)
        
        else:
            # Single query mode
            query = " ".join(sys.argv[1:])
            logger.info(f"🎯 Single query mode: '{query}'")
            from standalone_mode import run_single_query
            await run_single_query(query)
            return
    
    # Interactive mode detection
    if sys.stdin.isatty():
        # Interactive terminal - standalone mode
        logger.info("💻 Starting in interactive standalone mode")
        from standalone_mode import run_interactive_mode
        await run_interactive_mode()
    else:
        # Non-interactive (called by Claude Desktop) - MCP mode
        logger.info("🔌 Starting in MCP mode (non-interactive)")
        from mcp_mode import run_mcp_mode
        await run_mcp_mode()

def show_help():
    """Show help information"""
    print("""
🎯 Subscription Analytics Client

USAGE:
  python analytics_client.py                    # Interactive mode
  python analytics_client.py --mcp              # MCP mode (Claude Desktop)
  python analytics_client.py "your query"       # Single query
  python analytics_client.py --setup            # Setup wizard
  python analytics_client.py --test             # Test connection
  python analytics_client.py --help             # Show this help

MODES:
  📊 Interactive Mode (Default)
    - Full-featured CLI interface
    - Natural language queries
    - Beautiful formatted output
    - Query history and suggestions

  🔌 MCP Mode (Claude Desktop Integration)
    - Acts as local MCP server for Claude Desktop
    - Proxies requests to your remote analytics server
    - Real-time analytics in Claude conversations

EXAMPLES:
  # Interactive mode
  python analytics_client.py
  
  # Single queries
  python analytics_client.py "show database status"
  python analytics_client.py "subscription metrics for last 7 days"
  python analytics_client.py "compare 7 days vs 30 days performance"
  python analytics_client.py "analytics from June 1st to today"
  
  # MCP mode (for Claude Desktop config)
  python analytics_client.py --mcp
  
  # Setup and testing
  python analytics_client.py --setup
  python analytics_client.py --test

CONFIGURATION:
  The client connects to your remote MCP server for analytics.
  Run --setup to configure connection settings.

CLAUDE DESKTOP SETUP:
  Add this to your Claude Desktop config:
  {
    "mcpServers": {
      "subscription-analytics": {
        "command": "python",
        "args": ["/path/to/analytics_client.py", "--mcp"],
        "env": {
          "ANALYTICS_SERVER_URL": "ws://your-server.com:8765",
          "ANALYTICS_API_KEY": "your_api_key_here"
        }
      }
    }
  }

REQUIREMENTS:
  - Python 3.8+
  - Network access to your remote MCP server
  - Valid API credentials

For more help: https://github.com/your-repo/subscription-analytics
    """)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"❌ Client error: {e}")
        sys.exit(1)

