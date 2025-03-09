"""
Console Reporter Module

This module implements a reporter that displays results in the console.
"""

import time
import sys
from typing import Dict, Any

from reporters.base import BaseReporter
from config.settings import LoadTestConfig


class ConsoleReporter(BaseReporter):
    """Reporter that displays results in the console"""
    
    def __init__(self, config: LoadTestConfig):
        """
        Initialize the console reporter.
        
        Args:
            config: The test configuration
        """
        super().__init__(config)
        self.start_time = None
        self.progress_shown = False
    
    async def report_start(self, config: LoadTestConfig) -> None:
        """
        Report the start of the test.
        
        Args:
            config: The test configuration
        """
        self.start_time = time.time()
        
        print("\n" + "=" * 80)
        print(f"LOAD TEST STARTED: {config.url}")
        print(f"Mode: {config.mode.upper()}, Users: {config.num_users}")
        
        if config.mode == "loop":
            print(f"Duration: {config.duration} seconds, Ramp-up: {config.ramp_up} seconds")
        else:
            print(f"Requests per user: {config.requests_per_user}, Ramp-up: {config.ramp_up} seconds")
        
        print(f"Protocol: {config.protocol.upper()}")
        print(f"Scenario: {config.scenario.upper()}")
        
        print("=" * 80 + "\n")
    
    async def report_progress(self, progress: Dict[str, Any]) -> None:
        """
        Report test progress.
        
        Args:
            progress: Dictionary with progress information
        """
        self.progress_shown = True
        
        # Format for status line
        status_format = "{elapsed:5.1f}s | {users:3d} users | {reqs:5d} reqs | {rps:6.1f} req/s | {rt:6.1f} ms avg | {status}"
        
        # Create progress bar
        bar_length = 30
        bar_filled = int(bar_length * progress['progress_pct'] / 100)
        bar = f"[{'#' * bar_filled}{' ' * (bar_length - bar_filled)}]"
        
        # Format status line
        status_line = status_format.format(
            elapsed=progress['elapsed'],
            users=progress['active_users'],
            reqs=progress['completed_requests'],
            rps=progress['current_rps'],
            rt=progress['avg_response_time'] * 1000,  # Convert to ms
            status=bar
        )
        
        # Print status with carriage return
        print(f"\r{status_line}", end="", flush=True)
    
    async def report(self, results: Dict[str, Any]) -> None:
        """
        Report test results.
        
        Args:
            results: Dictionary with test results
        """
        # Print a newline if we were showing progress
        if self.progress_shown:
            print("\n")
        
        print("\n" + "=" * 80)
        print("LOAD TEST RESULTS")
        print("=" * 80)
        
        # Basic information
        print(f"\nURL: {self.config.url}")
        print(f"Protocol: {self.config.protocol.upper()}")
        print(f"Mode: {self.config.mode.upper()}")
        print(f"Users: {self.config.num_users}")
        print(f"Duration: {results['duration']:.2f} seconds")
        print(f"Requests Completed: {results['total_requests']}")
        
        if results['total_requests'] > 0:
            success_rate = (results['successful_requests'] / results['total_requests']) * 100
            failure_rate = (results['failed_requests'] / results['total_requests']) * 100
            print(f"Successful Requests: {results['successful_requests']} ({success_rate:.1f}%)")
            print(f"Failed Requests: {results['failed_requests']} ({failure_rate:.1f}%)")
        
        # Performance summary
        print("\nPerformance Summary:")
        print(f"  - Average RPS: {results['requests_per_second']:.2f} requests/second")
        print(f"  - Peak RPS: {results['max_rps']:.2f} requests/second")
        
        # Response time statistics
        if 'response_times' in results:
            rt = results['response_times']
            print("\nResponse Times:")
            print(f"  - Minimum: {rt['min'] * 1000:.2f} ms")
            print(f"  - Average: {rt['avg'] * 1000:.2f} ms")
            print(f"  - Maximum: {rt['max'] * 1000:.2f} ms")
            print(f"  - Median (P50): {rt['median'] * 1000:.2f} ms")
            print(f"  - 90th Percentile: {rt['p90'] * 1000:.2f} ms")
            print(f"  - 95th Percentile: {rt['p95'] * 1000:.2f} ms")
            print(f"  - 99th Percentile: {rt['p99'] * 1000:.2f} ms")
            print(f"  - Standard Deviation: {rt['std_dev'] * 1000:.2f} ms")
        
        # Status codes
        if results['status_codes']:
            print("\nStatus Codes:")
            for code, count in sorted(results['status_codes'].items()):
                percentage = (count / max(1, results['total_requests'])) * 100
                print(f"  - {code}: {count} ({percentage:.1f}%)")
        
        # Errors
        if results['errors']:
            print("\nErrors:")
            for error, count in sorted(results['errors'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / max(1, results['total_requests'])) * 100
                print(f"  - {error}: {count} ({percentage:.1f}%)")
        else:
            print("\nNo errors reported")
        
        print("\n" + "=" * 80)