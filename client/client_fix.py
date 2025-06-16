async def _send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
    """Send message to server and get response - FIXED to reuse connection"""
    # Only connect if not already connected
    if not self.connected:
        await self.connect()
    
    try:
        logger.info(f"📤 Sending: {message}")
        
        # Send message
        await self.websocket.send(json.dumps(message))
        
        # Wait for response
        response = await self.websocket.recv()
        logger.info(f"📥 Received: {response[:200]}...")
        
        return json.loads(response)
        
    except websockets.exceptions.ConnectionClosed:
        logger.warning("🔌 Connection lost, will reconnect on next request")
        self.connected = False
        raise ConnectionError("Connection to server was lost")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid response from server: {e}")
    except Exception as e:
        logger.error(f"❌ Communication error: {e}")
        raise ConnectionError(f"Communication error with remote server: {e}")
