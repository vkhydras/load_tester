"""
Core Load Tester Module

This module contains the main LoadTester class that orchestrates the load testing process.
"""

import asyncio
import time
import signal
import logging
from typing import Dict, List, Any, Optional, Callable

from config.settings import LoadTestConfig
from core.metrics import MetricsCollector

logger = logging.getLogger("load_tester")


class LoadTester:
    """Main load tester orchestration class"""

    def __init__(self, config: LoadTestConfig, scenario, reporters):
        """
        Initialize the load tester with configuration and components.

        Args:
            config: The test configuration
            scenario: The test scenario to run
            reporters: List of reporters for output
        """
        self.config = config
        self.scenario = scenario
        self.reporters = reporters

        # Test control
        self.test_running = False
        self.start_time = None

        # Metrics
        self.metrics = MetricsCollector()

        # Internal state
        self._tasks = []
        self._lock = asyncio.Lock()

    async def run(self) -> Dict[str, Any]:
        """
        Run the load test.

        Returns:
            Dict containing test results
        """
        logger.info(f"Starting load test for {self.config.url}")

        self.test_running = True
        self.start_time = time.time()

        # Register signal handlers
        self._setup_signal_handlers()

        try:
            # Create user tasks
            user_tasks = [
                self._run_user_session(user_id)
                for user_id in range(1, self.config.num_users + 1)
            ]

            # Create progress monitoring task
            progress_task = asyncio.create_task(self._monitor_progress())

            # Create metrics collection task
            metrics_task = asyncio.create_task(self._collect_metrics())

            # Store all tasks for potential cancellation
            self._tasks = user_tasks + [progress_task, metrics_task]

            # Run user sessions
            await asyncio.gather(*user_tasks, return_exceptions=True)

            # Ensure metrics are finalized
            await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error during test execution: {e}")
            raise
        finally:
            # Ensure test is marked as completed
            self.test_running = False

            # Cancel monitoring tasks
            await self._cancel_monitoring_tasks()

            # Reset signal handlers
            self._reset_signal_handlers()

        # Generate and return test results
        results = self.metrics.get_results()

        # Report results through all reporters
        for reporter in self.reporters:
            await reporter.report(results)

        return results

    async def _run_user_session(self, user_id: int) -> None:
        """
        Run a single user session.

        Args:
            user_id: Unique identifier for the user
        """
        # Calculate start delay based on ramp-up time
        if self.config.ramp_up > 0:
            delay = (user_id / self.config.num_users) * self.config.ramp_up
            await asyncio.sleep(delay)

        # Register the user as active
        async with self._lock:
            self.metrics.increment_active_users()

        try:
            # Run the appropriate type of session
            if self.config.mode == "loop":
                await self._run_loop_mode_session(user_id)
            else:  # "fixed" mode
                await self._run_fixed_mode_session(user_id)
        finally:
            # Unregister the user
            async with self._lock:
                self.metrics.decrement_active_users()

    async def _run_loop_mode_session(self, user_id: int) -> None:
        """
        Run a continuous loop session until the test duration is reached.

        Args:
            user_id: Unique identifier for the user
        """
        # Continue until the test duration is reached
        while (
            time.time() - self.start_time < self.config.duration and self.test_running
        ):
            # Execute the scenario
            result = await self.scenario.execute(user_id)

            # Record the result
            self.metrics.record_result(result)

            # Apply rate limiting if configured
            if self.config.rate_limit:
                await self._apply_rate_limiting()

            # Simulate user think time
            think_time = self._calculate_think_time()
            await asyncio.sleep(think_time)

    async def _run_fixed_mode_session(self, user_id: int) -> None:
        """
        Run a session with a fixed number of requests.

        Args:
            user_id: Unique identifier for the user
        """
        # Make a fixed number of requests
        for req_num in range(self.config.requests_per_user):
            if not self.test_running:
                break

            # Execute the scenario
            result = await self.scenario.execute(user_id)

            # Record the result
            self.metrics.record_result(result)

            # Apply rate limiting if configured
            if self.config.rate_limit:
                await self._apply_rate_limiting()

            # Simulate user think time (except for the last request)
            if req_num < self.config.requests_per_user - 1:
                think_time = self._calculate_think_time()
                await asyncio.sleep(think_time)

    async def _apply_rate_limiting(self) -> None:
        """Apply rate limiting based on configuration"""
        if not self.config.rate_limit:
            return

        # Get current RPS
        current_rps = self.metrics.get_current_rps()

        # If we're exceeding the limit, delay the next request
        if current_rps > self.config.rate_limit:
            delay = (current_rps - self.config.rate_limit) / self.config.rate_limit
            await asyncio.sleep(delay)

    def _calculate_think_time(self) -> float:
        """Calculate random think time based on configuration"""
        import random

        return random.uniform(self.config.think_time_min, self.config.think_time_max)

    async def _monitor_progress(self) -> None:
        """Monitor and display test progress"""
        try:
            # Report initial state
            for reporter in self.reporters:
                await reporter.report_start(self.config)

            # Update progress periodically
            while self.test_running:
                # Calculate progress
                progress = self._calculate_progress()

                # Report progress
                for reporter in self.reporters:
                    await reporter.report_progress(progress)

                # Wait before next update
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            # Normal cancellation
            pass
        except Exception as e:
            logger.error(f"Error in progress monitoring: {e}")

    async def _collect_metrics(self) -> None:
        """Collect and update metrics periodically"""
        try:
            while self.test_running:
                # Update metrics
                self.metrics.update_periodic_metrics()

                # Wait before next update
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            # Normal cancellation
            pass
        except Exception as e:
            logger.error(f"Error in metrics collection: {e}")

    def _calculate_progress(self) -> Dict[str, Any]:
        """Calculate test progress"""
        elapsed = time.time() - self.start_time

        if self.config.mode == "loop":
            # Loop mode: progress based on time
            progress_pct = min(100, (elapsed / self.config.duration) * 100)
            remaining = max(0, self.config.duration - elapsed)
            status = f"Time-based: {progress_pct:.1f}% complete"
        else:
            # Fixed mode: progress based on completed requests
            total_requests = self.config.num_users * self.config.requests_per_user
            completed = self.metrics.get_completed_requests()
            progress_pct = min(100, (completed / total_requests) * 100)

            # Estimate remaining time
            if completed > 0 and elapsed > 0:
                requests_per_second = completed / elapsed
                remaining_requests = total_requests - completed
                remaining = (
                    remaining_requests / requests_per_second
                    if requests_per_second > 0
                    else 0
                )
            else:
                remaining = 0

            status = f"Request-based: {progress_pct:.1f}% complete ({completed}/{total_requests})"

        return {
            "elapsed": elapsed,
            "progress_pct": progress_pct,
            "remaining": remaining,
            "status": status,
            "active_users": self.metrics.get_active_users(),
            "completed_requests": self.metrics.get_completed_requests(),
            "current_rps": self.metrics.get_current_rps(),
            "avg_response_time": self.metrics.get_avg_response_time(),
            "errors": self.metrics.get_error_count(),
        }

    async def _cancel_monitoring_tasks(self) -> None:
        """Cancel all monitoring tasks"""
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error canceling task: {e}")

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown"""
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._handle_shutdown)
            except NotImplementedError:
                # Windows doesn't support SIGTERM
                pass

    def _reset_signal_handlers(self) -> None:
        """Reset signal handlers to default"""
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.remove_signal_handler(sig)
            except NotImplementedError:
                # Windows doesn't support SIGTERM
                pass

    def _handle_shutdown(self) -> None:
        """Handle shutdown signals (Ctrl+C)"""
        if not self.test_running:
            return

        print("\nShutting down test gracefully. Please wait...")
        self.test_running = False
