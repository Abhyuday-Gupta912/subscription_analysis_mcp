#!/usr/bin/env python3
"""
Remote MCP Client - FIXED VERSION with correct class name
Connects to remote MCP server via WebSocket with proper error handling
"""
import asyncio
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK

logger = logging.getLogger("remote-mcp-client")

class RemoteMCPClient:
    """Client that connects to your remote MCP server - Fixed class name"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.server_url = config.get('server_url', 'ws://localhost:8765')
        self.api_key = config.get('api_key')
        self.websocket = None
        self.connected = False
        
        # Connection settings
        self.timeout = config.get('timeout', 90)
        self.ping_interval = config.get('ping_interval', 20)
        self.retry_attempts = config.get('retry_attempts', 3)
        self.reconnect_delay = 2
        
        # SSL context for wss:// connections
        self.ssl_context = None
        if self.server_url.startswith('wss://'):
            self.ssl_context = ssl.create_default_context()
        
        logger.info(f"🔗 Remote MCP client configured for: {self.server_url}")
    
    async def connect(self):
        """Connect to remote MCP server with retry logic"""
        if self.connected:
            return
        
        if not self.api_key:
            raise ValueError("API Key is required to connect to remote server")
        
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"🔌 Connection attempt {attempt + 1}/{self.retry_attempts} to {self.server_url}")
                
                # Create WebSocket connection
                connect_kwargs = {
                    'ping_interval': self.ping_interval,
                    'ping_timeout': 10,
                    'close_timeout': 10
                }
                
                if self.ssl_context:
                    connect_kwargs['ssl'] = self.ssl_context
                
                self.websocket = await asyncio.wait_for(
                    websockets.connect(self.server_url, **connect_kwargs),
                    timeout=self.timeout
                )
                
                # Send authentication
                auth_message = {
                    "api_key": self.api_key,
                    "client_type": "mcp_client",
                    "version": "1.0.0"
                }
                
                await self.websocket.send(json.dumps(auth_message))
                
                # Wait for auth response
                response = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=10
                )
                auth_result = json.loads(response)
                
                if "error" in auth_result:
                    raise ConnectionError(f"Authentication failed: {auth_result['error']}")
                
                self.connected = True
                logger.info("✅ Connected and authenticated with remote MCP server")
                return
                
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Connection timeout on attempt {attempt + 1}")
            except ConnectionRefusedError:
                logger.warning(f"🚫 Connection refused on attempt {attempt + 1}")
            except Exception as e:
                logger.warning(f"❌ Connection failed on attempt {attempt + 1}: {e}")
            
            if attempt < self.retry_attempts - 1:
                wait_time = self.reconnect_delay * (2 ** attempt)
                logger.info(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
        
        raise ConnectionError(f"Failed to connect after {self.retry_attempts} attempts")
    
    async def disconnect(self):
        """Safely disconnect from MCP server"""
        if self.websocket:
            try:
                await self.websocket.close()
                await self.websocket.wait_closed()
            except Exception as e:
                logger.debug(f"Disconnect cleanup error (safe to ignore): {e}")
        
        self.websocket = None
        self.connected = False
        logger.info("🔌 Disconnected from remote MCP server")
    
    async def _send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to server and get response"""
        if not self.connected:
            await self.connect()
        
        try:
            # Send message
            await self.websocket.send(json.dumps(message))
            
            # Wait for response
            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=self.timeout
            )
            return json.loads(response)
            
        except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK):
            self.connected = False
            raise ConnectionError("Connection to server was lost")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid response from server: {e}")
        except Exception as e:
            raise ConnectionError(f"Communication error with remote server: {e}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from remote server"""
        message = {
            "method": "tools/list",
            "id": "list_tools_request"
        }
        
        response = await self._send_message(message)
        
        if "error" in response:
            raise Exception(f"Remote server error: {response['error']}")
        
        return response.get("result", [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> str:
        """Call a tool on the remote server"""
        message = {
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments or {}
            },
            "id": f"tool_call_{name}"
        }
        
        response = await self._send_message(message)
        
        if "error" in response:
            raise Exception(f"Remote tool call failed: {response['error']}")
        
        return response.get("result", "No result returned")
    
    async def natural_language_query(self, query: str) -> str:
        """Send natural language query to remote server"""
        return await self.call_tool("natural_language_query", {"query": query})
    
    async def get_database_status(self) -> str:
        """Get database status from remote server"""
        return await self.call_tool("get_database_status")
    
    async def get_subscription_summary(self, days: int = 30) -> str:
        """Get subscription summary from remote server"""
        return await self.call_tool("get_subscription_summary", {"days": days})

# For backwards compatibility
EnhancedRemoteMCPClient = RemoteMCPClient

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    
    async def test_remote_client():
        config = {
            'server_url': 'ws://localhost:8765',
            'api_key': 'test_key_123'
        }
        
        client = RemoteMCPClient(config)
        try:
            await client.connect()
            result = await client.get_database_status()
            print(f"Test result: {result}")
        except Exception as e:
            print(f"Test failed: {e}")
        finally:
            await client.disconnect()
    
    asyncio.run(test_remote_client())