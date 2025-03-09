#!/usr/bin/env python3
"""
Terminal-Based Website Load Testing Tool - CLI Entry Point

This is the main entry point for the load testing tool when run from the command line.
"""

import asyncio
import sys
import platform
import argparse
from typing import Dict, Any, List, Optional

# Update these imports based on your actual file structure
from load_tester.config.settings import LoadTestConfig
from load_tester.core.load_tester import LoadTester
from load_tester.protocols.http import HttpProtocol
from load_tester.protocols.websocket import WebSocketProtocol
from load_tester.scenarios.simple import SimpleScenario
from load_tester.scenarios.workflow import WorkflowScenario
from load_tester.reporters.console import ConsoleReporter
from load_tester.reporters.csv import CsvReporter
from load_tester.reporters.json import JsonReporter
from load_tester.reporters.html import HtmlReporter
from load_tester.utils.logger import setup_logging


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Terminal-Based Website Load Testing Tool"
    )

    # URL configuration
    parser.add_argument("url", help="URL to test (e.g., https://example.com)")
    parser.add_argument(
        "--mode",
        choices=["exact", "paths", "default"],
        default="default",
        help="URL testing mode: exact=test only provided URL, paths=test custom paths, default=test default paths",
    )
    parser.add_argument(
        "--paths", nargs="+", help="Custom paths to test (used with --mode=paths)"
    )

    # User configuration
    parser.add_argument(
        "--users", "-u", type=int, default=10, help="Number of concurrent users"
    )
    parser.add_argument(
        "--test-mode",
        choices=["loop", "fixed"],
        default="loop",
        help="Test mode: loop=continuous requests for duration, fixed=fixed number of requests per user",
    )
    parser.add_argument(
        "--requests",
        "-r",
        type=int,
        default=10,
        help="Requests per user (for fixed mode)",
    )
    parser.add_argument(
        "--duration",
        "-d",
        type=int,
        default=30,
        help="Test duration in seconds (for loop mode)",
    )

    # Timing configuration
    parser.add_argument(
        "--ramp-up", type=int, default=5, help="Ramp-up time in seconds"
    )
    parser.add_argument(
        "--timeout", type=int, default=10, help="Request timeout in seconds"
    )
    parser.add_argument(
        "--think-min", type=float, default=1, help="Minimum think time between requests"
    )
    parser.add_argument(
        "--think-max", type=float, default=5, help="Maximum think time between requests"
    )

    # Connection configuration
    parser.add_argument(
        "--connections-per-host",
        type=int,
        default=100,
        help="Maximum connections per host",
    )
    parser.add_argument(
        "--max-connections", type=int, default=10000, help="Maximum total connections"
    )

    # Protocol options
    parser.add_argument(
        "--protocol",
        choices=["http", "websocket"],
        default="http",
        help="Protocol to use for testing",
    )

    # Scenario options
    parser.add_argument(
        "--scenario",
        choices=["simple", "workflow"],
        default="simple",
        help="Test scenario type",
    )
    parser.add_argument(
        "--workflow-file",
        help="JSON file defining the workflow steps (for workflow scenario)",
    )

    # Authentication
    parser.add_argument(
        "--auth-type",
        choices=["none", "basic", "bearer", "custom"],
        default="none",
        help="Authentication type",
    )
    parser.add_argument("--auth-username", help="Username for basic auth")
    parser.add_argument("--auth-password", help="Password for basic auth")
    parser.add_argument("--auth-token", help="Token for bearer auth")
    parser.add_argument("--auth-header", help="Custom auth header (name:value)")

    # Headers and cookies
    parser.add_argument(
        "--headers", nargs="+", help="Custom headers as name:value pairs"
    )
    parser.add_argument(
        "--cookies", nargs="+", help="Custom cookies as name=value pairs"
    )

    # Payload options
    parser.add_argument(
        "--request-method",
        default="GET",
        choices=["GET", "POST", "PUT", "DELETE", "PATCH"],
        help="HTTP method to use",
    )
    parser.add_argument("--payload-file", help="File containing the request payload")
    parser.add_argument("--payload", help="Request payload string")
    parser.add_argument(
        "--content-type",
        default="application/json",
        help="Content type for the request payload",
    )

    # Output options
    parser.add_argument(
        "--output-format",
        choices=["console", "csv", "json", "html", "all"],
        default="console",
        help="Output format",
    )
    parser.add_argument("--output-file", help="Output file name (without extension)")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # Response validation
    parser.add_argument("--validate-status", type=int, help="Expected HTTP status code")
    parser.add_argument("--validate-text", help="Text that should appear in responses")
    parser.add_argument(
        "--validate-regex", help="Regex pattern that response should match"
    )
    parser.add_argument(
        "--validate-json-path", help="JSONPath expression to validate in response"
    )
    parser.add_argument(
        "--validate-json-value", help="Expected value for JSONPath expression"
    )

    # Rate limiting
    parser.add_argument("--rate-limit", type=int, help="Maximum requests per second")

    return parser.parse_args()


