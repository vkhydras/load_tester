"""
Logging Utilities Module

This module provides logging configuration and utilities.
"""

import logging
import sys
import os
from typing import Optional
from datetime import datetime


def setup_logging(log_file: Optional[str] = None, verbose: bool = False) -> None:
    """
    Set up logging for the application.
    
    Args:
        log_file: Path to the log file, or None to use a default name
        verbose: Enable verbose logging
    """
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"load_test_{timestamp}.log"
    
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set log level based on verbose flag
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Get the main logger
    logger = logging.getLogger('load_tester')
    
    logger.info("Logging initialized")
    
    if verbose:
        logger.debug("Verbose logging enabled")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f'load_tester.{name}')