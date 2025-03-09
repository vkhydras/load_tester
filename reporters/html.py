"""
HTML Reporter Module

This module implements a reporter that saves results to HTML files with charts.
"""

import os
import time
import json
from typing import Dict, Any, List
from datetime import datetime

from reporters.base import BaseReporter
from config.settings import LoadTestConfig


class HtmlReporter(BaseReporter):
    """Reporter that saves results to HTML files with charts"""
    
    def __init__(self, config: LoadTestConfig):
        """
        Initialize the HTML reporter.
        
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
        print(f"HTML Reporter: Results will be saved to an HTML file")
    
    async def report_progress(self, progress: Dict[str, Any]) -> None:
        """
        Report test progress.
        
        Args:
            progress: Dictionary with progress information
        """
        # Store metrics data for later
        self.metrics_data.append({
            'timestamp': progress['elapsed'],
            'active_users': progress['active_users'],
            'completed_requests': progress['completed_requests'],
            'current_rps': progress['current_rps'],
            'avg_response_time': progress['avg_response_time'] * 1000,  # Convert to ms
            'progress_pct': progress['progress_pct']
        })
    
    async def report(self, results: Dict[str, Any]) -> None:
        """
        Report test results.
        
        Args:
            results: Dictionary with test results
        """
        # Create directory for HTML files if needed
        output_dir = os.path.dirname(self.config.get_output_filename('html'))
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Generate the HTML content
        html_content = self._generate_html_report(results)
        
        # Save the HTML file
        filename = self.config.get_output_filename('html')
        
        with open(filename, 'w') as f:
            f.write(html_content)
        
        print(f"HTML Reporter: Results saved to {filename}")
    
    def _generate_html_report(self, results: Dict[str, Any]) -> str:
        """
        Generate the HTML report content.
        
        Args:
            results: Dictionary with test results
            
        Returns:
            HTML content as a string
        """
        # Calculate success/failure rates
        success_rate = 0
        failure_rate = 0
        
        if results['total_requests'] > 0:
            success_rate = (results['successful_requests'] / results['total_requests']) * 100
            failure_rate = (results['failed_requests'] / results['total_requests']) * 100
        
        # Prepare data for charts
        rps_data = []
        response_time_data = []
        users_data = []
        
        # Use metrics_data if available, otherwise use history from results
        data_points = self.metrics_data if self.metrics_data else results.get('history', [])
        
        for point in data_points:
            timestamp = point.get('timestamp', 0)
            
            rps_data.append({
                'x': timestamp,
                'y': point.get('rps', point.get('current_rps', 0))
            })
            
            response_time_data.append({
                'x': timestamp,
                'y': point.get('avg_response_time', 0) * 1000  # Convert to ms if needed
            })
            
            users_data.append({
                'x': timestamp,
                'y': point.get('active_users', 0)
            })
        
        # Prepare status code and error data for pie charts
        status_data = []
        for status, count in results.get('status_codes', {}).items():
            status_data.append({
                'name': str(status),
                'value': count
            })
        
        error_data = []
        for error, count in results.get('errors', {}).items():
            error_data.append({
                'name': error,
                'value': count
            })
        
        # Convert data to JSON for embedding in HTML
        rps_json = json.dumps(rps_data)
        response_time_json = json.dumps(response_time_data)
        users_json = json.dumps(users_data)
        status_json = json.dumps(status_data)
        error_json = json.dumps(error_data)
        
        # Generate the HTML content
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Load Test Results - {self.config.url}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            margin-bottom: 20px;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        .card {{
            background: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }}
        .row {{
            display: flex;
            flex-wrap: wrap;
            margin: 0 -10px;
        }}
        .col {{
            flex: 1;
            padding: 0 10px;
            min-width: 300px;
        }}
        .stat {{
            text-align: center;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
            margin-bottom: 10px;
        }}
        .stat h2 {{
            margin: 0;
            font-size: 28px;
        }}
        .stat p {{
            margin: 5px 0 0;
            color: #666;
        }}
        .chart-container {{
            width: 100%;
            height: 300px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        table th, table td {{
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        table th {{
            background-color: #f2f2f2;
        }}
        .success {{
            color: #28a745;
        }}
        .error {{
            color: #dc3545;
        }}
    </style>
    <!-- Include Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>Load Test Results</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <div class="card">
            <h2>Test Configuration</h2>
            <div class="row">
                <div class="col">
                    <table>
                        <tr><th>URL</th><td>{self.config.url}</td></tr>
                        <tr><th>Protocol</th><td>{self.config.protocol.upper()}</td></tr>
                        <tr><th>Mode</th><td>{self.config.mode.upper()}</td></tr>
                        <tr><th>Users</th><td>{self.config.num_users}</td></tr>
                        <tr><th>Duration</th><td>{results['duration']:.2f} seconds</td></tr>
                    </table>
                </div>
                <div class="col">
                    <table>
                        <tr><th>Requests Per User</th><td>{self.config.requests_per_user}</td></tr>
                        <tr><th>Ramp-up Time</th><td>{self.config.ramp_up} seconds</td></tr>
                        <tr><th>Timeout</th><td>{self.config.timeout} seconds</td></tr>
                        <tr><th>Think Time</th><td>{self.config.think_time_min} - {self.config.think_time_max} seconds</td></tr>
                        <tr><th>Scenario</th><td>{self.config.scenario}</td></tr>
                    </table>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Performance Summary</h2>
            <div class="row">
                <div class="col">
                    <div class="stat">
                        <h2>{results['total_requests']}</h2>
                        <p>Total Requests</p>
                    </div>
                </div>
                <div class="col">
                    <div class="stat">
                        <h2 class="success">{results['successful_requests']}</h2>
                        <p>Successful ({success_rate:.1f}%)</p>
                    </div>
                </div>
                <div class="col">
                    <div class="stat">
                        <h2 class="error">{results['failed_requests']}</h2>
                        <p>Failed ({failure_rate:.1f}%)</p>
                    </div>
                </div>
                <div class="col">
                    <div class="stat">
                        <h2>{results['requests_per_second']:.2f}</h2>
                        <p>Requests/Second</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Response Time Statistics</h2>
            <div class="row">
                <div class="col">
                    <table>
                        <tr><th>Metric</th><th>Time (ms)</th></tr>
"""

        # Add response time statistics if available
        if 'response_times' in results:
            rt = results['response_times']
            html += f"""
                        <tr><td>Minimum</td><td>{rt['min'] * 1000:.2f}</td></tr>
                        <tr><td>Average</td><td>{rt['avg'] * 1000:.2f}</td></tr>
                        <tr><td>Maximum</td><td>{rt['max'] * 1000:.2f}</td></tr>
                        <tr><td>Median (P50)</td><td>{rt['median'] * 1000:.2f}</td></tr>
                        <tr><td>90th Percentile</td><td>{rt['p90'] * 1000:.2f}</td></tr>
                        <tr><td>95th Percentile</td><td>{rt['p95'] * 1000:.2f}</td></tr>
                        <tr><td>99th Percentile</td><td>{rt['p99'] * 1000:.2f}</td></tr>
                        <tr><td>Standard Deviation</td><td>{rt['std_dev'] * 1000:.2f}</td></tr>
"""
        
        html += f"""
                    </table>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Charts</h2>
            
            <h3>Requests Per Second</h3>
            <div class="chart-container">
                <canvas id="rpsChart"></canvas>
            </div>
            
            <h3>Response Time</h3>
            <div class="chart-container">
                <canvas id="responseTimeChart"></canvas>
            </div>
            
            <h3>Active Users</h3>
            <div class="chart-container">
                <canvas id="usersChart"></canvas>
            </div>
            
            <div class="row">
                <div class="col">
                    <h3>Status Codes</h3>
                    <div class="chart-container">
                        <canvas id="statusChart"></canvas>
                    </div>
                </div>
                <div class="col">
                    <h3>Errors</h3>
                    <div class="chart-container">
                        <canvas id="errorChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Status Codes</h2>
            <table>
                <tr><th>Status Code</th><th>Count</th><th>Percentage</th></tr>
"""

        # Add status code data
        for status, count in sorted(results.get('status_codes', {}).items()):
            percentage = (count / max(1, results['total_requests'])) * 100
            html += f"""
                <tr><td>{status}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>
"""

        html += f"""
            </table>
        </div>

        <div class="card">
            <h2>Errors</h2>
"""

        # Add error data
        if results.get('errors'):
            html += f"""
            <table>
                <tr><th>Error Type</th><th>Count</th><th>Percentage</th></tr>
"""
            
            for error, count in sorted(results.get('errors', {}).items()):
                percentage = (count / max(1, results['total_requests'])) * 100
                html += f"""
                <tr><td>{error}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>
"""
            
            html += f"""
            </table>
"""
        else:
            html += "<p>No errors reported</p>"

        html += f"""
        </div>
    </div>

    <script>
        // Function to create charts
        function createCharts() {{
            // RPS Chart
            const rpsCtx = document.getElementById('rpsChart').getContext('2d');
            new Chart(rpsCtx, {{
                type: 'line',
                data: {{
                    datasets: [{{
                        label: 'Requests Per Second',
                        data: {rps_json},
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1,
                        fill: false
                    }}]
                }},
                options: {{
                    scales: {{
                        x: {{
                            type: 'linear',
                            title: {{
                                display: true,
                                text: 'Time (seconds)'
                            }}
                        }},
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Requests Per Second'
                            }}
                        }}
                    }}
                }}
            }});

            // Response Time Chart
            const rtCtx = document.getElementById('responseTimeChart').getContext('2d');
            new Chart(rtCtx, {{
                type: 'line',
                data: {{
                    datasets: [{{
                        label: 'Response Time (ms)',
                        data: {response_time_json},
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1,
                        fill: false
                    }}]
                }},
                options: {{
                    scales: {{
                        x: {{
                            type: 'linear',
                            title: {{
                                display: true,
                                text: 'Time (seconds)'
                            }}
                        }},
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Response Time (ms)'
                            }}
                        }}
                    }}
                }}
            }});

            // Users Chart
            const usersCtx = document.getElementById('usersChart').getContext('2d');
            new Chart(usersCtx, {{
                type: 'line',
                data: {{
                    datasets: [{{
                        label: 'Active Users',
                        data: {users_json},
                        borderColor: 'rgb(54, 162, 235)',
                        tension: 0.1,
                        fill: false
                    }}]
                }},
                options: {{
                    scales: {{
                        x: {{
                            type: 'linear',
                            title: {{
                                display: true,
                                text: 'Time (seconds)'
                            }}
                        }},
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Active Users'
                            }}
                        }}
                    }}
                }}
            }});

            // Status Code Pie Chart
            const statusCtx = document.getElementById('statusChart').getContext('2d');
            new Chart(statusCtx, {{
                type: 'pie',
                data: {{
                    labels: {status_json}.map(item => item.name),
                    datasets: [{{
                        label: 'Status Codes',
                        data: {status_json}.map(item => item.value),
                        backgroundColor: [
                            'rgba(75, 192, 192, 0.6)',
                            'rgba(54, 162, 235, 0.6)',
                            'rgba(255, 206, 86, 0.6)',
                            'rgba(255, 99, 132, 0.6)',
                            'rgba(153, 102, 255, 0.6)'
                        ]
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            position: 'right',
                        }}
                    }}
                }}
            }});

            // Error Pie Chart
            const errorCtx = document.getElementById('errorChart').getContext('2d');
            const errorData = {error_json};
            
            if (errorData.length > 0) {{
                new Chart(errorCtx, {{
                    type: 'pie',
                    data: {{
                        labels: errorData.map(item => item.name),
                        datasets: [{{
                            label: 'Errors',
                            data: errorData.map(item => item.value),
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.6)',
                                'rgba(255, 159, 64, 0.6)',
                                'rgba(255, 205, 86, 0.6)',
                                'rgba(75, 192, 192, 0.6)',
                                'rgba(54, 162, 235, 0.6)'
                            ]
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{
                                position: 'right',
                            }}
                        }}
                    }}
                }});
            }} else {{
                document.getElementById('errorChart').getContext('2d').canvas.style.display = 'none';
                document.getElementById('errorChart').parentNode.innerHTML = '<p>No errors reported</p>';
            }}
        }}

        // Create the charts when the page loads
        window.addEventListener('load', createCharts);
    </script>
</body>
</html>
"""
        
        return html