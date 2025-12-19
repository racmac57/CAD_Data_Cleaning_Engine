"""
Structured logging utility for CAD data processing pipeline.

Provides timestamped, formatted logging with automatic file rotation
and console output for all CAD processing operations.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logger(
    name: str = "cad_processor",
    log_file: str = "logs/cad_processing.log",
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    Configure and return a structured logger for CAD processing.

    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        console_output: Whether to output to console as well

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # Log initialization
    logger.info("=" * 80)
    logger.info(f"Logger initialized: {name}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Log level: {logging.getLevelName(level)}")
    logger.info(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    return logger


def log_dataframe_info(logger: logging.Logger, df, name: str = "DataFrame"):
    """
    Log comprehensive information about a DataFrame.

    Args:
        logger: Logger instance
        df: pandas DataFrame
        name: Name/description of the DataFrame
    """
    logger.info(f"{name} Information:")
    logger.info(f"  Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
    logger.info(f"  Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    logger.info(f"  Columns: {', '.join(df.columns.tolist())}")

    # Log null counts for columns with missing values
    null_counts = df.isnull().sum()
    if null_counts.any():
        logger.info(f"  Columns with null values:")
        for col, count in null_counts[null_counts > 0].items():
            pct = (count / len(df)) * 100
            logger.info(f"    {col}: {count:,} ({pct:.2f}%)")


def log_processing_step(logger: logging.Logger, step_name: str, details: dict = None):
    """
    Log a processing step with optional details.

    Args:
        logger: Logger instance
        step_name: Name of processing step
        details: Optional dictionary of step details
    """
    logger.info("-" * 80)
    logger.info(f"STEP: {step_name}")
    if details:
        for key, value in details.items():
            logger.info(f"  {key}: {value}")
    logger.info("-" * 80)


def log_validation_result(logger: logging.Logger, validation_name: str, passed: bool, message: str = ""):
    """
    Log a validation result with status.

    Args:
        logger: Logger instance
        validation_name: Name of validation check
        passed: Whether validation passed
        message: Optional message with details
    """
    status = "PASSED" if passed else "FAILED"
    level = logging.INFO if passed else logging.ERROR

    logger.log(level, f"Validation [{status}]: {validation_name}")
    if message:
        logger.log(level, f"  {message}")


def log_correction_summary(logger: logging.Logger, correction_type: str, records_affected: int, details: dict = None):
    """
    Log a summary of corrections applied.

    Args:
        logger: Logger instance
        correction_type: Type of correction applied
        records_affected: Number of records affected
        details: Optional dictionary of correction details
    """
    logger.info(f"Correction Applied: {correction_type}")
    logger.info(f"  Records affected: {records_affected:,}")
    if details:
        for key, value in details.items():
            logger.info(f"  {key}: {value}")


def log_error_with_context(logger: logging.Logger, error: Exception, context: str = ""):
    """
    Log an error with context information.

    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Context description where error occurred
    """
    logger.error("=" * 80)
    logger.error(f"ERROR OCCURRED: {context}")
    logger.error(f"Error Type: {type(error).__name__}")
    logger.error(f"Error Message: {str(error)}")
    logger.error("=" * 80)


# Example usage
if __name__ == "__main__":
    # Test the logger
    logger = setup_logger(
        name="test_logger",
        log_file="logs/test.log",
        level=logging.DEBUG
    )

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    # Test helper functions
    log_processing_step(logger, "Test Step", {"detail1": "value1", "detail2": 123})
    log_validation_result(logger, "Test Validation", True, "All checks passed")
    log_validation_result(logger, "Failed Validation", False, "Found issues")
    log_correction_summary(logger, "Test Correction", 1000, {"field": "Address", "method": "RMS Backfill"})
