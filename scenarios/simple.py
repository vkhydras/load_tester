"""
Simple Scenario Module

This module implements a simple URL request scenario.
"""

from typing import Dict, Any

# Change the import to use relative imports
from .base import BaseScenario
# If you're not using the package structure, use this instead:
# from scenarios.base import BaseScenario

# These imports should also be relative or package-based
from config.settings import LoadTestConfig
from protocols.base import BaseProtocol


class SimpleScenario(BaseScenario):
    """Simple scenario that makes requests to target URLs"""
    
    def __init__(self, config: LoadTestConfig, protocol: BaseProtocol):
        """
        Initialize the simple scenario.
        
        Args:
            config: The test configuration
            protocol: The protocol handler to use
        """
        super().__init__(config, protocol)
    
    async def execute(self, user_id: int) -> Dict[str, Any]:
        """
        Execute the scenario for the given user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary containing the result of the execution
        """
        # Get or create session
        session = await self.get_session(user_id)
        
        # Select target URL
        url = self.select_target_url()
        
        # Make request
        result = await self.protocol.request(session, url, user_id)
        
        return result