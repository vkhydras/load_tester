"""
HTTP Protocol Module

This module implements HTTP protocol support for load testing.
"""

import time
import random
import aiohttp
import logging
import json
import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin

from load_tester.protocols.base import BaseProtocol
from load_tester.config.settings import LoadTestConfig

logger = logging.getLogger("load_tester")


class HttpProtocol(BaseProtocol):
    """HTTP protocol implementation for load testing"""

    def __init__(self, config: LoadTestConfig):
        """
        Initialize the HTTP protocol handler.

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

    async def create_session(self, user_id: int) -> aiohttp.ClientSession:
        """
        Create an HTTP session for the given user.

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

        # Add authentication if configured
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
        self, session: aiohttp.ClientSession, url: str, user_id: int, **kwargs
    ) -> Dict[str, Any]:
        """
        Make an HTTP request and return the result.

        Args:
            session: The HTTP session to use
            url: The URL to request
            user_id: Unique identifier for the user
            **kwargs: Additional request parameters

        Returns:
            Dictionary containing the result of the request
        """
        request_start = time.time()
        method = kwargs.get("method", self.config.request_method)

        result = {
            "user_id": user_id,
            "url": url,
            "method": method,
            "timestamp": time.time(),
            "is_error": False,
            "error_type": None,
        }

        try:
            # Prepare the request data
            request_kwargs = {}

            # Copy any passed kwargs, excluding 'method' which we handled above
            for key, value in kwargs.items():
                if key != "method":
                    request_kwargs[key] = value

            # Use configured payload if none provided in kwargs
            if (
                method in ["POST", "PUT", "PATCH"]
                and "data" not in request_kwargs
                and "json" not in request_kwargs
            ):
                if self.config.payload:
                    payload = self.config.payload
                    if self.config.content_type == "application/json":
                        try:
                            # Try to convert string to JSON
                            request_kwargs["json"] = json.loads(payload)
                        except json.JSONDecodeError:
                            # If not valid JSON, use as-is with content type
                            request_kwargs["data"] = payload
                            request_kwargs.setdefault("headers", {})[
                                "Content-Type"
                            ] = self.config.content_type
                    else:
                        request_kwargs["data"] = payload
                        request_kwargs.setdefault("headers", {})[
                            "Content-Type"
                        ] = self.config.content_type

            # Make the request
            async with session.request(method, url, **request_kwargs) as response:
                # Calculate response time
                response_time = time.time() - request_start

                # Read response content if validation is required
                body = None
                if any(
                    [
                        self.config.validate_text,
                        self.config.validate_regex,
                        self.config.validate_json_path,
                    ]
                ):
                    body = await response.text()

                # Extract cookies
                cookies = {}
                for cookie_name, cookie in response.cookies.items():
                    cookies[cookie_name] = cookie.value

                # Record basic result info
                result.update(
                    {
                        "status": response.status,
                        "response_time": response_time,
                        "content_length": len(body) if body is not None else 0,
                        "headers": dict(response.headers),
                        "cookies": cookies,
                        "body": body,
                    }
                )

                # Validate the response if configured
                validation_result = await self._validate_response(response, body)
                if not validation_result[0]:
                    result["is_error"] = True
                    result["error_type"] = f"validation_failed:{validation_result[1]}"

                if (
                    self.config.verbose and random.random() < 0.05
                ):  # Log ~5% of requests in verbose mode
                    logger.info(
                        f"User {user_id} - {method} {url} - {response.status} - {response_time:.3f}s"
                    )

        except asyncio.TimeoutError:
            result.update(
                {
                    "is_error": True,
                    "error_type": "timeout",
                    "response_time": time.time() - request_start,
                }
            )
            if (
                self.config.verbose and random.random() < 0.2
            ):  # Log more frequently for errors
                logger.warning(f"User {user_id} - {method} {url} - TIMEOUT")

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
                logger.warning(f"User {user_id} - {method} {url} - ERROR: {error_type}")

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
                    f"User {user_id} - {method} {url} - UNEXPECTED ERROR: {error_type}"
                )

        return result

    async def _validate_response(
        self, response: aiohttp.ClientResponse, body: Optional[str]
    ) -> Tuple[bool, str]:
        """
        Validate the response based on configuration.

        Args:
            response: The HTTP response
            body: The response body (if read)

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate status code
        if (
            self.config.validate_status
            and response.status != self.config.validate_status
        ):
            return (
                False,
                f"status_code:{response.status}!={self.config.validate_status}",
            )

        # Validate response text
        if self.config.validate_text and body is not None:
            if self.config.validate_text not in body:
                return False, "text_not_found"

        # Validate regex pattern
        if self.config.validate_regex and body is not None:
            pattern = re.compile(self.config.validate_regex)
            if not pattern.search(body):
                return False, "regex_not_matched"

        # Validate JSON path and value
        if self.config.validate_json_path and body is not None:
            try:
                from jsonpath_ng import parse

                # Parse the JSON
                json_data = json.loads(body)

                # Parse and find the JSON path
                jsonpath_expr = parse(self.config.validate_json_path)
                matches = [match.value for match in jsonpath_expr.find(json_data)]

                # Validate that we found at least one match
                if not matches:
                    return False, "json_path_not_found"

                # If a specific value is required, check it
                if self.config.validate_json_value is not None:
                    # Try to parse the expected value as JSON if possible
                    try:
                        expected_value = json.loads(self.config.validate_json_value)
                    except json.JSONDecodeError:
                        expected_value = self.config.validate_json_value

                    # Check if any match equals the expected value
                    if not any(match == expected_value for match in matches):
                        return False, "json_value_mismatch"

            except json.JSONDecodeError:
                return False, "invalid_json"
            except Exception as e:
                return False, f"json_validation_error:{str(e)}"

        return True, ""
