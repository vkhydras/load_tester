"""
Metrics Collection Module

This module handles collecting and analyzing metrics during load tests.
"""

import time
import statistics
from collections import deque, Counter
from typing import Dict, List, Any, Optional
import asyncio


class MetricsCollector:
    """Collects and analyzes metrics during load tests"""

    def __init__(self, max_recent_samples: int = 100):
        """
        Initialize the metrics collector.

        Args:
            max_recent_samples: Maximum number of recent samples to keep for calculations
        """
        # Timestamps for calculating requests per second
        self.start_time = time.time()
        self.last_update_time = self.start_time

        # Response time tracking
        self.recent_response_times = deque(maxlen=max_recent_samples)
        self.min_response_time = float("inf")
        self.max_response_time = 0

        # Request counters
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.active_users = 0

        # Last second metrics
        self.requests_last_second = 0
        self.current_rps = 0

        # Status codes and errors
        self.status_codes = Counter()
        self.errors = Counter()

        # Historical data
        self.metrics_history = []
        self.max_rps = 0
        self.response_times = []

        # Thread safety
        self.lock = asyncio.Lock()

    def record_result(self, result: Dict[str, Any]) -> None:
        """
        Record a test result.

        Args:
            result: Dictionary containing the test result
        """
        # Extract data from the result
        response_time = result.get("response_time", 0)
        status = result.get("status", 0)
        is_error = result.get("is_error", False)
        error_type = result.get("error_type", None)

        # Update counters
        self.total_requests += 1
        self.requests_last_second += 1

        if is_error:
            self.failed_requests += 1
            self.errors[error_type] += 1
        else:
            self.successful_requests += 1
            self.status_codes[status] += 1

        # Track response times
        self.recent_response_times.append(response_time)
        self.response_times.append(response_time)

        if response_time < self.min_response_time:
            self.min_response_time = response_time

        if response_time > self.max_response_time:
            self.max_response_time = response_time

    def update_periodic_metrics(self) -> None:
        """Update metrics that need periodic calculation"""
        current_time = time.time()
        time_diff = current_time - self.last_update_time

        # Calculate requests per second
        if time_diff > 0:
            self.current_rps = self.requests_last_second / time_diff
            self.max_rps = max(self.max_rps, self.current_rps)

        # Store current metrics for historical analysis
        self.metrics_history.append(
            {
                "timestamp": current_time - self.start_time,
                "rps": self.current_rps,
                "active_users": self.active_users,
                "completed_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "avg_response_time": self.get_avg_response_time(),
                "errors": sum(self.errors.values()),
                "status_codes": dict(self.status_codes),
            }
        )

        # Reset counters
        self.requests_last_second = 0
        self.last_update_time = current_time

    def increment_active_users(self) -> None:
        """Increment the active users counter"""
        self.active_users += 1

    def decrement_active_users(self) -> None:
        """Decrement the active users counter"""
        self.active_users = max(0, self.active_users - 1)

    def get_active_users(self) -> int:
        """Get the number of currently active users"""
        return self.active_users

    def get_completed_requests(self) -> int:
        """Get the total number of completed requests"""
        return self.total_requests

    def get_current_rps(self) -> float:
        """Get the current requests per second rate"""
        return self.current_rps

    def get_avg_response_time(self) -> float:
        """Get the average response time from recent requests"""
        if not self.recent_response_times:
            return 0
        return sum(self.recent_response_times) / len(self.recent_response_times)

    def get_error_count(self) -> int:
        """Get the total number of errors"""
        return sum(self.errors.values())

    def get_results(self) -> Dict[str, Any]:
        """
        Generate complete results from collected metrics.

        Returns:
            Dictionary with complete test results
        """
        test_duration = time.time() - self.start_time

        results = {
            "duration": test_duration,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "requests_per_second": self.total_requests / max(1, test_duration),
            "max_rps": self.max_rps,
            "status_codes": dict(self.status_codes),
            "errors": dict(self.errors),
            "response_times": self._calculate_response_time_stats(),
            "history": self.metrics_history,
        }

        return results

    def _calculate_response_time_stats(self) -> Dict[str, float]:
        """Calculate response time statistics"""
        if not self.response_times:
            return {
                "min": 0,
                "max": 0,
                "avg": 0,
                "median": 0,
                "p90": 0,
                "p95": 0,
                "p99": 0,
                "std_dev": 0,
            }

        sorted_times = sorted(self.response_times)

        def safe_percentile(p):
            """Calculate percentile safely"""
            idx = min(int(p * len(sorted_times)), len(sorted_times) - 1)
            return sorted_times[idx]

        return {
            "min": min(self.response_times),
            "max": max(self.response_times),
            "avg": statistics.mean(self.response_times),
            "median": statistics.median(self.response_times),
            "p90": safe_percentile(0.9),
            "p95": safe_percentile(0.95),
            "p99": safe_percentile(0.99),
            "std_dev": (
                statistics.stdev(self.response_times)
                if len(self.response_times) > 1
                else 0
            ),
        }
