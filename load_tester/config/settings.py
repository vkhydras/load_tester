"""
Configuration Module for Load Tester

This module defines the configuration class for the load testing tool.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse


@dataclass
class LoadTestConfig:
    """Configuration for the load testing tool"""
    
    # URL configuration
    url: str = ""
    url_mode: str = "default"  # "exact", "paths", or "default"
    url_paths: Optional[List[str]] = None
    
    # Test parameters
    num_users: int = 10
    mode: str = "loop"  # "loop" or "fixed"
    requests_per_user: int = 10
    duration: int = 30
    ramp_up: int = 5
    timeout: int = 10
    think_time_min: float = 1.0
    think_time_max: float = 5.0
    connections_per_host: int = 100
    max_connections: int = 10000
    
    # Protocol configuration
    protocol: str = "http"  # "http" or "websocket"
    
    # Scenario configuration
    scenario: str = "simple"  # "simple" or "workflow"
    workflow_file: Optional[str] = None
    workflow_steps: List[Dict[str, Any]] = field(default_factory=list)
    
    # Authentication
    auth_type: str = "none"  # "none", "basic", "bearer", or "custom"
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    auth_token: Optional[str] = None
    auth_header: Optional[str] = None
    
    # Request configuration
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    request_method: str = "GET"
    payload: Optional[str] = None
    payload_file: Optional[str] = None
    content_type: str = "application/json"
    
    # Output configuration
    output_format: str = "console"  # "console", "csv", "json", "html", or "all"
    output_file: Optional[str] = None
    verbose: bool = False
    
    # Validation configuration
    validate_status: Optional[int] = None
    validate_text: Optional[str] = None
    validate_regex: Optional[str] = None
    validate_json_path: Optional[str] = None
    validate_json_value: Optional[str] = None
    
    # Rate limiting
    rate_limit: Optional[int] = None
    
    def __post_init__(self):
        """Perform post-initialization validations and computations"""
        # Load workflow if specified
        if self.workflow_file and self.scenario == "workflow":
            self._load_workflow()
            
        # Load payload if specified
        if self.payload_file:
            self._load_payload()
            
        # Set default paths if needed
        if self.url_mode == "default" and not self.url_paths:
            self.url_paths = ["/", "/about", "/contact"]
            
        # Set user agent headers if not provided
        if "User-Agent" not in self.headers:
            self.headers["User-Agent"] = "LoadTester/1.0"
    
    def _load_workflow(self):
        """Load workflow steps from a JSON file"""
        if not os.path.exists(self.workflow_file):
            raise FileNotFoundError(f"Workflow file not found: {self.workflow_file}")
        
        try:
            with open(self.workflow_file, 'r') as f:
                self.workflow_steps = json.load(f)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in workflow file: {self.workflow_file}")
    
    def _load_payload(self):
        """Load payload from a file"""
        if not os.path.exists(self.payload_file):
            raise FileNotFoundError(f"Payload file not found: {self.payload_file}")
        
        try:
            with open(self.payload_file, 'r') as f:
                self.payload = f.read()
        except Exception as e:
            raise ValueError(f"Error reading payload file: {e}")
    
    def get_base_url(self) -> str:
        """Get the base URL (scheme + netloc)"""
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def get_target_urls(self) -> List[str]:
        """Get the list of URLs to test based on the configuration"""
        if self.url_mode == "exact":
            return [self.url]
        
        base_url = self.get_base_url()
        
        if self.url_paths:
            # Use custom paths
            return [f"{base_url}{path}" if path.startswith('/') else f"{base_url}/{path}" 
                    for path in self.url_paths]
        
        # Use default paths
        return [f"{base_url}/", f"{base_url}/about", f"{base_url}/contact"]
    
    def get_output_filename(self, extension: str) -> str:
        """Get the output filename with the given extension"""
        from datetime import datetime
        
        if self.output_file:
            base_name = self.output_file
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"load_test_results_{timestamp}"
        
        return f"{base_name}.{extension}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary"""
        return {k: v for k, v in self.__dict__.items() 
                if not k.startswith('_') and v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoadTestConfig':
        """Create a configuration from a dictionary"""
        return cls(**data)
    
    @classmethod
    def from_json_file(cls, filename: str) -> 'LoadTestConfig':
        """Load configuration from a JSON file"""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Configuration file not found: {filename}")
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in configuration file: {filename}")
    
    def save_to_json_file(self, filename: str) -> None:
        """Save configuration to a JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)