# ===== client/modules/remote_client.py =====
#!/usr/bin/env python3
"""
Remote MCP Client - FINAL VERSION
Connects to remote MCP server via WebSocket with proper error handling
"""
import asyncio
import json
import logging
import websockets
from typing import Dict, Any, List

logger = logging.getLogger("remote-mcp-client")

class RemoteMCPClient:
    """Client that connects to your remote MCP server"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.server_url = config.get('server_url', 'ws://localhost:8765')
        self.api_key = config.get('api_key')
        self.websocket = None
        self.connected = False
        
        logger.info(f"🔗 Remote MCP client configured for: {self.server_url}")
    
    async def connect(self):
        """Connect to remote MCP server"""
        if self.connected:
            return
        
        if not self.api_key:
            raise ValueError("API Key is required to connect to remote server")
        
        try:
            logger.info(f"🔌 Connecting to remote MCP server at {self.server_url}")
            
            # Simple connection (based on working test pattern)
            self.websocket = await websockets.connect(self.server_url)
            
            # Send authentication
            auth_message = {
                "api_key": self.api_key,
                "client_type": "mcp_client",
                "version": "1.0.0"
            }
            await self.websocket.send(json.dumps(auth_message))
            
            # Wait for auth response
            response = await self.websocket.recv()
            auth_result = json.loads(response)
            
            if "error" in auth_result:
                raise ConnectionError(f"Authentication failed: {auth_result['error']}")
            
            self.connected = True
            logger.info("✅ Connected and authenticated with remote MCP server")
            
        except websockets.exceptions.ConnectionClosedError:
            raise ConnectionError("Connection to remote server was closed unexpectedly")
        except ConnectionRefusedError:
            raise ConnectionError(f"Connection refused. Is the MCP server running on {self.server_url}?")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to remote server: {str(e)}")
    
    async def disconnect(self):
        """Safely disconnect from MCP server"""
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass  # Ignore any disconnect errors
        
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
            response = await self.websocket.recv()
            return json.loads(response)
            
        except websockets.exceptions.ConnectionClosed:
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

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    
    import asyncio
    asyncio.run(test_remote_client())