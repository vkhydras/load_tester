"""
Workflow Scenario Module

This module implements multi-step workflow scenarios.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional

from .base import BaseScenario
from config.settings import LoadTestConfig
from protocols.base import BaseProtocol

logger = logging.getLogger('load_tester')


class WorkflowScenario(BaseScenario):
    """
    Workflow scenario that executes a series of steps.
    
    A workflow is a sequence of requests with dependencies between them,
    such as extracting data from one response to use in the next request.
    """
    
    def __init__(self, config: LoadTestConfig, protocol: BaseProtocol):
        """
        Initialize the workflow scenario.
        
        Args:
            config: The test configuration
            protocol: The protocol handler to use
        """
        super().__init__(config, protocol)
        
        # Initialize workflow steps
        self.workflow_steps = config.workflow_steps
        
        # Validate workflow
        if not self.workflow_steps:
            raise ValueError("No workflow steps defined")
        
        # Last results by user (for maintaining state across steps)
        self.user_states = {}
    
    async def execute(self, user_id: int) -> Dict[str, Any]:
        """
        Execute the workflow scenario for the given user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary containing the result of the last step in the workflow
        """
        # Get or create session
        session = await self.get_session(user_id)
        
        # Initialize user state if needed
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                'step_index': 0,
                'variables': {},
                'last_result': None
            }
        
        user_state = self.user_states[user_id]
        step_index = user_state['step_index']
        variables = user_state['variables']
        
        # Get the current step
        if step_index >= len(self.workflow_steps):
            # Reset to the beginning if we've completed the workflow
            step_index = 0
            
        step = self.workflow_steps[step_index]
        
        # Process the step
        url = self._process_template(step.get('url', self.config.url), variables)
        method = step.get('method', self.config.request_method)
        
        # Prepare additional request parameters
        request_kwargs = {
            'method': method
        }
        
        # Add payload if specified
        if 'payload' in step:
            payload = self._process_template(step['payload'], variables)
            content_type = step.get('content_type', self.config.content_type)
            
            request_kwargs['content_type'] = content_type
            
            if content_type == 'application/json':
                try:
                    # Try to convert string to JSON
                    json_data = json.loads(payload)
                    request_kwargs['json'] = json_data
                except json.JSONDecodeError:
                    # If not valid JSON, use as-is
                    request_kwargs['data'] = payload
            else:
                request_kwargs['data'] = payload
        
        # Add headers if specified
        if 'headers' in step:
            headers = {}
            for name, value in step['headers'].items():
                headers[name] = self._process_template(value, variables)
            
            request_kwargs['headers'] = headers
        
        # Add cookies if specified
        if 'cookies' in step:
            cookies = {}
            for name, value in step['cookies'].items():
                cookies[name] = self._process_template(value, variables)
            
            request_kwargs['cookies'] = cookies
        
        # Make the request
        result = await self.protocol.request(session, url, user_id, **request_kwargs)
        
        # Extract variables if specified
        if 'extract' in step and not result.get('is_error', False):
            await self._extract_variables(step['extract'], result, variables)
        
        # Check conditions if specified
        if 'conditions' in step:
            for condition in step['conditions']:
                await self._check_condition(condition, result, variables)
        
        # Determine next step
        next_step = step_index + 1
        
        # Handle conditional branching if specified
        if 'next_step' in step:
            if isinstance(step['next_step'], int):
                # Direct step number
                next_step = step['next_step']
            elif isinstance(step['next_step'], dict):
                # Conditional branching
                for condition, target in step['next_step'].items():
                    if self._evaluate_condition(condition, variables):
                        next_step = target
                        break
        
        # Ensure next step is within bounds
        next_step = next_step % len(self.workflow_steps)
        
        # Update user state
        user_state['step_index'] = next_step
        user_state['last_result'] = result
        
        return result
    
    def _process_template(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Process a template string with variables.
        
        Args:
            template: The template string
            variables: The variables to substitute
            
        Returns:
            The processed string
        """
        if not isinstance(template, str):
            return template
        
        # Replace ${variable} placeholders
        def replace_var(match):
            var_name = match.group(1)
            return str(variables.get(var_name, f"${{{var_name}}}"))
        
        return re.sub(r'\${(\w+)}', replace_var, template)
    
    async def _extract_variables(self, 
                                extract_config: Dict[str, Any], 
                                result: Dict[str, Any], 
                                variables: Dict[str, Any]) -> None:
        """
        Extract variables from the response.
        
        Args:
            extract_config: Configuration for variable extraction
            result: The request result
            variables: Dictionary to store extracted variables
        """
        import re
        
        # Get response body if available
        body = result.get('body') or result.get('response_data', '')
        
        # Convert binary data to string if needed
        if isinstance(body, bytes):
            try:
                body = body.decode('utf-8')
            except UnicodeDecodeError:
                # Can't decode as UTF-8, use hex representation
                body = body.hex()
        
        # Extract variables based on type
        for var_name, config in extract_config.items():
            if isinstance(config, str):
                # Simple string configuration, assume it's a JSONPath
                config = {'type': 'jsonpath', 'path': config}
            
            extract_type = config.get('type', 'jsonpath')
            
            if extract_type == 'jsonpath' and body:
                try:
                    from jsonpath_ng import parse
                    
                    # Parse the body as JSON
                    json_data = json.loads(body)
                    
                    # Extract using JSONPath
                    jsonpath_expr = parse(config['path'])
                    matches = [match.value for match in jsonpath_expr.find(json_data)]
                    
                    if matches:
                        variables[var_name] = matches[0]
                except (json.JSONDecodeError, Exception) as e:
                    logger.debug(f"JSONPath extraction error: {e}")
            
            elif extract_type == 'regex' and body:
                # Extract using regex
                pattern = re.compile(config['pattern'])
                match = pattern.search(body)
                
                if match:
                    if 'group' in config:
                        group = config['group']
                        if isinstance(group, int):
                            variables[var_name] = match.group(group)
                        else:
                            variables[var_name] = match.group(group)
                    else:
                        variables[var_name] = match.group(0)
            
            elif extract_type == 'header' and 'headers' in result:
                # Extract from headers
                header_name = config['name']
                if header_name in result['headers']:
                    variables[var_name] = result['headers'][header_name]
            
            elif extract_type == 'cookie' and 'cookies' in result:
                # Extract from cookies
                cookie_name = config['name']
                if cookie_name in result['cookies']:
                    variables[var_name] = result['cookies'][cookie_name]
            
            elif extract_type == 'status':
                # Extract status code
                variables[var_name] = result.get('status', 0)
    
    async def _check_condition(self, 
                              condition: Dict[str, Any], 
                              result: Dict[str, Any], 
                              variables: Dict[str, Any]) -> bool:
        """
        Check a condition against the result.
        
        Args:
            condition: Condition configuration
            result: The request result
            variables: Dictionary with variables
            
        Returns:
            True if condition is met, False otherwise
        """
        condition_type = condition.get('type', 'status')
        
        if condition_type == 'status':
            # Check status code
            expected = condition.get('value')
            actual = result.get('status')
            
            return self._compare_values(expected, actual, condition.get('operator', '=='))
        
        elif condition_type == 'content':
            # Check content
            expected = condition.get('value')
            content = result.get('body', '') or result.get('response_data', '')
            
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            
            operator = condition.get('operator', 'contains')
            
            if operator == 'contains':
                return expected in content
            elif operator == 'not_contains':
                return expected not in content
            elif operator == 'regex':
                pattern = re.compile(expected)
                return bool(pattern.search(content))
        
        elif condition_type == 'variable':
            # Check variable value
            var_name = condition.get('variable')
            expected = condition.get('value')
            actual = variables.get(var_name)
            
            return self._compare_values(expected, actual, condition.get('operator', '=='))
        
        return False
    
    def _evaluate_condition(self, condition_expr: str, variables: Dict[str, Any]) -> bool:
        """
        Evaluate a condition expression.
        
        Args:
            condition_expr: Condition expression
            variables: Dictionary with variables
            
        Returns:
            True if condition is met, False otherwise
        """
        # Replace variables in the expression
        expr = self._process_template(condition_expr, variables)
        
        # Simple case: variable name directly
        if expr in variables:
            return bool(variables[expr])
        
        # Comparison operators
        for op in ['==', '!=', '>=', '<=', '>', '<']:
            if op in expr:
                left, right = expr.split(op, 1)
                left = left.strip()
                right = right.strip()
                
                # Convert to appropriate types
                try:
                    left_val = self._convert_value(left, variables)
                    right_val = self._convert_value(right, variables)
                    
                    return self._compare_values(left_val, right_val, op)
                except Exception as e:
                    logger.debug(f"Condition evaluation error: {e}")
                    return False
        
        # Default case: evaluate as boolean
        try:
            return bool(eval(expr))
        except Exception:
            return False
    
    def _convert_value(self, value_str: str, variables: Dict[str, Any]) -> Any:
        """
        Convert a string value to an appropriate type.
        
        Args:
            value_str: String value
            variables: Dictionary with variables
            
        Returns:
            Converted value
        """
        # Check if it's a variable reference
        if value_str in variables:
            return variables[value_str]
        
        # Try numeric conversion
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass
        
        # Handle boolean values
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False
        
        # Handle null
        if value_str.lower() == 'null':
            return None
        
        # Default to string
        return value_str
    
    def _compare_values(self, left: Any, right: Any, operator: str) -> bool:
        """
        Compare two values using the specified operator.
        
        Args:
            left: Left operand
            right: Right operand
            operator: Comparison operator
            
        Returns:
            Comparison result
        """
        if operator == '==':
            return left == right
        elif operator == '!=':
            return left != right
        elif operator == '>':
            return left > right
        elif operator == '>=':
            return left >= right
        elif operator == '<':
            return left < right
        elif operator == '<=':
            return left <= right
        else:
            return False