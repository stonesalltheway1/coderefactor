#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logging utilities for CodeRefactor.
Provides a centralized logging configuration and custom formatters.
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any, Union

# ANSI color codes for colored terminal output
COLORS = {
    'RESET': '\033[0m',
    'BLACK': '\033[30m',
    'RED': '\033[31m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'BLUE': '\033[34m',
    'MAGENTA': '\033[35m',
    'CYAN': '\033[36m',
    'WHITE': '\033[37m',
    'BOLD': '\033[1m',
    'UNDERLINE': '\033[4m',
}

# Mapping of log levels to colors
LEVEL_COLORS = {
    logging.DEBUG: COLORS['BLUE'],
    logging.INFO: COLORS['GREEN'],
    logging.WARNING: COLORS['YELLOW'],
    logging.ERROR: COLORS['RED'],
    logging.CRITICAL: COLORS['BOLD'] + COLORS['RED'],
}


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels in terminal output."""
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors if enabled."""
        # Save the original levelname
        orig_levelname = record.levelname
        
        # Apply colors if enabled and we're not in a non-TTY environment
        if self.use_colors and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            color = LEVEL_COLORS.get(record.levelno, COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{COLORS['RESET']}"
        
        # Format the message
        result = super().format(record)
        
        # Restore the original levelname
        record.levelname = orig_levelname
        
        return result


def setup_logging(config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        config: Optional configuration dictionary with the following keys:
            - log_level: Minimum log level to capture (default: INFO)
            - log_file: Path to log file (default: None, logs to console only)
            - log_format: Format string for log messages
            - use_colors: Whether to use colors in console output (default: True)
            - max_file_size: Maximum size of log file before rotation in bytes (default: 10MB)
            - backup_count: Number of backup log files to keep (default: 5)
    
    Returns:
        The root logger instance.
    """
    if config is None:
        config = {}
    
    # Get configuration values with defaults
    log_level_name = config.get('log_level', 'INFO').upper()
    log_file = config.get('log_file')
    log_format = config.get('log_format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    use_colors = config.get('use_colors', True)
    max_file_size = config.get('max_file_size', 10 * 1024 * 1024)  # 10MB
    backup_count = config.get('backup_count', 5)
    
    # Convert log level name to numeric value
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Create formatter and add it to the handler
    console_formatter = ColoredFormatter(log_format, use_colors=use_colors)
    console_handler.setFormatter(console_formatter)
    
    # Add the console handler to the logger
    logger.addHandler(console_handler)
    
    # Add file handler if log_file is specified
    if log_file:
        try:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count
            )
            file_handler.setLevel(log_level)
            
            # Create formatter without colors for file output
            file_formatter = logging.Formatter(log_format)
            file_handler.setFormatter(file_formatter)
            
            # Add the file handler to the logger
            logger.addHandler(file_handler)
            
            logger.info(f"Logging to file: {log_file}")
        
        except Exception as e:
            logger.error(f"Failed to set up file logging to {log_file}: {str(e)}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Name of the logger, typically the module name.
    
    Returns:
        A logger instance.
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for temporarily changing the log level."""
    
    def __init__(self, logger: Union[logging.Logger, str], level: int):
        """
        Initialize the context manager.
        
        Args:
            logger: Logger instance or name of logger.
            level: Log level to temporarily set.
        """
        self.logger = logger if isinstance(logger, logging.Logger) else logging.getLogger(logger)
        self.level = level
        self.previous_level = None
    
    def __enter__(self) -> logging.Logger:
        """Set the temporary log level."""
        self.previous_level = self.logger.level
        self.logger.setLevel(self.level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Restore the previous log level."""
        self.logger.setLevel(self.previous_level)


def debug_mode(logger_name: str = None) -> LogContext:
    """
    Context manager to temporarily enable debug logging.
    
    Args:
        logger_name: Name of the logger to affect. If None, affects the root logger.
    
    Returns:
        A LogContext instance.
    """
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    return LogContext(logger, logging.DEBUG)


if __name__ == "__main__":
    # Test the logging setup
    import argparse
    
    parser = argparse.ArgumentParser(description="Test logging configuration")
    parser.add_argument("--level", default="INFO", help="Log level")
    parser.add_argument("--file", help="Log file path")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    
    args = parser.parse_args()
    
    # Set up logging
    config = {
        'log_level': args.level,
        'log_file': args.file,
        'use_colors': not args.no_color
    }
    
    logger = setup_logging(config)
    
    # Test logging at different levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # Test with a named logger
    test_logger = get_logger("test")
    test_logger.info("This is a message from the test logger")
    
    # Test the debug context manager
    with debug_mode():
        logger.debug("This debug message should be visible inside the context")
    
    logger.debug("This debug message might not be visible outside the context")