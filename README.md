# Website Load Testing Tool

A load testing tool for websites and web services. Run comprehensive load tests directly from your terminal without requiring a web browser or complex infrastructure.

## Features

- **Multiple Protocol Support**: Test HTTP, HTTPS, and WebSocket endpoints
- **Flexible Testing Scenarios**: Simple URL testing or complex multi-step workflows
- **Realistic User Simulation**: Configurable think times, ramp-up periods, and connection limiting
- **Rich Result Analysis**: Detailed performance metrics with percentiles and visualizations
- **Modular Architecture**: Easily extend with new protocols, scenarios, and reporters
- **Authentication Support**: Basic, Bearer token, or custom authentication methods
- **Request Customization**: Headers, cookies, content types, and payloads
- **Response Validation**: Verify status codes, content, JSON paths, and regex patterns
- **Multiple Output Formats**: Console, CSV, JSON, and HTML reports with charts
- **Rate Limiting**: Control request rates to simulate specific traffic patterns

## Installation

```bash
# Clone the repository
git clone https://github.com/vkhydras/load_tester.git
cd load-tester

# Install dependencies
pip install -r requirements.txt

# Install the package (development mode)
pip install -e .
```

## Quick Start

```bash
# Basic load test with 10 users for 30 seconds
load-tester https://example.com

# More complex test with custom configuration
load-tester https://example.com \
    --users 50 \
    --duration 120 \
    --ramp-up 30 \
    --mode paths \
    --paths / /products /about /contact \
    --output-format all \
    --output-file my_test_results
```

## Command-Line Options

### Basic Configuration

- `url`: Target URL to test (required)
- `--users`, `-u`: Number of concurrent users (default: 10)
- `--test-mode`: Test mode - `loop` (continuous) or `fixed` (set number of requests) (default: loop)
- `--duration`, `-d`: Test duration in seconds for loop mode (default: 30)
- `--requests`, `-r`: Requests per user for fixed mode (default: 10)
- `--ramp-up`: Ramp-up time in seconds (default: 5)
- `--verbose`, `-v`: Enable verbose logging

### URL Configuration

- `--mode`: URL testing mode - `exact`, `paths`, or `default` (default: default)
- `--paths`: Custom paths to test when using path mode (e.g., `/` `/products` `/about`)

### Protocol Options

- `--protocol`: Protocol to use - `http` or `websocket` (default: http)
- `--timeout`: Request timeout in seconds (default: 10)
- `--connections-per-host`: Maximum connections per host (default: 100)
- `--max-connections`: Maximum total connections (default: 10000)

### Advanced Request Options

- `--request-method`: HTTP method to use (default: GET)
- `--auth-type`: Authentication type - `none`, `basic`, `bearer`, or `custom` (default: none)
- `--auth-username`: Username for basic auth
- `--auth-password`: Password for basic auth
- `--auth-token`: Token for bearer auth
- `--auth-header`: Custom auth header (name:value)
- `--headers`: Custom headers as name:value pairs
- `--cookies`: Custom cookies as name=value pairs
- `--payload`: Request payload string
- `--payload-file`: File containing the request payload
- `--content-type`: Content type for request payload (default: application/json)

### Response Validation

- `--validate-status`: Expected HTTP status code
- `--validate-text`: Text that should appear in responses
- `--validate-regex`: Regex pattern that response should match
- `--validate-json-path`: JSONPath expression to validate in response
- `--validate-json-value`: Expected value for JSONPath expression

### Output Options

- `--output-format`: Output format - `console`, `csv`, `json`, `html`, or `all` (default: console)
- `--output-file`: Base output file name without extension

### Timing Configuration

- `--think-min`: Minimum think time between requests in seconds (default: 1)
- `--think-max`: Maximum think time between requests in seconds (default: 5)
- `--rate-limit`: Maximum requests per second (optional)

## Usage Examples

### Basic HTTP Load Test

```bash
load-tester https://example.com --users 20 --duration 60
```

### Testing Specific Pages

```bash
load-tester https://example.com --mode paths --paths / /products /cart /checkout
```

### POST Request with Authentication

```bash
load-tester https://api.example.com/login \
    --request-method POST \
    --content-type application/json \
    --payload '{"username": "test", "password": "test"}' \
    --auth-type basic \
    --auth-username apiuser \
    --auth-password apipass
```

### WebSocket Test

```bash
load-tester wss://ws.example.com/socket \
    --protocol websocket \
    --users 5 \
    --duration 60 \
    --payload '{"type": "subscribe", "channel": "updates"}'
```

### Response Validation

```bash
load-tester https://api.example.com/users \
    --validate-status 200 \
    --validate-json-path $.data[*].id \
    --validate-json-value 12345
```

### HTML Report Generation

```bash
load-tester https://example.com \
    --output-format html \
    --output-file my_load_test
```

## Multi-Step Workflow Testing

You can define complex test workflows as JSON files:

```json
[
  {
    "name": "Login",
    "url": "${base_url}/login",
    "method": "POST",
    "payload": {
      "username": "testuser",
      "password": "password123"
    },
    "extract": {
      "token": {
        "type": "jsonpath",
        "path": "$.token"
      }
    }
  },
  {
    "name": "Get Profile",
    "url": "${base_url}/profile",
    "method": "GET",
    "headers": {
      "Authorization": "Bearer ${token}"
    }
  },
  {
    "name": "Logout",
    "url": "${base_url}/logout",
    "method": "POST"
  }
]
```

Then run:

```bash
load-tester https://api.example.com \
    --scenario workflow \
    --workflow-file my_workflow.json
```

## Extending the Tool

The modular architecture makes it easy to extend:

1. Create new protocol handlers by extending `BaseProtocol`
2. Implement new test scenarios by extending `BaseScenario`
3. Add new output formats by creating new reporters
4. Customize metrics collection by extending `MetricsCollector`

## Requirements

- Python 3.7+
- aiohttp
- jsonpath-ng (for JSON validation)
