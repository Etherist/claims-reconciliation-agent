"""
Claims Reconciliation Agent - Main Package

A modular, agent-based system for automating healthcare claims reconciliation.
Designed for Australian hospitals and insurers to match claims to payments,
identify discrepancies, and generate finance-ready reports.

Agent Architecture:
- File Ingestor: Parse CSV/JSON/EDI files
- Data Cleaner: Standardize names, dates, amounts
- Fuzzy Matcher: Match claims to payments using similarity scoring
- Discrepancy Detector: Flag underpayments, duplicates, unmatched items
- Report Generator: Create CSV/JSON/PDF outputs

Example usage:
    from src.agents import ingest_file, clean_data, match_claims_payments
    claims = ingest_file("claims.csv", "claims")
    payments = ingest_file("payments.csv", "payments")
    matched, disc = match_claims_payments(
        clean_data(claims, "claims"),
        clean_data(payments, "payments")
    )

See README.md for full documentation.
"""

# Agents package
from agents import (
    FileIngestor,
    ingest_file,
    DataCleaner,
    clean_data,
    FuzzyMatcher,
    match_claims_payments,
    DiscrepancyDetector,
    detect_discrepancies,
    ReportGenerator,
    generate_report,
)

# Utils package
from utils import Config, clean_name, standardize_date, clean_amount

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
    "Config",
    "clean_name",
    "standardize_date",
    "clean_amount",
]

__version__ = "1.0.0"
