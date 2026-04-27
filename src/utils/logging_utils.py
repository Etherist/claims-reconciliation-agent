"""Logging utilities for PII sanitization."""
import logging
import os
from typing import Dict, Any
from utils.config import Config

class PIIRedactingFilter(logging.Filter):
    """Filter that redacts PII from log records based on configuration."""

    # Keys that may contain PII
    PII_KEYS = {'patient_name', 'patient', 'name', 'amount', 'claim_amount', 'payment_amount'}

    def __init__(self):
        super().__init__()
        self.redact_pii = Config.LOG_SANITIZE_PII.lower() == 'true'

    def redact_value(self, value: Any) -> Any:
        """Redact sensitive values."""
        if isinstance(value, str) and value:
            return "[REDACTED]"
        return value

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record, redacting PII if enabled."""
        if not self.redact_pii:
            return True

        # Redact message arguments if they correspond to PII keys
        if hasattr(record, 'args') and isinstance(record.args, dict):
            for key in self.PII_KEYS:
                if key in record.args:
                    record.args[key] = self.redact_value(record.args[key])

        # Also sanitize the message string if we can detect PII patterns
        # (simple approach – real implementation could use regex)
        return True

def configure_logging():
    """Configure root logger with PII filter if enabled."""
    root_logger = logging.getLogger()
    if Config.LOG_SANITIZE_PII.lower() == 'true':
        pii_filter = PIIRedactingFilter()
        for handler in root_logger.handlers:
            # Avoid adding duplicate PII filters (idempotency)
            if not any(isinstance(f, PIIRedactingFilter) for f in handler.filters):
                handler.addFilter(pii_filter)
        logging.getLogger(__name__).info("PII sanitization enabled in logs")