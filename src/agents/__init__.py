"""
Agents Package – Core processing components for claims reconciliation.

This package contains five autonomous agents that collaborate to transform raw
claim and payment files into reconciled reports:

1. **FileIngestor** – Load and validate CSV/JSON/EDI files
2. **DataCleaner** – Normalize patient names, dates, and amounts
3. **FuzzyMatcher** – Match claims to payments using fuzzy logic
4. **DiscrepancyDetector** – Categorize issues (underpayments, duplicates)
5. **ReportGenerator** – Output results in CSV/JSON/PDF formats

Each agent is independently usable but designed to work in sequence.
"""

from .file_ingestor import FileIngestor, ingest_file
from .data_cleaner import DataCleaner, clean_data
from .fuzzy_matcher import FuzzyMatcher, match_claims_payments
from .discrepancy_detector import DiscrepancyDetector, detect_discrepancies
from .report_generator import ReportGenerator, generate_report

__all__ = [
    "FileIngestor",
    "ingest_file",
    "DataCleaner",
    "clean_data",
    "FuzzyMatcher",
    "match_claims_payments",
    "DiscrepancyDetector",
    "detect_discrepancies",
    "ReportGenerator",
    "generate_report",
]

__version__ = "1.0.0"
