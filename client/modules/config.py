#!/usr/bin/env python3
"""
Configuration module for Analytics Client - COMPLETELY FIXED VERSION
Handles client-side configuration, setup, and testing for remote MCP server connection.
"""
import os
import asyncio
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

def load_client_config() -> Dict[str, Any]:
    """Load client configuration from .env file or environment variables."""
    # Look for .env file in client directory
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    
    return {
        # Your remote MCP server WebSocket URL
        'server_url': os.getenv('ANALYTICS_SERVER_URL', 'ws://localhost:8765'),
        
        # API key for authentication with your server
        'api_key': os.getenv('ANALYTICS_API_KEY'),
        
        # Connection settings
        'timeout': int(os.getenv('ANALYTICS_TIMEOUT', '30')),
        'retry_attempts': int(os.getenv('ANALYTICS_RETRIES', '3')),
        'ping_interval': int(os.getenv('ANALYTICS_PING_INTERVAL', '20')),
    }

def save_client_config(config: Dict[str, Any]) -> bool:
    """Save client configuration to a .env file."""
    try:
        env_path = Path(__file__).parent.parent / '.env'
        
        # Clean the URL before saving
        clean_url = config['server_url'].strip()
        
        # Ensure WebSocket protocol
        if not clean_url.startswith(('ws://', 'wss://')):
            if clean_url.startswith('http://'):
                clean_url = clean_url.replace('http://', 'ws://')
            elif clean_url.startswith('https://'):
                clean_url = clean_url.replace('https://', 'wss://')
            elif '://' not in clean_url:
                # Assume ws:// if no protocol specified
                clean_url = f"ws://{clean_url}"
        
        content = (
            f"# Subscription Analytics Client Configuration\n"
            f"# Connection to your remote MCP server\n\n"
            f"ANALYTICS_SERVER_URL={clean_url}\n"
            f"ANALYTICS_API_KEY={config['api_key']}\n"
            f"ANALYTICS_TIMEOUT={config['timeout']}\n"
            f"ANALYTICS_RETRIES={config['retry_attempts']}\n"
            f"ANALYTICS_PING_INTERVAL={config.get('ping_interval', 20)}\n"
        )
        
        with open(env_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Configuration saved to {env_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to save configuration to {env_path}: {e}")
        return False

async def setup_wizard():
    """Interactive setup wizard for first-time client configuration."""
    print("\n" + "="*60)
    print("🔧 SUBSCRIPTION ANALYTICS CLIENT SETUP WIZARD")
    print("="*60)
    print("This wizard will help you connect to your remote MCP server.")
    print()
    
    # Get server URL
    print("1. Remote MCP Server URL:")
    print("   Examples:")
    print("   - ws://your-server.com:8765 (WebSocket)")
    print("   - wss://your-server.com:8765 (Secure WebSocket)")
    print("   - localhost:8765 (Local testing)")
    server_url = input("   Enter server URL: ").strip()
    
    # Get API key
    print("\n2. Authentication:")
    api_key = input("   Enter your Analytics API Key: ").strip()
    
    # Get connection settings
    print("\n3. Connection Settings (optional, press Enter for defaults):")
    timeout = input("   Connection timeout in seconds (default: 30): ").strip() or "30"
    retry_attempts = input("   Retry attempts (default: 3): ").strip() or "3"
    
    # Validate inputs
    if not server_url:
        print("❌ Server URL is required!")
        return
    
    if not api_key:
        print("❌ API key is required!")
        return
    
    config = {
        'server_url': server_url,
        'api_key': api_key,
        'timeout': int(timeout),
        'retry_attempts': int(retry_attempts),
        'ping_interval': 20
    }
    
    print(f"\n4. Testing connection to {config['server_url']}...")
    print("   This may take a moment...")
    
    if await test_connection_with_config(config):
        print("✅ Connection test successful!")
        
        if save_client_config(config):
            print("\n🎉 Setup completed successfully!")
            print("\nYou can now use the client:")
            print("  - Interactive mode: python analytics_client.py")
            print("  - Single query: python analytics_client.py 'your query'")
            print("  - Claude Desktop: python analytics_client.py --mcp")
            print()
            print("For Claude Desktop integration, add this to your config:")
            print('{')
            print('  "mcpServers": {')
            print('    "subscription-analytics": {')
            print('      "command": "python",')
            print(f'      "args": ["{Path(__file__).parent.parent.absolute() / "analytics_client.py"}", "--mcp"]')
            print('    }')
            print('  }')
            print('}')
        else:
            print("❌ Failed to save configuration")
    else:
        print("❌ Connection test failed. Please check your settings and try again.")
        print("\nTroubleshooting:")
        print("  - Ensure your remote MCP server is running")
        print("  - Check the server URL format (should start with ws:// or wss://)")
        print("  - Verify your API key is correct")
        print("  - Check network connectivity and firewall settings")

async def test_connection_with_config(config: Dict[str, Any]) -> bool:
    """Test connection with provided configuration - FIXED VERSION"""
    try:
        from remote_client import RemoteMCPClient
        
        client = RemoteMCPClient(config)
        
        # Test connection
        await client.connect()
        
        # Test a simple tool call
        await client.get_database_status()
        
        # FIXED: Manual cleanup instead of calling disconnect()
        if client.websocket:
            try:
                await client.websocket.close()
            except Exception:
                pass  # Ignore any close errors
        
        client.connected = False
        client.websocket = None
        
        return True
        
    except Exception as e:
        print(f"   -> Connection failed: {e}")
        return False

async def test_connection() -> bool:
    """Test connection with current configuration"""
    config = load_client_config()
    
    if not config.get('api_key'):
        print("❌ No API key configured. Run --setup first.")
        return False
    
    if not config.get('server_url'):
        print("❌ No server URL configured. Run --setup first.")
        return False
    
    print(f"🧪 Testing connection to {config['server_url']}...")
    return await test_connection_with_config(config)

def show_config():
    """Show current configuration"""
    config = load_client_config()
    
    print("📋 CURRENT CONFIGURATION")
    print("="*40)
    print(f"Server URL: {config.get('server_url', 'Not configured')}")
    print(f"API Key: {'Configured ✅' if config.get('api_key') else 'Missing ❌'}")
    print(f"Timeout: {config.get('timeout', 30)}s")
    print(f"Retry Attempts: {config.get('retry_attempts', 3)}")
    print(f"Ping Interval: {config.get('ping_interval', 20)}s")
    
    env_path = Path(__file__).parent.parent / '.env'
    print(f"Config File: {env_path}")
    print(f"File Exists: {'Yes ✅' if env_path.exists() else 'No ❌'}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--setup":
            asyncio.run(setup_wizard())
        elif sys.argv[1] == "--test":
            result = asyncio.run(test_connection())
            sys.exit(0 if result else 1)
        elif sys.argv[1] == "--show":
            show_config()
        else:
            print("Usage: python config.py [--setup|--test|--show]")
    else:
        asyncio.run(setup_wizard())