def create_config_from_args(args: argparse.Namespace) -> LoadTestConfig:
    """Create configuration object from command-line arguments"""
    config = LoadTestConfig()

    # Base configuration
    config.url = args.url
    config.num_users = args.users
    config.mode = args.test_mode
    config.requests_per_user = args.requests
    config.duration = args.duration
    config.ramp_up = args.ramp_up
    config.timeout = args.timeout
    config.think_time_min = args.think_min
    config.think_time_max = args.think_max
    config.connections_per_host = args.connections_per_host
    config.max_connections = args.max_connections
    config.verbose = args.verbose

    # URL mode configuration
    config.url_mode = args.mode
    config.url_paths = args.paths

    # Protocol configuration
    config.protocol = args.protocol

    # Scenario configuration
    config.scenario = args.scenario
    config.workflow_file = args.workflow_file

    # Authentication configuration
    config.auth_type = args.auth_type
    config.auth_username = args.auth_username
    config.auth_password = args.auth_password
    config.auth_token = args.auth_token
    config.auth_header = args.auth_header

    # Headers and cookies
    config.headers = parse_key_value_pairs(args.headers) if args.headers else {}
    config.cookies = (
        parse_key_value_pairs(args.cookies, delimiter="=") if args.cookies else {}
    )

    # Payload configuration
    config.request_method = args.request_method
    config.payload_file = args.payload_file
    config.payload = args.payload
    config.content_type = args.content_type

    # Output configuration
    config.output_format = args.output_format
    config.output_file = args.output_file

    # Validation configuration
    config.validate_status = args.validate_status
    config.validate_text = args.validate_text
    config.validate_regex = args.validate_regex
    config.validate_json_path = args.validate_json_path
    config.validate_json_value = args.validate_json_value

    # Rate limiting
    config.rate_limit = args.rate_limit

    return config


def parse_key_value_pairs(pairs: List[str], delimiter: str = ":") -> Dict[str, str]:
    """Parse a list of key-value pairs into a dictionary"""
    result = {}
    if not pairs:
        return result

    for pair in pairs:
        if delimiter in pair:
            key, value = pair.split(delimiter, 1)
            result[key.strip()] = value.strip()

    return result


def create_protocol(config: LoadTestConfig):
    """Create the appropriate protocol handler based on configuration"""
    if config.protocol == "websocket":
        return WebSocketProtocol(config)
    else:  # Default to HTTP
        return HttpProtocol(config)


def create_scenario(config: LoadTestConfig, protocol):
    """Create the appropriate scenario based on configuration"""
    if config.scenario == "workflow":
        return WorkflowScenario(config, protocol)
    else:  # Default to simple
        return SimpleScenario(config, protocol)


def create_reporters(config: LoadTestConfig) -> List:
    """Create reporters based on the output format configuration"""
    reporters = []

    if config.output_format in ["console", "all"]:
        reporters.append(ConsoleReporter(config))

    if config.output_format in ["csv", "all"]:
        reporters.append(CsvReporter(config))

    if config.output_format in ["json", "all"]:
        reporters.append(JsonReporter(config))

    if config.output_format in ["html", "all"]:
        reporters.append(HtmlReporter(config))

    return reporters


async def run_load_test(config: LoadTestConfig) -> Dict[str, Any]:
    """Run the load test with the provided configuration"""
    # Create protocol handler
    protocol = create_protocol(config)

    # Create scenario
    scenario = create_scenario(config, protocol)

    # Create reporters
    reporters = create_reporters(config)

    # Create and run the load tester
    tester = LoadTester(config, scenario, reporters)
    results = await tester.run()

    return results


def main() -> int:
    """Main entry point for the script"""
    try:
        # Parse command-line arguments
        args = parse_arguments()

        # Set up logging
        setup_logging(verbose=args.verbose)

        # Create configuration
        config = create_config_from_args(args)

        # Print banner
        print("\n" + "=" * 80)
        print("TERMINAL-BASED WEBSITE LOAD TESTING TOOL")
        print("=" * 80)

        # Run the async main function
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        results = asyncio.run(run_load_test(config))

        # Exit cleanly
        return 0
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        return 1
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
