#!/usr/bin/env python3
"""
Quick Start Script for Subscription Analytics MCP
Helps you get everything running quickly
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path

def print_banner():
    """Print welcome banner"""
    print("""
🚀 SUBSCRIPTION ANALYTICS MCP - QUICK START
=============================================

This script will help you set up and run your subscription analytics system.
    """)

def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        print(f"Current version: {sys.version}")
        return False
    
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_file_structure():
    """Check if all required files exist"""
    print("\n🔍 Checking file structure...")
    
    required_files = {
        'server/ai_processor.py': '🤖 AI Processor',
        'server/database.py': '🗄️ Database Manager', 
        'server/config.py': '⚙️ Server Config',
        'server/mcp_server.py': '🔌 MCP Server',
        'client/analytics_client.py': '📊 Analytics Client',
        'client/standalone_mode.py': '💻 Standalone Mode',
        'client/mcp_mode.py': '🔌 MCP Mode',
        'client/modules/config.py': '⚙️ Client Config',
        'client/modules/remote_client.py': '📡 Remote Client',
        'client/modules/formatters.py': '🎨 Formatters'
    }
    
    missing_files = []
    for file_path, description in required_files.items():
        if Path(file_path).exists():
            print(f"  ✅ {description}: {file_path}")
        else:
            print(f"  ❌ {description}: {file_path} (MISSING)")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ Missing {len(missing_files)} required files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    print("✅ All required files present")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'mcp',
        'mysql-connector-python',
        'aiohttp',
        'websockets',
        'python-dotenv',
        'google-generativeai'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (MISSING)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing {len(missing_packages)} required packages")
        print("Run this command to install them:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ All dependencies installed")
    return True

def check_env_files():
    """Check environment configuration"""
    print("\n🔧 Checking environment configuration...")
    
    server_env = Path('server/.env')
    client_env = Path('client/.env') 
    root_env = Path('.env')
    
    env_found = False
    
    for env_path in [server_env, client_env, root_env]:
        if env_path.exists():
            print(f"  ✅ Found: {env_path}")
            env_found = True
        else:
            print(f"  ⚠️ Missing: {env_path}")
    
    if not env_found:
        print("\n⚠️ No .env files found")
        print("You'll need to configure environment variables")
        return False
    
    return True

async def test_server_config():
    """Test server configuration"""
    print("\n🧪 Testing server configuration...")
    
    try:
        # Test server config
        os.chdir('server')
        result = subprocess.run([sys.executable, 'config.py', '--check'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("  ✅ Server configuration valid")
            return True
        else:
            print("  ❌ Server configuration invalid")
            print(f"  Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Server config test failed: {e}")
        return False
    finally:
        os.chdir('..')

async def test_client_config():
    """Test client configuration"""
    print("\n🧪 Testing client configuration...")
    
    try:
        # Test client config
        os.chdir('client')
        result = subprocess.run([sys.executable, 'modules/config.py', '--show'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("  ✅ Client configuration found")
            return True
        else:
            print("  ⚠️ Client configuration needs setup")
            return False
            
    except Exception as e:
        print(f"  ❌ Client config test failed: {e}")
        return False
    finally:
        os.chdir('..')

def show_setup_instructions():
    """Show setup instructions"""
    print("""
🔧 SETUP INSTRUCTIONS
=====================

1. SERVER SETUP:
   cd server
   python config.py --create-env
   # Edit server/.env with your database credentials and API keys
   python config.py --check

2. CLIENT SETUP:
   cd client
   python analytics_client.py --setup
   # Follow the interactive setup wizard

3. TEST EVERYTHING:
   python quick_start.py --test

4. RUN THE SYSTEM:
   # Terminal 1 - Start server
   cd server
   python mcp_server.py
   
   # Terminal 2 - Use client
   cd client
   python analytics_client.py

5. CLAUDE DESKTOP INTEGRATION:
   cd client
   python mcp_mode.py --show-config
   # Add the configuration to Claude Desktop
    """)

def show_usage_examples():
    """Show usage examples"""
    print("""
📚 USAGE EXAMPLES
=================

SERVER (Terminal 1):
  cd server
  python mcp_server.py                    # Start MCP server
  python config.py --check               # Check configuration
  python config.py --create-env          # Create sample .env

CLIENT (Terminal 2):
  cd client
  python analytics_client.py             # Interactive mode
  python analytics_client.py --setup     # Setup wizard
  python analytics_client.py --test      # Test connection
  python analytics_client.py --mcp       # MCP mode (Claude Desktop)
  python analytics_client.py "query"     # Single query

NATURAL LANGUAGE QUERIES:
  "show database status" 
  "subscription metrics for last 7 days"
  "compare 7 days vs 30 days performance"
  "analytics from June 1st to today"
  "comprehensive analysis for last month"

CLAUDE DESKTOP:
  1. Configure client: python analytics_client.py --setup
  2. Get config: python mcp_mode.py --show-config  
  3. Add to Claude Desktop settings
  4. Chat with Claude using analytics tools
    """)

async def run_full_test():
    """Run comprehensive system test"""
    print("\n🧪 RUNNING COMPREHENSIVE TESTS")
    print("=" * 40)
    
    all_passed = True
    
    # Test server
    print("\n1. Testing server...")
    if not await test_server_config():
        all_passed = False
    
    # Test client
    print("\n2. Testing client...")
    if not await test_client_config():
        all_passed = False
    
    # TODO: Add more comprehensive tests
    # - Database connection
    # - AI processor
    # - Tool execution
    # - Client-server communication
    
    print(f"\n{'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    return all_passed

def main():
    """Main function"""
    print_banner()
    
    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test':
            success = asyncio.run(run_full_test())
            sys.exit(0 if success else 1)
        elif sys.argv[1] == '--setup':
            show_setup_instructions()
            return
        elif sys.argv[1] == '--examples':
            show_usage_examples()
            return
        elif sys.argv[1] == '--help':
            print("""
🚀 Quick Start Script for Subscription Analytics MCP

Usage:
  python quick_start.py           # Run setup checks
  python quick_start.py --test    # Run comprehensive tests
  python quick_start.py --setup   # Show setup instructions
  python quick_start.py --examples # Show usage examples
  python quick_start.py --help    # Show this help

This script helps you get your subscription analytics system running quickly.
            """)
            return
    
    # Run setup checks
    print("🔍 RUNNING SETUP CHECKS")
    print("=" * 30)
    
    checks = [
        ("Python Version", check_python_version),
        ("File Structure", check_file_structure), 
        ("Dependencies", check_dependencies),
        ("Environment Files", check_env_files)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        if not check_func():
            all_passed = False
    
    # Summary
    print(f"\n{'=' * 30}")
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("\n🎉 Your system is ready to run!")
        print("\n📋 Next steps:")
        print("1. Configure your environment variables (if not done)")
        print("2. Run: python quick_start.py --setup")
        print("3. Test: python quick_start.py --test")
        print("4. Start using the system!")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\n🔧 To fix issues:")
        print("1. Install missing dependencies")
        print("2. Create missing files")
        print("3. Set up environment variables")
        print("4. Run: python quick_start.py --setup")
    
    print(f"\n📚 For help: python quick_start.py --help")

if __name__ == "__main__":
    main()