"""
Logging utilities for the Askaosus Matrix Bot.

This module provides custom logging functionality including:
- Custom LLM log level for LLM-specific outputs
- Logging configuration utilities
- Log filtering capabilities
"""

import logging
import sys
from pathlib import Path
from typing import Optional


# Define custom LLM log level (between INFO=20 and WARNING=30)
LLM_LEVEL = 25
LLM_LEVEL_NAME = 'LLM'


def add_llm_log_level():
    """Add the custom LLM log level to the logging module."""
    # Add the log level to the logging module
    logging.addLevelName(LLM_LEVEL, LLM_LEVEL_NAME)
    
    # Add the level as an attribute to the logging module
    setattr(logging, LLM_LEVEL_NAME, LLM_LEVEL)
    
    # Add a method to logger class for the new level
    def llm(self, message, *args, **kwargs):
        """Log a message with severity 'LLM'."""
        if self.isEnabledFor(LLM_LEVEL):
            self._log(LLM_LEVEL, message, args, **kwargs)
    
    # Add the method to Logger class
    logging.Logger.llm = llm


class MatrixNioFilter(logging.Filter):
    """Filter to exclude matrix-nio logs when needed."""
    
    def filter(self, record):
        """Filter out matrix-nio related log records."""
        # Exclude logs from nio and related matrix libraries
        excluded_loggers = [
            'nio',
            'nio.client',
            'nio.api',
            'nio.events',
            'nio.http',
            'nio.store',
            'aiohttp',
            'aiohttp.access',
            'urllib3'
        ]
        
        return not any(record.name.startswith(excluded) for excluded in excluded_loggers)


def configure_logging(log_level: str = 'INFO', 
                     logs_dir: str = '/app/logs',
                     exclude_matrix_nio: bool = False):
    """
    Configure logging with custom LLM level and optional matrix-nio filtering.
    
    Args:
        log_level: Base log level (DEBUG, INFO, WARNING, ERROR, LLM)
        logs_dir: Directory for log files
        exclude_matrix_nio: Whether to filter out matrix-nio logs
    """
    # Ensure custom LLM level is available
    add_llm_log_level()
    
    # Create logs directory if it doesn't exist
    Path(logs_dir).mkdir(exist_ok=True)
    
    # Determine numeric log level
    if log_level.upper() == 'LLM':
        numeric_level = LLM_LEVEL
    else:
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    file_handler = logging.FileHandler(f'{logs_dir}/bot.log')
    file_handler.setFormatter(formatter)
    
    # Apply matrix-nio filter if requested
    if exclude_matrix_nio:
        matrix_filter = MatrixNioFilter()
        console_handler.addFilter(matrix_filter)
        file_handler.addFilter(matrix_filter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add our handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure specific loggers for better control
    
    # LLM logger - always show LLM level logs
    llm_logger = logging.getLogger('src.llm')
    llm_logger.setLevel(min(numeric_level, LLM_LEVEL))
    
    # Bot logger  
    bot_logger = logging.getLogger('src.bot')
    bot_logger.setLevel(numeric_level)
    
    # If we want to suppress matrix-nio logs entirely, set their level higher
    if exclude_matrix_nio:
        matrix_loggers = ['nio', 'aiohttp', 'urllib3']
        for logger_name in matrix_loggers:
            logging.getLogger(logger_name).setLevel(logging.ERROR)


def get_llm_logger(name: str) -> logging.Logger:
    """
    Get a logger configured for LLM operations.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance with LLM level support
    """
    # Ensure custom level is available
    add_llm_log_level()
    
    return logging.getLogger(name)