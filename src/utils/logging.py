"""
Logging setup for KubeNetLLM framework.
"""

import logging
import sys
from typing import Optional, Dict, Any
from pathlib import Path

import structlog
from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    level: str = "INFO",
    format_type: str = "rich",
    log_file: Optional[str] = None,
    console: Optional[Console] = None
) -> None:
    """
    Setup logging for KubeNetLLM framework.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("rich", "json", "plain")
        log_file: Optional log file path
        console: Optional Rich console instance
    """
    # Convert level string to logging level
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Clear any existing handlers
    logging.root.handlers.clear()
    structlog.reset_defaults()
    
    # Setup handlers
    handlers = []
    
    # Console handler
    if format_type == "rich":
        if console is None:
            console = Console(stderr=True)
        
        rich_handler = RichHandler(
            console=console,
            show_path=False,
            show_time=True,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True
        )
        rich_handler.setLevel(log_level)
        handlers.append(rich_handler)
        
    elif format_type == "json":
        json_handler = logging.StreamHandler(sys.stdout)
        json_handler.setLevel(log_level)
        handlers.append(json_handler)
        
    else:  # plain format
        plain_handler = logging.StreamHandler(sys.stdout)
        plain_handler.setLevel(log_level)
        plain_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        plain_handler.setFormatter(plain_formatter)
        handlers.append(plain_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        format="%(message)s"
    )
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if format_type == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set specific loggers to appropriate levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("kubernetes").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Create root logger
    logger = structlog.get_logger("kubenet")
    logger.info("Logging configured", 
                level=level, 
                format_type=format_type,
                log_file=log_file)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


def set_log_level(level: str) -> None:
    """
    Set log level for all loggers.
    
    Args:
        level: Log level string
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.getLogger().setLevel(log_level)
    
    # Update all handlers
    for handler in logging.getLogger().handlers:
        handler.setLevel(log_level)


def add_log_file(log_file: str, level: str = "INFO") -> None:
    """
    Add a file handler to existing loggers.
    
    Args:
        log_file: Path to log file
        level: Log level for file handler
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    
    logging.getLogger().addHandler(file_handler)
    
    logger = get_logger("kubenet.logging")
    logger.info("Added file handler", log_file=log_file, level=level)


def create_experiment_logger(experiment_name: str, output_dir: str = "experiments/results") -> structlog.stdlib.BoundLogger:
    """
    Create a logger for experiments with file output.
    
    Args:
        experiment_name: Name of the experiment
        output_dir: Output directory for logs
        
    Returns:
        Configured logger for the experiment
    """
    log_file = Path(output_dir) / f"{experiment_name}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a specific logger for this experiment
    logger_name = f"kubenet.experiment.{experiment_name}"
    logger = structlog.get_logger(logger_name)
    
    # Add file handler for this specific logger
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # Capture everything for experiments
    file_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    
    # Get the actual logging.Logger instance and add the handler
    stdlib_logger = logging.getLogger(logger_name)
    stdlib_logger.addHandler(file_handler)
    stdlib_logger.setLevel(logging.DEBUG)
    
    logger.info("Experiment logger created", 
                experiment_name=experiment_name,
                log_file=str(log_file))
    
    return logger


class ExperimentLogContext:
    """Context manager for experiment logging"""
    
    def __init__(self, experiment_name: str, output_dir: str = "experiments/results"):
        self.experiment_name = experiment_name
        self.output_dir = output_dir
        self.logger = None
        self.log_file = None
        self.handler = None
    
    def __enter__(self) -> structlog.stdlib.BoundLogger:
        """Enter the context and create experiment logger"""
        self.logger = create_experiment_logger(self.experiment_name, self.output_dir)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and clean up"""
        if self.handler:
            logger_name = f"kubenet.experiment.{self.experiment_name}"
            stdlib_logger = logging.getLogger(logger_name)
            stdlib_logger.removeHandler(self.handler)
            self.handler.close()
        
        if exc_type:
            self.logger.error("Experiment failed", 
                            experiment_name=self.experiment_name,
                            error=str(exc_val))
        else:
            self.logger.info("Experiment completed", 
                           experiment_name=self.experiment_name)


# Convenience function for quick experiment logging
def with_experiment_logging(experiment_name: str, output_dir: str = "experiments/results"):
    """
    Decorator for experiment functions that adds logging.
    
    Args:
        experiment_name: Name of the experiment
        output_dir: Output directory for logs
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with ExperimentLogContext(experiment_name, output_dir) as logger:
                return func(logger, *args, **kwargs)
        return wrapper
    return decorator 