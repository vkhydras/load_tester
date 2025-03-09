"""
Base Protocol Module

This module defines the base class for all protocol implementations.
"""

import abc
from typing import Dict, Any, Optional

from config.settings import LoadTestConfig


class BaseProtocol(abc.ABC):
    """Base class for all protocol implementations"""

    def __init__(self, config: LoadTestConfig):
        """
        Initialize the protocol handler.

        Args:
            config: The test configuration
        """
        self.config = config

    @abc.abstractmethod
    async def create_session(self, user_id: int):
        """
        Create a session for the given user.

        Args:
            user_id: Unique identifier for the user

        Returns:
            Session object appropriate for the protocol
        """
        pass

    @abc.abstractmethod
    async def request(
        self, session, url: str, user_id: int, **kwargs
    ) -> Dict[str, Any]:
        """
        Make a request using the protocol and return the result.

        Args:
            session: The session to use
            url: The URL or resource identifier to request
            user_id: Unique identifier for the user
            **kwargs: Additional request parameters

        Returns:
            Dictionary containing the result of the request
        """
        pass
