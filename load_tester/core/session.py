"""
User Session Management Module

This module handles user session management during load tests.
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any, Optional

from load_tester.config.settings import LoadTestConfig

logger = logging.getLogger('load_tester')


class UserSession:
    """Represents a single user session during a load test"""
    
    def __init__(self, user_id: int, config: LoadTestConfig, protocol):
        """
        Initialize a user session.
        
        Args:
            user_id: Unique identifier for the user
            config: The test configuration
            protocol: The protocol handler to use
        """
        self.user_id = user_id
        self.config = config
        self.protocol = protocol
        self.session = None
        self.start_time = None
        self.request_count = 0
        self.variables = {}  # For storing session variables
        self.cookies = {}  # For storing session cookies
    
    async def initialize(self) -> None:
        """Initialize the user session"""
        self.start_time = time.time()
        self.session = await self.protocol.create_session(self.user_id)
    
    async def close(self) -> None:
        """Close the user session"""
        if self.session:
            try:
                # Handle different session types
                if hasattr(self.session, 'close') and callable(self.session.close):
                    if asyncio.iscoroutinefunction(self.session.close):
                        await self.session.close()
                    else:
                        self.session.close()
            except Exception as e:
                logger.warning(f"Error closing session for user {self.user_id}: {e}")
            
            self.session = None
    
    async def request(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make a request using this session.
        
        Args:
            url: The URL to request
            **kwargs: Additional request parameters
            
        Returns:
            Dictionary containing the result of the request
        """
        if not self.session:
            await self.initialize()
        
        self.request_count += 1
        
        # Merge session cookies with request cookies
        if 'cookies' in kwargs:
            kwargs['cookies'] = {**self.cookies, **kwargs['cookies']}
        else:
            kwargs['cookies'] = self.cookies
        
        # Make the request
        result = await self.protocol.request(self.session, url, self.user_id, **kwargs)
        
        # Store cookies from the response if available
        if 'cookies' in result:
            self.cookies.update(result['cookies'])
        
        return result
    
    def set_variable(self, name: str, value: Any) -> None:
        """
        Set a session variable.
        
        Args:
            name: Variable name
            value: Variable value
        """
        self.variables[name] = value
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """
        Get a session variable.
        
        Args:
            name: Variable name
            default: Default value if variable doesn't exist
            
        Returns:
            Variable value or default
        """
        return self.variables.get(name, default)
    
    def replace_variables(self, text: str) -> str:
        """
        Replace variables in text with their values.
        
        Args:
            text: Text with variable placeholders
            
        Returns:
            Text with variables replaced
        """
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            return str(self.get_variable(var_name, f"${{{var_name}}}"))
        
        return re.sub(r'\${(\w+)}', replace_var, text)


class SessionManager:
    """Manages user sessions during a load test"""
    
    def __init__(self, config: LoadTestConfig, protocol):
        """
        Initialize the session manager.
        
        Args:
            config: The test configuration
            protocol: The protocol handler to use
        """
        self.config = config
        self.protocol = protocol
        self.sessions = {}
        self._lock = asyncio.Lock()
    
    async def get_session(self, user_id: int) -> UserSession:
        """
        Get or create a session for the given user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            UserSession for the user
        """
        async with self._lock:
            if user_id not in self.sessions:
                self.sessions[user_id] = UserSession(user_id, self.config, self.protocol)
                await self.sessions[user_id].initialize()
            
            return self.sessions[user_id]
    
    async def close_all(self) -> None:
        """Close all sessions"""
        close_tasks = []
        
        for user_id, session in self.sessions.items():
            close_tasks.append(session.close())
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.sessions.clear()