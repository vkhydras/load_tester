"""
Base Scenario Module

This module defines the base class for all scenario implementations.
"""

import abc
import random
from typing import Dict, List, Any, Optional

from config.settings import LoadTestConfig
from protocols.base import BaseProtocol


class BaseScenario(abc.ABC):
    """Base class for all test scenarios"""

    def __init__(self, config: LoadTestConfig, protocol: BaseProtocol):
        """
        Initialize the scenario.

        Args:
            config: The test configuration
            protocol: The protocol handler to use
        """
        self.config = config
        self.protocol = protocol
        self.session_cache = {}  # Cache sessions by user_id

    @abc.abstractmethod
    async def execute(self, user_id: int) -> Dict[str, Any]:
        """
        Execute the scenario for the given user.

        Args:
            user_id: Unique identifier for the user

        Returns:
            Dictionary containing the result of the execution
        """
        pass

    async def get_session(self, user_id: int):
        """
        Get or create a session for the given user.

        Args:
            user_id: Unique identifier for the user

        Returns:
            Session object for the protocol
        """
        if user_id not in self.session_cache:
            self.session_cache[user_id] = await self.protocol.create_session(user_id)

        return self.session_cache[user_id]

    def select_target_url(self) -> str:
        """
        Select a target URL based on the configuration.

        Returns:
            URL to request
        """
        if self.config.url_mode == "exact":
            return self.config.url

        # Use custom paths or default paths
        target_urls = self.config.get_target_urls()
        return random.choice(target_urls)

    async def cleanup(self) -> None:
        """Clean up resources used by the scenario"""
        # Close all sessions
        for user_id, session in self.session_cache.items():
            try:
                if hasattr(session, "close"):
                    if callable(session.close):
                        # For aiohttp and similar
                        await session.close()
                    else:
                        # For other types of sessions
                        session.close()
            except Exception as e:
                # Just log errors during cleanup
                import logging

                logger = logging.getLogger("load_tester")
                logger.warning(f"Error closing session for user {user_id}: {e}")

        # Clear the cache
        self.session_cache.clear()
