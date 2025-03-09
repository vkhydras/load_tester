"""
CSV Reporter Module

This module implements a reporter that saves results to CSV files.
"""

import csv
import os
import time
from typing import Dict, Any, List

from reporters.base import BaseReporter
from config.settings import LoadTestConfig


class CsvReporter(BaseReporter):
    """Reporter that saves results to CSV files"""

    def __init__(self, config: LoadTestConfig):
        """
        Initialize the CSV reporter.

        Args:
            config: The test configuration
        """
        super().__init__(config)
        self.detailed_results = []
        self.metrics_data = []
        self.start_time = None

    async def report_start(self, config: LoadTestConfig) -> None:
        """
        Report the start of the test.

        Args:
            config: The test configuration
        """
        self.start_time = time.time()
        print(f"CSV Reporter: Results will be saved to CSV files")

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
            }
        )

    async def report(self, results: Dict[str, Any]) -> None:
        """
        Report test results.

        Args:
            results: Dictionary with test results
        """
        # Create directory for CSV files if needed
        output_dir = os.path.dirname(self.config.get_output_filename("csv"))
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Save summary results
        self._save_summary_results(results)

        # Save detailed results if available
        if "history" in results:
            self._save_detailed_results(results["history"])

        # Save metrics data if collected
        if self.metrics_data:
            self._save_metrics_data()

        print(f"CSV Reporter: Results saved to CSV files")

    def _save_summary_results(self, results: Dict[str, Any]) -> None:
        """
        Save summary results to a CSV file.

        Args:
            results: Dictionary with test results
        """
        filename = self.config.get_output_filename("csv").replace(
            ".csv", "_summary.csv"
        )

        with open(filename, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)

            # Write header
            writer.writerow(["Metric", "Value"])

            # Write basic information
            writer.writerow(["URL", self.config.url])
            writer.writerow(["Protocol", self.config.protocol.upper()])
            writer.writerow(["Mode", self.config.mode.upper()])
            writer.writerow(["Users", self.config.num_users])
            writer.writerow(["Duration (s)", f"{results['duration']:.2f}"])
            writer.writerow(["Total Requests", results["total_requests"]])
            writer.writerow(["Successful Requests", results["successful_requests"]])
            writer.writerow(["Failed Requests", results["failed_requests"]])

            # Write performance summary
            writer.writerow(["Average RPS", f"{results['requests_per_second']:.2f}"])
            writer.writerow(["Peak RPS", f"{results['max_rps']:.2f}"])

            # Write response time statistics
            if "response_times" in results:
                rt = results["response_times"]
                writer.writerow(
                    ["Minimum Response Time (ms)", f"{rt['min'] * 1000:.2f}"]
                )
                writer.writerow(
                    ["Average Response Time (ms)", f"{rt['avg'] * 1000:.2f}"]
                )
                writer.writerow(
                    ["Maximum Response Time (ms)", f"{rt['max'] * 1000:.2f}"]
                )
                writer.writerow(
                    ["Median Response Time (ms)", f"{rt['median'] * 1000:.2f}"]
                )
                writer.writerow(["90th Percentile (ms)", f"{rt['p90'] * 1000:.2f}"])
                writer.writerow(["95th Percentile (ms)", f"{rt['p95'] * 1000:.2f}"])
                writer.writerow(["99th Percentile (ms)", f"{rt['p99'] * 1000:.2f}"])
                writer.writerow(
                    ["Response Time Std Dev (ms)", f"{rt['std_dev'] * 1000:.2f}"]
                )

            # Write status codes
            writer.writerow([""])
            writer.writerow(["Status Codes", "Count"])
            for code, count in sorted(results["status_codes"].items()):
                writer.writerow([code, count])

            # Write errors
            writer.writerow([""])
            writer.writerow(["Error Types", "Count"])
            for error, count in sorted(results["errors"].items()):
                writer.writerow([error, count])

    def _save_detailed_results(self, history: List[Dict[str, Any]]) -> None:
        """
        Save detailed results to a CSV file.

        Args:
            history: List of historical data points
        """
        filename = self.config.get_output_filename("csv").replace(
            ".csv", "_detailed.csv"
        )

        with open(filename, "w", newline="") as csvfile:
            # Get all possible status codes and error types
            all_status_codes = set()
            all_error_types = set()

            for point in history:
                if "status_codes" in point:
                    all_status_codes.update(point["status_codes"].keys())

                if "errors" in point:
                    all_error_types.update(point.get("errors", {}).keys())

            # Create field names
            fieldnames = [
                "timestamp",
                "active_users",
                "completed_requests",
                "rps",
                "avg_response_time",
                "progress",
            ]

            # Add status code fields
            for code in sorted(all_status_codes):
                fieldnames.append(f"status_{code}")

            # Add error type fields
            for error in sorted(all_error_types):
                fieldnames.append(f"error_{error}")

            # Create writer and write header
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Write data
            for point in history:
                row = {
                    "timestamp": point.get("timestamp", 0),
                    "active_users": point.get("active_users", 0),
                    "completed_requests": point.get("completed_requests", 0),
                    "rps": point.get("rps", 0),
                    "avg_response_time": point.get("avg_response_time", 0)
                    * 1000,  # Convert to ms
                    "progress": point.get("progress", 0),
                }

                # Add status code counts
                for code in all_status_codes:
                    row[f"status_{code}"] = point.get("status_codes", {}).get(code, 0)

                # Add error counts
                for error in all_error_types:
                    row[f"error_{error}"] = point.get("errors", {}).get(error, 0)

                writer.writerow(row)

    def _save_metrics_data(self) -> None:
        """Save metrics data collected during the test"""
        filename = self.config.get_output_filename("csv").replace(
            ".csv", "_metrics.csv"
        )

        with open(filename, "w", newline="") as csvfile:
            fieldnames = [
                "timestamp",
                "active_users",
                "completed_requests",
                "current_rps",
                "avg_response_time",
                "progress_pct",
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for point in self.metrics_data:
                writer.writerow(point)
