# ===== SERVER CONFIG (server/config.py) =====
#!/usr/bin/env python3
"""
Configuration Manager for the Subscription Analytics MCP Server.
FIXED VERSION - Consistent environment variable naming
"""
import os
import logging
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """Loads, validates, and returns configuration from environment variables."""
    # Search for .env in the current directory or parent directory
    env_path = Path('.env')
    if not env_path.exists():
        env_path = Path(__file__).parent / '.env'
    
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger.info(f"✅ Loaded .env file from: {env_path.resolve()}")
    else:
        logger.warning("⚠️ No .env file found. Relying solely on shell environment variables.")
    
    config = {
        # Database configuration
        'db_host': os.getenv('DB_HOST'),
        'db_port': int(os.getenv('DB_PORT', 3306)),
        'db_name': os.getenv('DB_NAME'),
        'db_user': os.getenv('DB_USER'),
        'db_password': os.getenv('DB_PASSWORD'),
        
        # AI and API configuration
        'gemini_api_key': os.getenv('GEMINI_API_KEY'),
        
        # FIXED: Use consistent API key name
        'analytics_api_key': os.getenv('ANALYTICS_API_KEY'),
        
        # Server configuration
        'server_host': os.getenv('SERVER_HOST', '0.0.0.0'),
        'server_port': int(os.getenv('SERVER_PORT', 8000)),
        'log_level': os.getenv('LOG_LEVEL', 'INFO').upper(),
    }
    
    # Set logging level based on config
    log_level = getattr(logging, config['log_level'], logging.INFO)
    logging.getLogger().setLevel(log_level)

    # Validate required keys and log the final config
    _validate_config(config)
    _log_config_safely(config)
    
    return config

def _validate_config(config: Dict[str, Any]):
    """Ensures all required secrets and settings are present."""
    required_keys = ['db_password', 'gemini_api_key', 'analytics_api_key']
    missing_keys = [key for key in required_keys if not config.get(key)]
    
    if missing_keys:
        error_msg = (f"❌ Missing required configuration: {', '.join(missing_keys)}. "
                     "Please set them in your server's .env file.")
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("✅ Configuration validation passed.")

def _log_config_safely(config: Dict[str, Any]):
    """Logs the configuration with sensitive values masked."""
    def mask(secret: str) -> str:
        return f"{secret[:4]}...{secret[-4:]}" if secret and len(secret) > 8 else "********"

    logger.info("🔧 Server Configuration Loaded:")
    logger.info(f"  - 🗄️  Database: {config.get('db_user')}@{config.get('db_host')}:{config.get('db_port')}")
    logger.info(f"  - 🤖 Gemini API Key: {mask(config.get('gemini_api_key'))}")
    logger.info(f"  - 🔑 Analytics API Key: {mask(config.get('analytics_api_key'))}")

# ===== CLIENT CONFIG (client/modules/config.py) =====
#!/usr/bin/env python3
"""
Configuration module for Analytics Client
FIXED VERSION - Consistent environment variable naming
"""
import os
import asyncio
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

def load_client_config() -> Dict[str, Any]:
    """Load client configuration from .env file or environment variables."""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    
    return {
        'server_url': os.getenv('ANALYTICS_SERVER_URL', 'http://localhost:8000'),
        'api_key': os.getenv('ANALYTICS_API_KEY'),  # FIXED: Consistent naming
        'timeout': int(os.getenv('ANALYTICS_TIMEOUT', '90')),
        'retry_attempts': int(os.getenv('ANALYTICS_RETRIES', '3')),
    }

def save_client_config(config: Dict[str, Any]) -> bool:
    """Save client configuration to a .env file."""
    try:
        env_path = Path(__file__).parent.parent / '.env'
        
        # Clean the URL before saving
        clean_url = config['server_url'].strip().rstrip('/')
        
        content = (
            f"# Subscription Analytics Client Configuration\n\n"
            f"ANALYTICS_SERVER_URL={clean_url}\n"
            f"ANALYTICS_API_KEY={config['api_key']}\n"  # FIXED: Consistent naming
            f"ANALYTICS_TIMEOUT={config['timeout']}\n"
            f"ANALYTICS_RETRIES={config['retry_attempts']}\n"
        )
        with open(env_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ Failed to save configuration to {env_path}: {e}")
        return False

async def setup_wizard():
    """Interactive setup wizard for first-time client configuration."""
    print("\n--- 🔧 Subscription Analytics Client Setup Wizard ---")
    config = {
        'server_url': input("Enter your server URL (e.g., http://localhost:8000): ").strip(),
        'api_key': input("Enter the Analytics API Key: ").strip(),
        'timeout': int(input("Connection timeout in seconds (default: 90): ").strip() or "90"),
        'retry_attempts': int(input("Retry attempts (default: 3): ").strip() or "3"),
    }
    
    # Validate URL format
    if '::' in config['server_url']:
        print(f"❌ Invalid URL format detected: {config['server_url']}. Please try again.")
        return

    print("\n🧪 Testing connection...")
    if await test_connection_with_config(config):
        print("✅ Connection test successful!")
        if save_client_config(config):
            print("\n🎉 Configuration saved successfully!")
    else:
        print("\n❌ Connection test failed. Please check your settings.")

async def test_connection_with_config(config: Dict[str, Any]) -> bool:
    from remote_client import RemoteAnalyticsClient
    client = RemoteAnalyticsClient(config)
    try:
        await client.natural_language_query("database status")
        return True
    except Exception as e:
        print(f"   -> Failure reason: {e}")
        return False
    finally:
        if client and client.connected:
            await client.disconnect()

async def test_connection():
    return await test_connection_with_config(load_client_config())

if __name__ == "__main__":
    asyncio.run(setup_wizard())