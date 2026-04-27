"""Shared helper functions for Claims Reconciliation Agent."""
import re
import logging
from datetime import datetime
from typing import Tuple, Optional
import pandas as pd

logger = logging.getLogger(__name__)

def clean_name(name: str) -> str:
    """
    Standardize patient name: remove extra whitespace, title case.

    Args:
        name: Raw patient name (any string, handles NaN)

    Returns:
        Cleaned name (e.g., "J. Smith" -> "J Smith", "  jane  " -> "Jane")
    """
    if pd.isna(name):
        return ""
    # Remove extra whitespace, convert to title case
    cleaned = " ".join(str(name).split()).title()
    # Remove periods (e.g., "J. Smith" -> "J Smith")
    cleaned = cleaned.replace(".", "")
    return cleaned.strip()

def standardize_date(date_str: str, input_format: str = "%Y-%m-%d") -> Optional[datetime]:
    """
    Parse and standardize date strings to datetime objects.

    Supports multiple Australian date formats. Returns None (NaT) for unparseable values.

    Args:
        date_str: Date string in various formats
        input_format: Default format for parsing (unused, kept for compatibility)

    Returns:
        datetime object or None if invalid
    """
    if pd.isna(date_str):
        return None

    date_str = str(date_str).strip()

    # Try common Australian date formats
    formats = [
        "%Y-%m-%d",      # 2026-04-01
        "%d/%m/%Y",      # 01/04/2026
        "%d-%m-%Y",      # 01-04-2026
        "%Y/%m/%d",      # 2026/04/01
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_str}")
    return None

def clean_amount(amount_str: str) -> float:
    """
    Convert amount string to float, removing currency symbols and commas.

    Args:
        amount_str: Amount string (e.g., "$1,500.00", "1500", "  $2,250.50 ")

    Returns:
        Float value (0.0 if unparseable)
    """
    if pd.isna(amount_str):
        return 0.0

    amount_str = str(amount_str).strip()
    # Remove $ and commas
    cleaned = re.sub(r"[\$,]", "", amount_str)
    try:
        return float(cleaned)
    except ValueError:
        logger.warning(f"Could not parse amount: {amount_str}")
        return 0.0

def validate_columns(df: pd.DataFrame, required_cols: list) -> Tuple[bool, list]:
    """
    Check if DataFrame has required columns.

    Args:
        df: DataFrame to validate
        required_cols: List of required column names

    Returns:
        Tuple of (is_valid, missing_columns_list)
    """
    missing = [col for col in required_cols if col not in df.columns]
    return len(missing) == 0, missing

def calculate_amount_difference(amount1: float, amount2: float, tolerance_pct: float, tolerance_abs: float) -> bool:
    """
    Check if two amounts are within tolerance thresholds.

    Amounts match if either absolute difference ≤ tolerance_abs OR
    percentage difference ≤ tolerance_pct.

    Args:
        amount1: First amount
        amount2: Second amount
        tolerance_pct: Percentage tolerance (e.g., 0.01 = 1%)
        tolerance_abs: Absolute dollar tolerance

    Returns:
        True if amounts match within tolerance
    """
    diff = abs(amount1 - amount2)

    # Check absolute tolerance first
    if diff <= tolerance_abs:
        return True

    # Check percentage tolerance
    avg = (amount1 + amount2) / 2
    if avg > 0 and (diff / avg) <= tolerance_pct:
        return True

    return False

def dates_within_tolerance(date1: datetime, date2: datetime, tolerance_days: int) -> bool:
    """
    Check if two dates are within tolerance range.

    Args:
        date1: First date
        date2: Second date
        tolerance_days: Maximum allowed day difference

    Returns:
        True if dates are within tolerance (|date_diff| ≤ tolerance_days)
    """
    if pd.isna(date1) or pd.isna(date2):
        return False
    return abs((date1 - date2).days) <= tolerance_days
