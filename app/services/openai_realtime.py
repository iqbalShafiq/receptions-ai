"""
OpenAI Realtime API Service - Direct WebSocket connection
Handles bidirectional audio streaming with OpenAI
"""
import asyncio
import json
from typing import Optional
import websockets
from websockets.client import WebSocketClientProtocol
from app.config import settings


class OpenAIRealtimeService:
    """Service for OpenAI Realtime API with direct WebSocket connection"""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = "gpt-4o-realtime-preview-2024-10-01"
        self.ws_url = "wss://api.openai.com/v1/realtime"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

    async def connect(self) -> bool:
        """
        Connect to OpenAI Realtime API with Bearer token authentication.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Check API key
            if not self.api_key or not self.api_key.startswith("sk-"):
                return False

            url = f"{self.ws_url}?model={self.model}"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1",
            }

            # Try different connection methods
            try:
                # Method 1: Try with headers parameter (websockets v12+)
                self.ws = await websockets.connect(
                    url,
                    subprotocols=["realtime"],
                    header={
                        "Authorization": f"Bearer {self.api_key}",
                        "OpenAI-Beta": "realtime=v1",
                    }
                )
            except TypeError:
                try:
                    # Method 2: Try with additional_headers (websockets v11)
                    self.ws = await websockets.connect(
                        url,
                        subprotocols=["realtime"],
                        additional_headers=[
                            ("Authorization", f"Bearer {self.api_key}"),
                            ("OpenAI-Beta", "realtime=v1"),
                        ]
                    )
                except TypeError:
                    # Method 3: Just try basic connection
                    self.ws = await websockets.connect(url)

            # Send session update
            await self.send_session_update()
            return True

        except Exception as e:
            self.ws = None
            return False

    async def send_session_update(self) -> None:
        """Configure OpenAI Realtime session"""
        if not self.ws:
            raise Exception("WebSocket not connected")

        # Use instructions to make OpenAI relay its response and wait for confirmation
        session_update = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": "You are a helpful AI receptionist. Keep responses brief and professional.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1",
                },
            },
        }

        await self.ws.send(json.dumps(session_update))

    async def send_audio_append(self, audio_base64: str) -> None:
        """Send audio to OpenAI"""
        if not self.ws:
            raise Exception("WebSocket not connected")

        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64,
        }
        await self.ws.send(json.dumps(message))

    async def commit_audio(self) -> None:
        """Commit audio buffer"""
        if not self.ws:
            raise Exception("WebSocket not connected")

        message = {"type": "input_audio_buffer.commit"}
        await self.ws.send(json.dumps(message))

    async def request_response(self) -> None:
        """Request response from OpenAI"""
        if not self.ws:
            raise Exception("WebSocket not connected")

        message = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
            },
        }
        await self.ws.send(json.dumps(message))

    async def request_agent_response(self, agent_text: str) -> None:
        """Send agent's response text to OpenAI for TTS conversion and audio output"""
        if not self.ws:
            raise Exception("WebSocket not connected")

        # Send the agent's response as text content
        message = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "output": [
                    {
                        "type": "text",
                        "text": agent_text,
                    }
                ],
            },
        }
        await self.ws.send(json.dumps(message))

    async def receive_message(self) -> dict:
        """Receive message from OpenAI"""
        if not self.ws:
            raise Exception("WebSocket not connected")

        return json.loads(await self.ws.recv())

    async def close(self) -> None:
        """Close WebSocket connection"""
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None

    async def is_connected(self) -> bool:
        """Check if connected"""
        if not self.ws:
            return False
        try:
            # Check if websocket is still open
            # Different websockets versions have different attributes
            return not getattr(self.ws, 'closed', False)
        except:
            return False
