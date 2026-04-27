"""Configuration loader for Claims Reconciliation Agent."""
import os
from dotenv import load_dotenv
from typing import Dict

load_dotenv()

class Config:
    """Configuration settings loaded from environment variables."""

    # File Processing
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    ALLOWED_EXTENSIONS: list = os.getenv("ALLOWED_EXTENSIONS", "csv,json,edi").split(",")

    # Fuzzy Matching Thresholds
    FUZZY_NAME_THRESHOLD: int = int(os.getenv("FUZZY_NAME_THRESHOLD", "90"))
    DATE_TOLERANCE_DAYS: int = int(os.getenv("DATE_TOLERANCE_DAYS", "2"))
    AMOUNT_TOLERANCE_PCT: float = float(os.getenv("AMOUNT_TOLERANCE_PCT", "0.01"))
    AMOUNT_TOLERANCE_ABS: float = float(os.getenv("AMOUNT_TOLERANCE_ABS", "10.0"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "reconciliation.log")
    LOG_SANITIZE_PII: str = os.getenv("LOG_SANITIZE_PII", "false")

    # Report Generation
    REPORT_DIR: str = os.getenv("REPORT_DIR", "reports")
    DEFAULT_REPORT_FORMAT: str = os.getenv("DEFAULT_REPORT_FORMAT", "csv")

    # Supported Insurers
    SUPPORTED_INSURERS: list = os.getenv("SUPPORTED_INSURERS", "Medicare,Bupa,Medibank,HBF,nib").split(",")

    @classmethod
    def to_dict(cls) -> Dict:
        """Convert config to dictionary."""
        return {
            k: v for k, v in cls.__dict__.items()
            if not k.startswith("__")
            and not callable(v)
            and not isinstance(v, (classmethod, staticmethod))
        }
