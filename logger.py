#!/usr/bin/env python3
"""
Comprehensive Logging System for LinkedIn Job Application Automation

This module provides structured logging with different loggers for various components
of the job application automation system.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

class JobApplicationLogger:
    """
    Centralized logging system for job application automation.
    """
    
    def __init__(self, log_file: str = "job_application.log"):
        """
        Initialize the logging system.
        
        Args:
            log_file: Path to the log file
        """
        self.log_file = log_file
        self.logger = logging.getLogger("job_application_logger")
        self.logger.setLevel(logging.INFO)
        self._setup_handlers()

    def _setup_handlers(self):
        """Attach file and console handlers to the logger (only once)."""
        if not self.logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            # File handler
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def get_logger(self) -> logging.Logger:
        return self.logger
    