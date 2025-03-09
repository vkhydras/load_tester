"""
WebSocket Protocol Module

This module implements WebSocket protocol support for load testing.
"""

import time
import random
import logging
import json
import asyncio
from typing import Dict, List, Any, Optional

import aiohttp
from aiohttp import WSMsgType

from load_tester.protocols.base import BaseProtocol
from load_tester.config.settings import LoadTestConfig

logger = logging.getLogger("load_tester")


class WebSocketProtocol(BaseProtocol):
    """WebSocket protocol implementation for load testing"""

    def __init__(self, config: LoadTestConfig):
        """
        Initialize the WebSocket protocol handler.

        Args:
            config: The test configuration
        """
        super().__init__(config)

        # User agent strings for realistic simulation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        ]

    async def create_session(self, user_id: int):
        """
        Create a WebSocket session for the given user.

        Args:
            user_id: Unique identifier for the user

        Returns:
            aiohttp.ClientSession: The created session
        """
        # Set up headers
        headers = dict(self.config.headers)

        # Add User-Agent if not provided
        if "User-Agent" not in headers:
            headers["User-Agent"] = random.choice(self.user_agents)

        # Add authentication headers
        self._add_auth_headers(headers)

        # Create TCP connector with limits
        connector = aiohttp.TCPConnector(
            limit_per_host=self.config.connections_per_host,
            limit=self.config.max_connections // max(1, self.config.num_users),
        )

        # Create the session
        session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            connector=connector,
            cookies=self.config.cookies,
        )

        return session

    def _add_auth_headers(self, headers: Dict[str, str]) -> None:
        """
        Add authentication headers based on configuration.

        Args:
            headers: Headers dictionary to update
        """
        if self.config.auth_type == "basic":
            import base64

            if self.config.auth_username and self.config.auth_password:
                auth_string = f"{self.config.auth_username}:{self.config.auth_password}"
                auth_bytes = auth_string.encode("ascii")
                base64_bytes = base64.b64encode(auth_bytes)
                base64_string = base64_bytes.decode("ascii")
                headers["Authorization"] = f"Basic {base64_string}"

        elif self.config.auth_type == "bearer":
            if self.config.auth_token:
                headers["Authorization"] = f"Bearer {self.config.auth_token}"

        elif self.config.auth_type == "custom":
            if self.config.auth_header:
                # Format should be name:value
                if ":" in self.config.auth_header:
                    name, value = self.config.auth_header.split(":", 1)
                    headers[name.strip()] = value.strip()

    async def request(
        self, session, url: str, user_id: int, **kwargs
    ) -> Dict[str, Any]:
        """
        Make a WebSocket request and return the result.

        Args:
            session: The HTTP session to use
            url: The WebSocket URL
            user_id: Unique identifier for the user
            **kwargs: Additional request parameters

        Returns:
            Dictionary containing the result of the request
        """
        request_start = time.time()

        result = {
            "user_id": user_id,
            "url": url,
            "method": "WEBSOCKET",
            "timestamp": time.time(),
            "is_error": False,
            "error_type": None,
        }

        try:
            # Get additional websocket parameters
            ws_kwargs = {}
            for key, value in kwargs.items():
                if key in ["protocols", "origin", "compress", "proxy", "ssl"]:
                    ws_kwargs[key] = value

            # Open the WebSocket connection
            async with session.ws_connect(url, **ws_kwargs) as ws:
                # Mark connection as established
                result["ws_connected"] = True
                result["status"] = 101  # WebSocket protocol switch

                # Prepare message to send if configured
                message = kwargs.get("message", self.config.payload)

                # Send a message if available
                if message:
                    content_type = kwargs.get("content_type", self.config.content_type)

                    if content_type == "application/json":
                        try:
                            # Try to send as JSON
                            if isinstance(message, str):
                                # Parse JSON string
                                json_data = json.loads(message)
                                await ws.send_json(json_data)
                            else:
                                # Assume already a JSON-compatible object
                                await ws.send_json(message)
                        except json.JSONDecodeError:
                            # If not valid JSON, send as text
                            await ws.send_str(message)
                    elif content_type == "application/octet-stream":
                        # Send as binary data
                        if isinstance(message, str):
                            await ws.send_bytes(message.encode("utf-8"))
                        elif isinstance(message, bytes):
                            await ws.send_bytes(message)
                        else:
                            # Convert to string then to bytes
                            await ws.send_bytes(str(message).encode("utf-8"))
                    else:
                        # Send as text
                        await ws.send_str(str(message))

                # Wait for a response with timeout
                response_data = None
                response_type = None

                try:
                    # Get max_messages parameter or default to 1
                    max_messages = kwargs.get("max_messages", 1)
                    messages = []

                    # Collect up to max_messages or until timeout
                    for _ in range(max_messages):
                        msg = await asyncio.wait_for(
                            ws.receive(), timeout=self.config.timeout
                        )

                        if msg.type == WSMsgType.TEXT:
                            response_type = "text"
                            messages.append(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            response_type = "binary"
                            messages.append(msg.data)
                        elif msg.type == WSMsgType.ERROR:
                            result["is_error"] = True
                            result["error_type"] = "ws_protocol_error"
                            break
                        elif msg.type == WSMsgType.CLOSED:
                            break
                        elif msg.type == WSMsgType.CLOSING:
                            break

                    # Store messages
                    if messages:
                        if len(messages) == 1:
                            response_data = messages[0]
                        else:
                            response_data = messages

                except asyncio.TimeoutError:
                    result["is_error"] = True
                    result["error_type"] = "ws_timeout"

                # Calculate response time
                response_time = time.time() - request_start

                # Record result
                result.update(
                    {
                        "response_time": response_time,
                        "content_length": (
                            len(response_data)
                            if response_data and isinstance(response_data, (str, bytes))
                            else 0
                        ),
                        "response_data": response_data,
                        "response_type": response_type,
                    }
                )

                # Close connection explicitly (good practice)
                await ws.close()

                if (
                    self.config.verbose and random.random() < 0.05
                ):  # Log ~5% of requests in verbose mode
                    logger.info(
                        f"User {user_id} - WS {url} - {result['status']} - {response_time:.3f}s"
                    )

        except aiohttp.ClientError as e:
            error_type = type(e).__name__
            result.update(
                {
                    "is_error": True,
                    "error_type": error_type,
                    "response_time": time.time() - request_start,
                }
            )
            if self.config.verbose and random.random() < 0.2:
                logger.warning(f"User {user_id} - WS {url} - ERROR: {error_type}")

        except Exception as e:
            error_type = type(e).__name__
            result.update(
                {
                    "is_error": True,
                    "error_type": error_type,
                    "response_time": time.time() - request_start,
                }
            )
            if self.config.verbose and random.random() < 0.2:
                logger.error(
                    f"User {user_id} - WS {url} - UNEXPECTED ERROR: {error_type}"
                )

        return result
