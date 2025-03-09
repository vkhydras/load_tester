"""
Base Reporter Module

This module defines the base class for all reporter implementations.
"""

import abc
from typing import Dict, Any

from config.settings import LoadTestConfig


class BaseReporter(abc.ABC):
    """Base class for all reporters"""

    def __init__(self, config: LoadTestConfig):
        """
        Initialize the reporter.

        Args:
            config: The test configuration
        """
        self.config = config

    @abc.abstractmethod
    async def report_start(self, config: LoadTestConfig) -> None:
        """
        Report the start of the test.

        Args:
            config: The test configuration
        """
        pass

    @abc.abstractmethod
    async def report_progress(self, progress: Dict[str, Any]) -> None:
        """
        Report test progress.

        Args:
            progress: Dictionary with progress information
        """
        pass

    @abc.abstractmethod
    async def report(self, results: Dict[str, Any]) -> None:
        """
        Report test results.

        Args:
            results: Dictionary with test results
        """
        pass
