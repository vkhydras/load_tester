"""
JSON Reporter Module

This module implements a reporter that saves results to JSON files.
"""

import json
import os
import time
from typing import Dict, Any, List
from datetime import datetime

from load_tester.reporters.base import BaseReporter
from load_tester.config.settings import LoadTestConfig


class JsonReporter(BaseReporter):
    """Reporter that saves results to JSON files"""

    def __init__(self, config: LoadTestConfig):
        """
        Initialize the JSON reporter.

        Args:
            config: The test configuration
        """
        super().__init__(config)
        self.metrics_data = []
        self.start_time = None

    async def report_start(self, config: LoadTestConfig) -> None:
        """
        Report the start of the test.

        Args:
            config: The test configuration
        """
        self.start_time = time.time()
        print(f"JSON Reporter: Results will be saved to JSON files")

    async def report_progress(self, progress: Dict[str, Any]) -> None:
        """
        Report test progress.

        Args:
            progress: Dictionary with progress information
        """
        # Store metrics data for later
        self.metrics_data.append(
            {
                "timestamp": progress["elapsed"],
                "active_users": progress["active_users"],
                "completed_requests": progress["completed_requests"],
                "current_rps": progress["current_rps"],
                "avg_response_time": progress["avg_response_time"]
                * 1000,  # Convert to ms
                "progress_pct": progress["progress_pct"],
                "errors": progress["errors"],
            }
        )

    async def report(self, results: Dict[str, Any]) -> None:
        """
        Report test results.

        Args:
            results: Dictionary with test results
        """
        # Create directory for JSON files if needed
        output_dir = os.path.dirname(self.config.get_output_filename("json"))
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Prepare the complete results object
        complete_results = self._prepare_complete_results(results)

        # Save the results to a file
        filename = self.config.get_output_filename("json")

        with open(filename, "w") as f:
            json.dump(complete_results, f, indent=2)

        print(f"JSON Reporter: Results saved to {filename}")

    def _prepare_complete_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare a complete results object with all data.

        Args:
            results: Dictionary with test results

        Returns:
            Dictionary with complete results
        """
        # Calculate success/failure rates
        success_rate = 0
        failure_rate = 0

        if results["total_requests"] > 0:
            success_rate = (
                results["successful_requests"] / results["total_requests"]
            ) * 100
            failure_rate = (
                results["failed_requests"] / results["total_requests"]
            ) * 100

        # Create a complete results object
        complete_results = {
            "test_info": {
                "url": self.config.url,
                "protocol": self.config.protocol,
                "mode": self.config.mode,
                "users": self.config.num_users,
                "test_time": datetime.now().isoformat(),
                "duration": results["duration"],
            },
            "config": self._get_config_dict(),
            "summary": {
                "total_requests": results["total_requests"],
                "successful_requests": results["successful_requests"],
                "failed_requests": results["failed_requests"],
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "requests_per_second": results["requests_per_second"],
                "max_rps": results["max_rps"],
            },
            "response_times": results.get("response_times", {}),
            "status_codes": self._count_to_list(results.get("status_codes", {})),
            "errors": self._count_to_list(results.get("errors", {})),
            "history": results.get("history", []),
            "metrics_data": self.metrics_data,
        }

        return complete_results

    def _get_config_dict(self) -> Dict[str, Any]:
        """
        Get configuration as a dictionary.

        Returns:
            Dictionary with configuration values
        """
        return {
            "url": self.config.url,
            "url_mode": self.config.url_mode,
            "url_paths": self.config.url_paths,
            "num_users": self.config.num_users,
            "mode": self.config.mode,
            "requests_per_user": self.config.requests_per_user,
            "duration": self.config.duration,
            "ramp_up": self.config.ramp_up,
            "timeout": self.config.timeout,
            "think_time_min": self.config.think_time_min,
            "think_time_max": self.config.think_time_max,
            "connections_per_host": self.config.connections_per_host,
            "max_connections": self.config.max_connections,
            "protocol": self.config.protocol,
            "scenario": self.config.scenario,
            "request_method": self.config.request_method,
            "rate_limit": self.config.rate_limit,
        }

    def _count_to_list(self, count_dict: Dict[Any, int]) -> List[Dict[str, Any]]:
        """
        Convert a counter dictionary to a list of dicts for better JSON serialization.

        Args:
            count_dict: Dictionary with counts

        Returns:
            List of dictionaries with name and count
        """
        return [
            {"name": str(name), "count": count}
            for name, count in sorted(count_dict.items())
        ]
