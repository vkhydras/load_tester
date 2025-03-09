"""
Validators Module

This module provides validation functions for inputs and configurations.
"""

import re
import os
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from urllib.parse import urlparse

from config.settings import LoadTestConfig


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a URL.
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"
    
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False, "URL must include scheme (http:// or https://) and hostname"
        
        if parsed.scheme not in ['http', 'https', 'ws', 'wss']:
            return False, "URL scheme must be http, https, ws, or wss"
        
        return True, None
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def validate_config(config: LoadTestConfig) -> Tuple[bool, Optional[str]]:
    """
    Validate the load test configuration.
    
    Args:
        config: The configuration to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate URL
    url_valid, url_error = validate_url(config.url)
    if not url_valid:
        return False, url_error
    
    # Validate user count
    if config.num_users <= 0:
        return False, "Number of users must be greater than zero"
    
    # Validate requests per user (for fixed mode)
    if config.mode == "fixed" and config.requests_per_user <= 0:
        return False, "Requests per user must be greater than zero"
    
    # Validate duration (for loop mode)
    if config.mode == "loop" and config.duration <= 0:
        return False, "Duration must be greater than zero"
    
    # Validate ramp-up time
    if config.ramp_up < 0:
        return False, "Ramp-up time cannot be negative"
    
    # Validate timeout
    if config.timeout <= 0:
        return False, "Timeout must be greater than zero"
    
    # Validate think time
    if config.think_time_min < 0:
        return False, "Minimum think time cannot be negative"
    if config.think_time_max < config.think_time_min:
        return False, "Maximum think time must be greater than or equal to minimum think time"
    
    # Validate rate limit
    if config.rate_limit is not None and config.rate_limit <= 0:
        return False, "Rate limit must be greater than zero"
    
    # Validate workflow file
    if config.scenario == "workflow" and not config.workflow_steps:
        if not config.workflow_file:
            return False, "Workflow file must be specified for workflow scenario"
        
        if not os.path.exists(config.workflow_file):
            return False, f"Workflow file not found: {config.workflow_file}"
        
        try:
            with open(config.workflow_file, 'r') as f:
                workflow = json.load(f)
            
            if not isinstance(workflow, list) or not workflow:
                return False, "Workflow file must contain a non-empty list of steps"
            
            for step in workflow:
                if not isinstance(step, dict):
                    return False, "Each workflow step must be a dictionary"
                
                if 'url' not in step and config.url_mode == "exact":
                    return False, "Each workflow step must include a URL"
            
        except json.JSONDecodeError:
            return False, f"Invalid JSON in workflow file: {config.workflow_file}"
        except Exception as e:
            return False, f"Error reading workflow file: {str(e)}"
    
    # Validate payload file
    if config.payload_file and not os.path.exists(config.payload_file):
        return False, f"Payload file not found: {config.payload_file}"
    
    # Validate authentication
    if config.auth_type == "basic" and (not config.auth_username or not config.auth_password):
        return False, "Basic authentication requires username and password"
    
    if config.auth_type == "bearer" and not config.auth_token:
        return False, "Bearer authentication requires a token"
    
    if config.auth_type == "custom" and not config.auth_header:
        return False, "Custom authentication requires an authentication header"
    
    # Everything looks good
    return True, None


def validate_json_path(path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a JSONPath expression.
    
    Args:
        path: JSONPath expression to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "JSONPath cannot be empty"
    
    # Basic validation - check for balanced brackets and quotes
    brackets = {'[': ']', '{': '}'}
    quotes = {'"': '"', "'": "'"}
    
    stack = []
    in_quote = None
    
    for char in path:
        if in_quote:
            if char == in_quote:
                in_quote = None
        else:
            if char in quotes:
                in_quote = quotes[char]
            elif char in brackets:
                stack.append(brackets[char])
            elif char in brackets.values():
                if not stack or stack.pop() != char:
                    return False, "Unbalanced brackets in JSONPath"
    
    if in_quote:
        return False, "Unbalanced quotes in JSONPath"
    
    if stack:
        return False, "Unbalanced brackets in JSONPath"
    
    return True, None


def validate_regex(pattern: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a regular expression pattern.
    
    Args:
        pattern: Regex pattern to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not pattern:
        return False, "Regex pattern cannot be empty"
    
    try:
        re.compile(pattern)
        return True, None
    except re.error as e:
        return False, f"Invalid regex pattern: {str(e)}"