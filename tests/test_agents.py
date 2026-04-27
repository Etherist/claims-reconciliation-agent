"""
Comprehensive tests for all Claims Reconciliation Agents.
"""
import builtins
import importlib.util
import json
import pytest
import pandas as pd
import tempfile
import os
import sys
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import using absolute imports from src root
from agents.file_ingestor import FileIngestor, ingest_file
from agents.data_cleaner import clean_data, DataCleaner  
from agents.fuzzy_matcher import match_claims_payments, FuzzyMatcher
from agents.discrepancy_detector import detect_discrepancies, DiscrepancyDetector
from agents.report_generator import ReportGenerator, generate_report
from utils.config import Config
from utils.helpers import (
    clean_name, standardize_date, clean_amount, validate_columns,
    calculate_amount_difference, dates_within_tolerance
)

# ==================== FILE INGESTOR TESTS ====================

class TestFileIngestor:
    """Test suite for File Ingestion."""

    def test_ingest_valid_csv(self):
        """Test ingesting a valid CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("claim_id,patient_name,date_of_service,amount,provider_id,insurer\n")
            f.write("101,John Smith,2026-04-01,1500.00,PRV123,Medicare\n")
            temp_path = f.name

        try:
            ingestor = FileIngestor()
            df = ingestor.ingest_file(temp_path, "claims")
            assert len(df) == 1
            assert "patient_name" in df.columns
            assert df.iloc[0]["patient_name"] == "John Smith"
        finally:
            os.unlink(temp_path)

    def test_ingest_invalid_file_not_found(self):
        """Test handling of non-existent file."""
        ingestor = FileIngestor()
        with pytest.raises(ValueError, match="File not found"):
            ingestor.ingest_file("nonexistent.csv", "claims")

    def test_ingest_invalid_format(self):
        """Test handling of unsupported file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("some content")
            temp_path = f.name

        try:
            ingestor = FileIngestor()
            with pytest.raises(ValueError, match="Unsupported file format"):
                ingestor.ingest_file(temp_path, "claims")
        finally:
            os.unlink(temp_path)

    def test_ingest_missing_required_columns(self):
        """Test handling of missing required columns."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("claim_id,patient_name\n")  # Missing required columns
            f.write("101,John Smith\n")
            temp_path = f.name

        try:
            ingestor = FileIngestor()
            with pytest.raises(ValueError, match="Missing required columns"):
                ingestor.ingest_file(temp_path, "claims")
        finally:
            os.unlink(temp_path)

    def test_ingest_payments_file(self):
        """Test ingesting a payments file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("payment_id,patient_name,date_of_service,amount,provider_id,insurer\n")
            f.write("201,John Smith,2026-04-01,1400.00,PRV123,Medicare\n")
            temp_path = f.name

        try:
            ingestor = FileIngestor()
            df = ingestor.ingest_file(temp_path, "payments")
            assert len(df) == 1
            assert "payment_id" in df.columns
            assert df.iloc[0]["payment_id"] == "201"
        finally:
            os.unlink(temp_path)

    def test_convenience_function(self):
        """Test the convenience ingest_file function."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("claim_id,patient_name,date_of_service,amount,provider_id,insurer\n")
            f.write("101,Test Patient,2026-04-01,1000.00,PRV999,Bupa\n")
            temp_path = f.name

        try:
            df = ingest_file(temp_path, "claims")
            assert len(df) == 1
            assert df.iloc[0]["claim_id"] == "101"
        finally:
            os.unlink(temp_path)

    def test_validate_file_path_outside_project(self):
        """Test that file path outside project directory is rejected."""
        ingestor = FileIngestor()
        # Use an absolute path outside project (e.g., /tmp if not /tmp? but /tmp is allowed as temp)
        # Actually validate_file allows paths in temp dir, so we need a path definitely outside both
        outside_path = "/nonexistent/path/file.csv"
        is_valid, error = ingestor.validate_file(outside_path)
        assert is_valid is False
        assert "outside allowed directories" in error

    def test_validate_file_nonexistent(self):
        """Test nonexistent file is rejected."""
        ingestor = FileIngestor()
        is_valid, error = ingestor.validate_file("/path/that/does/not/exist.csv")
        assert is_valid is False
        assert "outside allowed directories" in error or "File not found" in error

    def test_validate_file_too_large(self):
        """Test file size limit enforcement."""
        # Create a file larger than max
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Write some data (size doesn't matter exactly, we'll just test logic)
            f.write(b"x" * (11 * 1024 * 1024))  # 11 MB when max is 10
            temp_path = f.name
        
        try:
            ingestor = FileIngestor(max_file_size_mb=10)
            is_valid, error = ingestor.validate_file(temp_path)
            assert is_valid is False
            assert "too large" in error.lower() or "File too large" in error
        finally:
            os.unlink(temp_path)

    def test_validate_file_unsupported_extension(self):
        """Test unsupported file extensions are rejected."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(b"test")
            temp_path = f.name
        
        try:
            ingestor = FileIngestor()
            is_valid, error = ingestor.validate_file(temp_path)
            assert is_valid is False
            assert "Unsupported file format" in error
        finally:
            os.unlink(temp_path)

    def test_ingest_json(self):
        """Test JSON ingestion."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            # Write JSON array of objects
            f.write('[{"claim_id": "101", "patient_name": "Test"}]')
            temp_path = f.name
        
        try:
            ingestor = FileIngestor()
            df = ingestor.ingest_json(temp_path)
            assert len(df) == 1
            assert df.iloc[0]["claim_id"] == "101"
        finally:
            os.unlink(temp_path)

    def test_ingest_edi_stub(self):
        """Test EDI ingestion returns empty DataFrame with warning."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.edi') as f:
            f.write(b"EDI content not parsed")
            temp_path = f.name
        
        try:
            ingestor = FileIngestor()
            df = ingestor.ingest_edi(temp_path)
            assert df.empty
            assert list(df.columns) == []
        finally:
            os.unlink(temp_path)

    def test_ingest_csv_with_missing_required_columns_raises(self):
        """Test that CSV with missing required columns raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("claim_id,patient_name\n")  # Missing date_of_service, amount, etc.
            f.write("101,John Smith\n")
            temp_path = f.name
        
        try:
            ingestor = FileIngestor()
            with pytest.raises(ValueError, match="Missing required columns"):
                ingestor.ingest_file(temp_path, "claims")
        finally:
            os.unlink(temp_path)

    def test_config_to_dict(self):
        """Test Config.to_dict method."""
        config_dict = Config.to_dict()
        # Should be a dict with all the class attributes
        assert isinstance(config_dict, dict)
        # Check a few known keys are present
        assert "MAX_FILE_SIZE_MB" in config_dict
        assert "FUZZY_NAME_THRESHOLD" in config_dict
        assert "REPORT_DIR" in config_dict
        assert "SUPPORTED_INSURERS" in config_dict
        # Should not contain private methods
        assert not any(k.startswith("__") for k in config_dict.keys())
        # Should not contain callable methods (except maybe classmethods? but to_dict is a method, but we are calling it on the class, so the class's __dict__ includes the function object? Actually the to_dict method is in the class dict, but we are filtering out callables, so it should not be in the result.
        assert "to_dict" not in config_dict  # because it's a method and we filter out callables

# ==================== DATA CLEANER TESTS ====================

class TestDataCleaner:
    """Test suite for Data Cleaning."""

    def test_clean_patient_names(self):
        """Test patient name standardization."""
        cleaner = DataCleaner()
        df = pd.DataFrame({
            "patient_name": ["J. Smith", "  jane doe  ", "BOB JONES"],
            "amount": [100, 200, 300],
            "date_of_service": ["2026-04-01", "2026-04-02", "2026-04-03"]
        })
        cleaned = cleaner.clean_patient_names(df)
        assert cleaned["patient_name"].iloc[0] == "J Smith"
        assert cleaned["patient_name"].iloc[1] == "Jane Doe"
        assert cleaned["patient_name"].iloc[2] == "Bob Jones"

    def test_clean_dates(self):
        """Test date standardization."""
        cleaner = DataCleaner()
        df = pd.DataFrame({
            "patient_name": ["Test1", "Test2", "Test3"],
            "date_of_service": ["01/04/2026", "2026-04-02", "2026/04/03"]
        })
        cleaned = cleaner.clean_dates(df)
        assert "date_of_service_dt" in cleaned.columns
        assert cleaned["date_of_service_dt"].iloc[0] is not None

    def test_clean_amounts(self):
        """Test amount cleaning."""
        cleaner = DataCleaner()
        df = pd.DataFrame({
            "amount": ["$1,500.00", "2000", "  $350.50 "]
        })
        cleaned = cleaner.clean_amounts(df)
        assert cleaned["amount_clean"].iloc[0] == 1500.00
        assert cleaned["amount_clean"].iloc[1] == 2000.00
        assert cleaned["amount_clean"].iloc[2] == 350.50

    def test_clean_dataframe_full(self):
        """Test full dataframe cleaning."""
        raw = pd.DataFrame({
            "claim_id": ["101"],
            "patient_name": ["J. SMITH"],
            "date_of_service": ["01/04/2026"],
            "amount": ["$1,500.00"],
            "provider_id": ["PRV123"],
            "insurer": ["medicare"]
        })
        cleaned = clean_data(raw, "claims")

        assert cleaned["patient_name"].iloc[0] == "J Smith"
        assert cleaned["amount"].iloc[0] == 1500.00
        assert cleaned["insurer"].iloc[0] == "Medicare"
        assert "date_of_service_dt" in cleaned.columns

# ==================== FUZZY MATCHER TESTS ====================

class TestFuzzyMatcher:
    """Test suite for fuzzy matching."""

    def test_exact_match(self):
        """Test exact name match."""
        matcher = FuzzyMatcher(name_threshold=90)
        claim = pd.Series({
            "patient_name": "John Smith",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1500.00
        })
        payment = pd.Series({
            "patient_name": "John Smith",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1500.00
        })
        score, components = matcher._score_match(claim, payment)
        assert score >= 90  # Should be very high

    def test_fuzzy_name_match(self):
        """Test fuzzy name matching (typos)."""
        matcher = FuzzyMatcher(name_threshold=80)
        claim = pd.Series({
            "patient_name": "John Smith",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1500.00
        })
        payment = pd.Series({
            "patient_name": "John Smyth",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1500.00
        })
        score, components = matcher._score_match(claim, payment)
        assert score >= 80  # Should still match due to fuzzy name

    def test_no_match_different_patients(self):
        """Test no match for completely different names."""
        matcher = FuzzyMatcher(name_threshold=90)
        claim = pd.Series({
            "patient_name": "John Smith",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1500.00
        })
        payment = pd.Series({
            "patient_name": "Jane Doe",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1500.00
        })
        score, components = matcher._score_match(claim, payment)
        assert score < 90

    def test_date_tolerance(self):
        """Test date tolerance (±2 days)."""
        matcher = FuzzyMatcher(date_tolerance_days=2)
        claim = pd.Series({
            "patient_name": "Test",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1000.00
        })
        # Payment date is 1 day later - should match
        payment = pd.Series({
            "patient_name": "Test",
            "date_of_service_dt": pd.Timestamp("2026-04-02"),
            "amount": 1000.00
        })
        score, components = matcher._score_match(claim, payment)
        assert components["date"] == 100  # Full date score

    def test_date_missing_gives_neutral_score(self):
        """Test that missing dates result in neutral score (50)."""
        matcher = FuzzyMatcher()
        claim = pd.Series({
            "patient_name": "Test",
            "date_of_service_dt": None,  # Missing
            "amount": 1000.00
        })
        payment = pd.Series({
            "patient_name": "Test",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1000.00
        })
        score, components = matcher._score_match(claim, payment)
        assert components["date"] == 50  # Neutral when date missing

    def test_amount_tolerance(self):
        """Test amount tolerance."""
        matcher = FuzzyMatcher(amount_tolerance_pct=0.01)  # 1%
        claim = pd.Series({
            "patient_name": "Test",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1000.00
        })
        # Payment amount is 1% lower - should match
        payment = pd.Series({
            "patient_name": "Test",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 990.00
        })
        score, components = matcher._score_match(claim, payment)
        assert components["amount"] == 100  # Full amount score

    def test_full_matching_pipeline(self):
        """Test end-to-end matching with sample data."""
        claims = pd.DataFrame({
            "claim_id": ["101", "102"],
            "patient_name": ["John Smith", "Jane Doe"],
            "date_of_service": ["2026-04-01", "2026-04-02"],
            "amount": [1500.00, 2000.00],
            "provider_id": ["PRV123", "PRV456"],
            "insurer": ["Medicare", "Bupa"],
            "date_of_service_dt": [pd.Timestamp("2026-04-01"), pd.Timestamp("2026-04-02")]
        })
        payments = pd.DataFrame({
            "payment_id": ["201", "202"],
            "patient_name": ["John Smith", "Jane Doe"],
            "date_of_service": ["2026-04-01", "2026-04-02"],
            "amount": [1400.00, 2000.00],
            "provider_id": ["PRV123", "PRV456"],
            "insurer": ["Medicare", "Bupa"],
            "date_of_service_dt": [pd.Timestamp("2026-04-01"), pd.Timestamp("2026-04-02")]
        })

        matched, discrepancies = match_claims_payments(claims, payments)

        assert len(matched) == 2
        assert len([d for d in discrepancies if d["type"] == "unmatched_claim"]) == 0

    def test_overpayment_detection_in_matching(self):
        """Test that overpayment (payment > claim) is flagged correctly."""
        matcher = FuzzyMatcher(name_threshold=80)  # lower to ensure name match
        claims = pd.DataFrame([{
            "claim_id": "101",
            "patient_name": "John Smith",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1000.00,
            "provider_id": "PRV123",
            "insurer": "Medicare"
        }])
        payments = pd.DataFrame([{
            "payment_id": "201",
            "patient_name": "John Smith",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1100.00,  # Overpayment
            "provider_id": "PRV123",
            "insurer": "Medicare"
        }])
        
        matched, discrepancies = matcher.match_claims_payments(claims, payments)
        
        assert len(matched) == 1
        assert matched.iloc[0]["discrepancy_type"] == "overpayment"
        assert matched.iloc[0]["difference"] == -100.00

    def test_unmatched_payment_detection(self):
        """Test that unmatched payments are flagged."""
        matcher = FuzzyMatcher(name_threshold=90)
        claims = pd.DataFrame([{
            "claim_id": "101",
            "patient_name": "John Smith",
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1000.00,
            "provider_id": "PRV123",
            "insurer": "Medicare"
        }])
        # Payment with different patient name will not match
        payments = pd.DataFrame([{
            "payment_id": "201",
            "patient_name": "Jane Doe",  # Different name - won't match
            "date_of_service_dt": pd.Timestamp("2026-04-01"),
            "amount": 1000.00,
            "provider_id": "PRV123",
            "insurer": "Medicare"
        }])
        
        matched, discrepancies = matcher.match_claims_payments(claims, payments)
        
        # Claim should be unmatched (since name mismatch)
        assert len(matched) == 0
        # Payment also unmatched
        unmatched_payments = [d for d in discrepancies if d["type"] == "unmatched_payment"]
        assert len(unmatched_payments) == 1
        assert unmatched_payments[0]["payment_id"] == "201"

# ==================== DISCREPANCY DETECTOR TESTS ====================

class TestDiscrepancyDetector:
    """Test suite for discrepancy detection."""

    def test_underpayment_detection(self):
        """Detecting underpayments from matched records."""
        matched = pd.DataFrame([{
            "claim_id": "101",
            "payment_id": "201",
            "patient_name": "John Smith",
            "claim_amount": 1500.00,
            "payment_amount": 1400.00,
            "difference": 100.00,
            "discrepancy_type": "underpayment"
        }])
        raw_claims = pd.DataFrame([{"claim_id": "101", "amount": 1500.00}])
        raw_payments = pd.DataFrame([{"payment_id": "201", "amount": 1400.00}])

        result = detect_discrepancies(matched, raw_claims, raw_payments)
        discrepancies = result["discrepancies"]

        underpayments = [d for d in discrepancies if d["type"] == "underpayment"]
        assert len(underpayments) == 1
        assert underpayments[0]["difference"] == 100.00

    def test_overpayment_detection(self):
        """Detecting overpayments."""
        matched = pd.DataFrame([{
            "claim_id": "102",
            "payment_id": "202",
            "claim_amount": 1000.00,
            "payment_amount": 1100.00,
            "difference": -100.00,
            "discrepancy_type": "overpayment"
        }])
        raw_claims = pd.DataFrame([{"claim_id": "102", "amount": 1000.00}])
        raw_payments = pd.DataFrame([{"payment_id": "202", "amount": 1100.00}])

        result = detect_discrepancies(matched, raw_claims, raw_payments)
        overpayments = [d for d in result["discrepancies"] if d["type"] == "overpayment"]
        assert len(overpayments) == 1

    def test_unmatched_claim_detection(self):
        """Detecting unmatched claims (no payment found)."""
        matched = pd.DataFrame()  # No matches
        raw_claims = pd.DataFrame([
            {"claim_id": "101", "patient_name": "John", "amount": 1000, "date_of_service": "2026-04-01"}
        ])
        raw_payments = pd.DataFrame()

        result = detect_discrepancies(matched, raw_claims, raw_payments)
        unmatched = [d for d in result["discrepancies"] if d["type"] == "unmatched_claim"]
        assert len(unmatched) == 1
        assert unmatched[0]["claim_id"] == "101"

    def test_duplicate_detection(self):
        """Detecting duplicate claim IDs."""
        matched = pd.DataFrame([
            {"claim_id": "101", "payment_id": "201"},
            {"claim_id": "101", "payment_id": "202"}  # Duplicate claim_id
        ])
        raw_claims = pd.DataFrame([{"claim_id": "101", "amount": 1000}])
        raw_payments = pd.DataFrame([{"payment_id": "201"}, {"payment_id": "202"}])

        result = detect_discrepancies(matched, raw_claims, raw_payments)
        duplicates = [d for d in result["discrepancies"] if d["type"] == "duplicate"]
        assert len(duplicates) >= 1

    def test_summary_statistics(self):
        """Test summary statistics generation."""
        matched = pd.DataFrame([{"claim_id": "1", "payment_id": "1"}])
        raw_claims = pd.DataFrame([{"claim_id": "1"}])
        raw_payments = pd.DataFrame([{"payment_id": "1"}])

        result = detect_discrepancies(matched, raw_claims, raw_payments)
        summary = result["summary"]

        assert summary["total_claims"] == 1
        assert summary["matched_count"] == 1
        assert summary["match_rate_pct"] == 100.0

    def test_categorize_discrepancies_underpayment(self):
        """Test categorization of underpayment from matched records."""
        detector = DiscrepancyDetector()
        matched = pd.DataFrame([{
            "claim_id": "101",
            "payment_id": "201",
            "patient_name": "John Smith",
            "claim_amount": 1500.00,
            "payment_amount": 1400.00,
            "difference": 100.00,
            "discrepancy_type": "underpayment"
        }])
        existing = []
        result = detector.categorize_discrepancies(matched, existing)
        
        assert len(result) == 1
        assert result[0]["type"] == "underpayment"
        assert result[0]["difference"] == 100.00
        assert result[0]["severity"] == "medium"  # <= 100 is medium

    def test_categorize_discrepancies_underpayment_high(self):
        """Test high severity underpayment (>100)."""
        detector = DiscrepancyDetector()
        matched = pd.DataFrame([{
            "claim_id": "101",
            "payment_id": "201",
            "patient_name": "John Smith",
            "claim_amount": 1500.00,
            "payment_amount": 1300.00,
            "difference": 200.00,
            "discrepancy_type": "underpayment"
        }])
        existing = []
        result = detector.categorize_discrepancies(matched, existing)
        
        assert len(result) == 1
        assert result[0]["severity"] == "high"  # > 100

    def test_categorize_discrepancies_overpayment(self):
        """Test categorization of overpayment from matched records."""
        detector = DiscrepancyDetector()
        matched = pd.DataFrame([{
            "claim_id": "102",
            "payment_id": "202",
            "claim_amount": 1000.00,
            "payment_amount": 1100.00,
            "difference": -100.00,
            "discrepancy_type": "overpayment"
        }])
        existing = []
        result = detector.categorize_discrepancies(matched, existing)
        
        assert len(result) == 1
        assert result[0]["type"] == "overpayment"
        assert result[0]["difference"] == 100.00  # absolute value
        assert result[0]["severity"] == "medium"

    def test_detect_all_duplicate_payment_in_matched(self):
        """Test detection of duplicate payment_id in matched records (one payment used for multiple claims)."""
        detector = DiscrepancyDetector()
        matched = pd.DataFrame([
            {"claim_id": "101", "payment_id": "201"},
            {"claim_id": "102", "payment_id": "201"}  # Same payment, different claim
        ])
        raw_claims = pd.DataFrame([{"claim_id": "101"}, {"claim_id": "102"}])
        raw_payments = pd.DataFrame([{"payment_id": "201"}])
        
        result = detector.detect_all_discrepancies(matched, raw_claims, raw_payments)
        discrepancies = result["discrepancies"]
        
        # Look for duplicate with subtype "duplicate_payment_id"
        dupes = [d for d in discrepancies if d.get("subtype") == "duplicate_payment_id"]
        assert len(dupes) >= 1
        # Check severity is high
        assert all(d["severity"] == "high" for d in dupes)

    def test_detect_all_unmatched_payment(self):
        """Test detection of payments with no matching claim."""
        detector = DiscrepancyDetector()
        matched = pd.DataFrame()
        raw_claims = pd.DataFrame()  # No claims
        raw_payments = pd.DataFrame([
            {"payment_id": "201", "patient_name": "John", "amount": 1000}
        ])
        
        result = detector.detect_all_discrepancies(matched, raw_claims, raw_payments)
        discrepancies = result["discrepancies"]
        
        unmatched = [d for d in discrepancies if d["type"] == "unmatched_payment"]
        assert len(unmatched) == 1
        assert unmatched[0]["payment_id"] == "201"

    def test_flag_high_value_discrepancies(self):
        """Test high-value discrepancy flagging."""
        detector = DiscrepancyDetector()
        discrepancies = [
            {"type": "underpayment", "amount": 500, "difference": 500},
            {"type": "underpayment", "amount": 1500, "difference": 1500},  # high
            {"type": "duplicate", "amount": 0}
        ]
        
        result = detector.flag_high_value_discrepancies(discrepancies, threshold=1000.0)
        
        assert result[0]["priority"] == "normal"
        assert result[1]["priority"] == "high"
        assert "HIGH PRIORITY" in result[1]["reason"]
        assert result[2]["priority"] == "normal"

# ==================== REPORT GENERATOR TESTS ====================

class TestReportGenerator:
    """Test suite for report generation."""

    def test_csv_injection_prevention(self):
        """Ensure CSV reports sanitize dangerous values."""
        matched = pd.DataFrame([{
            "claim_id": "101",
            "payment_id": "201",
            "patient_name": "=1+1",  # Formula injection attempt
            "claim_amount": 1500.00,
            "payment_amount": 1400.00,
            "difference": 100.00,
            "discrepancy_type": "underpayment"
        }])
        discrepancies = [{
            "type": "underpayment",
            "claim_id": "101",
            "patient_name": "=cmd|'/c calc'!A1",  # Another attack vector
            "amount": 1500.00
        }]
        summary = {"total_claims": 1, "matched_count": 1}

        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        output = gen.generate_csv_report(matched, discrepancies, summary)

        with open(output, 'r') as f:
            content = f.read()

        # Ensure dangerous patterns are quoted or prefixed
        assert "'=1+1" in content or '"=1+1"' in content, "Formula not sanitized"
        assert "'=" in content or '"=' in content, "Potential injection not escaped"

        # Cleanup
        os.unlink(output)
        os.rmdir("test_reports")

    def test_csv_report_generation(self):
        """Test CSV report generation."""
        matched = pd.DataFrame([{
            "claim_id": "101",
            "payment_id": "201",
            "patient_name": "John Smith",
            "claim_amount": 1500.00,
            "payment_amount": 1400.00,
            "difference": 100.00,
            "discrepancy_type": "underpayment"
        }])
        discrepancies = [{
            "type": "underpayment",
            "claim_id": "101",
            "difference": 100.00
        }]
        summary = {"total_claims": 1, "matched_count": 1}

        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        output = gen.generate_csv_report(matched, discrepancies, summary)

        assert os.path.exists(output)
        with open(output, 'r') as f:
            content = f.read()
            assert "SUMMARY" in content
            assert "MATCHED RECORDS" in content
            assert "DISCREPANCIES" in content

        # Cleanup
        os.unlink(output)
        os.rmdir("test_reports")

    def test_json_report_generation(self):
        """Test JSON report generation."""
        matched = pd.DataFrame([{"claim_id": "101", "payment_id": "201"}])
        discrepancies = []
        summary = {"total_claims": 1}

        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        output = gen.generate_json_report(matched, discrepancies, summary)

        assert os.path.exists(output)
        import json
        with open(output, 'r') as f:
            data = json.load(f)
            assert "summary" in data
            assert data["summary"]["total_claims"] == 1

        # Cleanup
        os.unlink(output)
        os.rmdir("test_reports")

# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_pipeline(self):
        """Test complete reconciliation pipeline."""
        # Create sample data
        claims_raw = pd.DataFrame({
            "claim_id": ["101", "102", "103"],
            "patient_name": ["John Smith", "Jane Doe", "Unmatched Claim"],
            "date_of_service": ["2026-04-01", "2026-04-02", "2026-04-03"],
            "amount": [1500.00, 2000.00, 500.00],
            "provider_id": ["PRV123", "PRV456", "PRV789"],
            "insurer": ["Medicare", "Bupa", "Medibank"]
        })
        payments_raw = pd.DataFrame({
            "payment_id": ["201", "202"],
            "patient_name": ["John Smith", "Jane Doe"],
            "date_of_service": ["2026-04-01", "2026-04-02"],
            "amount": [1400.00, 2000.00],  # Underpayment on 101, exact on 102
            "provider_id": ["PRV123", "PRV456"],
            "insurer": ["Medicare", "Bupa"]
        })

        # Step 1: Clean
        claims = clean_data(claims_raw, "claims")
        payments = clean_data(payments_raw, "payments")

        # Step 2: Match
        matched, _ = match_claims_payments(claims, payments)

        # Step 3: Detect discrepancies
        result = detect_discrepancies(matched, claims_raw, payments_raw)
        summary = result["summary"]
        discrepancies = result["discrepancies"]

        # Assertions
        assert summary["total_claims"] == 3
        assert summary["matched_count"] == 2
        assert summary["match_rate_pct"] == pytest.approx(66.67, 0.1)
        assert summary["underpayments_count"] == 1
        assert summary["unmatched_claims"] == 1

        # Check underpayment detected
        underpayments = [d for d in discrepancies if d["type"] == "underpayment"]
        assert len(underpayments) == 1
        assert underpayments[0]["difference"] == 100.00

        # Check unmatched claim
        unmatched = [d for d in discrepancies if d["type"] == "unmatched_claim"]
        assert len(unmatched) == 1
        assert unmatched[0]["claim_id"] == "103"

# ==================== REPORT GENERATOR EXTENDED TESTS ====================

    def test_sanitize_csv_value_formula_injection(self):
        """Test sanitization of various formula injection strings."""
        from agents.report_generator import sanitize_csv_value
        
        # Test dangerous prefixes
        assert sanitize_csv_value("=1+1") == "'=1+1"
        assert sanitize_csv_value("+1+1") == "'+1+1"
        assert sanitize_csv_value("-1+1") == "'-1+1"
        assert sanitize_csv_value("@SUM(A1:A10)") == "'@SUM(A1:A10)"
        assert sanitize_csv_value("|cmd") == "'|cmd"
        assert sanitize_csv_value("\t tab") == "'\t tab"
        
        # Safe values unchanged
        assert sanitize_csv_value("normal_value") == "normal_value"
        assert sanitize_csv_value("123") == "123"
        assert sanitize_csv_value("") == ""
        assert sanitize_csv_value(None) == None  # None passes through
        
        # Non-string values unchanged
        assert sanitize_csv_value(123) == 123
        assert sanitize_csv_value(12.34) == 12.34

    def test_sanitize_dataframe_empty(self):
        """Test sanitizing empty DataFrame."""
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        empty_df = pd.DataFrame()
        result = gen._sanitize_dataframe(empty_df)
        
        assert result.empty
        pd.testing.assert_frame_equal(result, empty_df)
        
        os.rmdir("test_reports")

    def test_csv_report_empty_matched_and_discrepancies(self):
        """Test CSV generation when no matches or discrepancies."""
        matched = pd.DataFrame()
        discrepancies = []
        summary = {"total_claims": 0, "matched_count": 0}
        
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        csv_path = gen.generate_csv_report(matched, discrepancies, summary)
        
        assert os.path.exists(csv_path)
        with open(csv_path, 'r') as f:
            content = f.read()
            assert "No matched records" in content
            assert "No discrepancies found" in content
            assert "SECTION 1: SUMMARY" in content
        
        # Cleanup
        os.unlink(csv_path)
        os.rmdir("test_reports")

    def test_csv_report_only_matched(self):
        """Test CSV with matched records but no discrepancies."""
        matched = pd.DataFrame([{
            "claim_id": "101",
            "payment_id": "201",
            "patient_name": "John Smith",
            "claim_amount": 1500.0,
            "payment_amount": 1500.0,
            "match_score": 100.0,
            "discrepancy_type": "exact"
        }])
        discrepancies = []
        summary = {"total_claims": 1, "matched_count": 1}
        
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        csv_path = gen.generate_csv_report(matched, discrepancies, summary)
        
        assert os.path.exists(csv_path)
        with open(csv_path, 'r') as f:
            content = f.read()
            assert "patient_name" in content  # Header present
            assert "John Smith" in content
        
        os.unlink(csv_path)
        os.rmdir("test_reports")

    def test_csv_report_only_discrepancies(self):
        """Test CSV with discrepancies but no matched records."""
        matched = pd.DataFrame()
        discrepancies = [{
            "type": "unmatched_claim",
            "claim_id": "999",
            "patient_name": "Jane Doe",
            "amount": 500.0,
            "reason": "No payment matched"
        }]
        summary = {"total_claims": 1, "matched_count": 0}
        
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        csv_path = gen.generate_csv_report(matched, discrepancies, summary)
        
        assert os.path.exists(csv_path)
        with open(csv_path, 'r') as f:
            content = f.read()
            assert "type" in content  # Discrepancy header
            assert "unmatched_claim" in content
        
        os.unlink(csv_path)
        os.rmdir("test_reports")

    def test_generate_json_report_empty_data(self):
        """Test JSON report with empty inputs."""
        matched = pd.DataFrame()
        discrepancies = []
        summary = {"total_claims": 0, "matched_count": 0}
        
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        json_path = gen.generate_json_report(matched, discrepancies, summary)
        
        assert os.path.exists(json_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
            assert data["summary"] == summary
            assert data["matched_count"] == 0
            assert data["discrepancy_count"] == 0
            # matched_records key should NOT be present when empty (per implementation)
            assert "matched_records" not in data
        
        os.unlink(json_path)
        os.rmdir("test_reports")

    def test_generate_json_report_with_data(self):
        """Test JSON report includes matched_records when present."""
        matched = pd.DataFrame([{
            "claim_id": "101",
            "payment_id": "201",
            "patient_name": "John Smith",
            "claim_amount": 1500.0,
            "match_score": 100.0
        }])
        discrepancies = [{"type": "underpayment", "claim_id": "101"}]
        summary = {"total_claims": 1, "matched_count": 1}
        
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        json_path = gen.generate_json_report(matched, discrepancies, summary)
        
        with open(json_path, 'r') as f:
            data = json.load(f)
            assert "matched_records" in data
            assert len(data["matched_records"]) == 1
            assert data["matched_records"][0]["claim_id"] == "101"
        
        os.unlink(json_path)
        os.rmdir("test_reports")

    def test_generate_pdf_report_without_reportlab(self, monkeypatch):
        """Test PDF generation when reportlab is missing."""
        import importlib
        
        # Simulate reportlab missing
        original_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name.startswith('reportlab'):
                raise ImportError("reportlab not available")
            return original_import(name, *args, **kwargs)
        
        monkeypatch.setattr(builtins, '__import__', mock_import)
        
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        matched = pd.DataFrame([{"claim_id": "101", "payment_id": "201"}])
        discrepancies = []
        summary = {"total_claims": 1, "matched_count": 1}
        
        pdf_path = gen.generate_pdf_report(matched, discrepancies, summary)
        
        assert pdf_path == ""  # Should return empty string when reportlab missing
        
        os.rmdir("test_reports")

    def test_generate_pdf_report_with_reportlab(self):
        """Test PDF generation when reportlab is available."""
        try:
            from reportlab.lib.pagesizes import letter
        except ImportError:
            pytest.skip("reportlab not installed")
        
        matched = pd.DataFrame([{
            "claim_id": "101",
            "payment_id": "201",
            "patient_name": "John Smith",
            "claim_amount": 1500.0,
            "payment_amount": 1500.0
        }])
        discrepancies = [{
            "type": "underpayment",
            "patient_name": "Jane Doe",
            "difference": 100.0,
            "reason": "Payment less than claim",
            "priority": "high"
        }]
        summary = {
            "total_claims": 2,
            "total_payments": 2,
            "matched_count": 1,
            "match_rate_pct": 50.0,
            "underpayments_count": 1,
            "overpayments_count": 0,
            "duplicates_count": 0,
            "total_discrepancy_value": 100.0,
            "high_priority_count": 1
        }
        
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        pdf_path = gen.generate_pdf_report(matched, discrepancies, summary)
        
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith('.pdf')
        assert os.path.getsize(pdf_path) > 0
        
        # Cleanup
        os.unlink(pdf_path)
        os.rmdir("test_reports")

    def test_generate_report_format_csv(self):
        """Test generate_report with format='csv'."""
        matched = pd.DataFrame([{"claim_id": "101", "payment_id": "201"}])
        discrepancies = []
        summary = {"total_claims": 1, "matched_count": 1}
        
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        outputs = gen.generate_report(matched, discrepancies, summary, format="csv")
        
        assert "csv" in outputs
        assert os.path.exists(outputs["csv"])
        assert "pdf" not in outputs
        assert "json" not in outputs
        
        os.unlink(outputs["csv"])
        os.rmdir("test_reports")

    def test_generate_report_format_json(self):
        """Test generate_report with format='json'."""
        matched = pd.DataFrame([{"claim_id": "101"}])
        discrepancies = [{"type": "test"}]
        summary = {"total_claims": 1}
        
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        outputs = gen.generate_report(matched, discrepancies, summary, format="json")
        
        assert "json" in outputs
        assert os.path.exists(outputs["json"])
        
        os.unlink(outputs["json"])
        os.rmdir("test_reports")

    def test_generate_report_format_all(self):
        """Test generate_report with format='all'."""
        matched = pd.DataFrame([{"claim_id": "101"}])
        discrepancies = []
        summary = {"total_claims": 1}
        
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        outputs = gen.generate_report(matched, discrepancies, summary, format="all")
        
        assert "csv" in outputs
        assert "json" in outputs
        # PDF may or may not be present depending on reportlab
        if "pdf" in outputs:
            assert os.path.exists(outputs["pdf"])
            os.unlink(outputs["pdf"])
        
        os.unlink(outputs["csv"])
        os.unlink(outputs["json"])
        os.rmdir("test_reports")

    def test_report_generator_path_traversal_protection(self):
        """Test that report directory validation prevents path traversal."""
        # Should reject paths outside project
        with pytest.raises(ValueError, match="outside project"):
            gen = ReportGenerator(report_dir="/etc/passwd")
        
        # Should accept relative paths (within project)
        gen = ReportGenerator(report_dir="test_reports")
        assert os.path.exists("test_reports")
        os.rmdir("test_reports")

    def test_convenience_function(self):
        """Test the generate_report convenience function."""
        matched = pd.DataFrame([{"claim_id": "101"}])
        discrepancies = []
        summary = {"total_claims": 1}
        
        outputs = generate_report(matched, discrepancies, summary, format="csv")
        
        assert "csv" in outputs
        assert os.path.exists(outputs["csv"])
        os.unlink(outputs["csv"])

    def test_pdf_discrepancy_truncation(self):
        """Test that PDF truncates long discrepancy reasons."""
        if not importlib.util.find_spec("reportlab"):
            pytest.skip("reportlab not installed")
        
        matched = pd.DataFrame()
        discrepancies = [{
            "type": "underpayment",
            "patient_name": "Test Patient",
            "difference": 100.0,
            "reason": "x" * 200,  # Very long reason
            "priority": "normal"
        }]
        summary = {"total_claims": 0, "matched_count": 0}
        
        gen = ReportGenerator(report_dir="test_reports")
        os.makedirs("test_reports", exist_ok=True)
        
        pdf_path = gen.generate_pdf_report(matched, discrepancies, summary)
        

# ==================== HELPER FUNCTIONS TESTS ====================

class TestHelpers:
    """Test suite for helper utility functions."""

    # clean_name tests
    def test_clean_name_with_nan(self):
        """Test clean_name with NaN returns empty string."""
        assert clean_name(pd.NA) == ""
        assert clean_name(None) == ""

    def test_clean_name_basic(self):
        """Test clean_name with basic inputs."""
        assert clean_name("  John  Smith  ") == "John Smith"
        assert clean_name("J. Smith") == "J Smith"
        assert clean_name("jane doe") == "Jane Doe"

    # standardize_date tests
    def test_standardize_date_with_nan(self):
        """Test standardize_date with NaN returns None."""
        assert standardize_date(pd.NA) is None
        assert standardize_date(None) is None

    def test_standardize_date_valid_formats(self):
        """Test standardize_date with valid Australian formats."""
        # ISO format
        dt = standardize_date("2026-04-01")
        assert dt == datetime(2026, 4, 1)
        # UK format
        dt = standardize_date("01/04/2026")
        assert dt == datetime(2026, 4, 1)
        # Dash format
        dt = standardize_date("01-04-2026")
        assert dt == datetime(2026, 4, 1)
        # Slash format with YYYY first
        dt = standardize_date("2026/04/01")
        assert dt == datetime(2026, 4, 1)

    def test_standardize_date_invalid(self):
        """Test standardize_date with unparseable date returns None."""
        assert standardize_date("99/99/9999") is None
        assert standardize_date("invalid-date-string") is None
        assert standardize_date("") is None

    # clean_amount tests
    def test_clean_amount_with_nan(self):
        """Test clean_amount with NaN returns 0.0."""
        assert clean_amount(pd.NA) == 0.0
        assert clean_amount(None) == 0.0

    def test_clean_amount_valid(self):
        """Test clean_amount with valid amount strings."""
        assert clean_amount("$1,500.00") == 1500.0
        assert clean_amount("2000") == 2000.0
        assert clean_amount("  $350.50 ") == 350.5

    def test_clean_amount_invalid(self):
        """Test clean_amount with unparseable string returns 0.0."""
        assert clean_amount("abc") == 0.0
        assert clean_amount("---") == 0.0
        assert clean_amount("not-a-number") == 0.0

    # validate_columns tests
    def test_validate_columns_all_present(self):
        """Test validate_columns when all required columns present."""
        df = pd.DataFrame({"a": [1], "b": [2]})
        valid, missing = validate_columns(df, ["a", "b"])
        assert valid is True
        assert missing == []

    def test_validate_columns_missing(self):
        """Test validate_columns when some columns missing."""
        df = pd.DataFrame({"a": [1]})
        valid, missing = validate_columns(df, ["a", "b", "c"])
        assert valid is False
        assert set(missing) == {"b", "c"}

    # calculate_amount_difference tests
    def test_calculate_amount_difference_exact_match(self):
        """Test exact amount match returns True."""
        assert calculate_amount_difference(1000, 1000, 0.01, 10.0) is True

    def test_calculate_amount_difference_within_absolute(self):
        """Test amounts within absolute tolerance."""
        # diff=8 < 10 -> True
        assert calculate_amount_difference(1000, 1008, 0.01, 10.0) is True
        # diff=10 exactly -> True
        assert calculate_amount_difference(1000, 1010, 0.01, 10.0) is True

    def test_calculate_amount_difference_within_percentage(self):
        """Test amounts within percentage tolerance (absolute diff > abs tolerance)."""
        # 1000 vs 1010: diff=10, abs_tol=5, so abs fails; avg=1005, diff/avg≈0.00995 < 0.01 -> True
        assert calculate_amount_difference(1000, 1010, 0.01, 5.0) is True

    def test_calculate_amount_difference_false_branch(self):
        """Test amounts outside both tolerances returns False."""
        # 1000 vs 2000: diff=1000 > 10, diff/avg=0.666 > 0.01
        assert calculate_amount_difference(1000, 2000, 0.01, 10.0) is False

    def test_calculate_amount_difference_avg_zero_edge(self):
        """Test when both amounts are zero (avg=0) returns True because diff<=abs_tol."""
        assert calculate_amount_difference(0, 0, 0.01, 10.0) is True

    # dates_within_tolerance tests
    def test_dates_within_tolerance_exact(self):
        """Test dates exactly same."""
        d1 = datetime(2026, 4, 1)
        d2 = datetime(2026, 4, 1)
        assert dates_within_tolerance(d1, d2, 0) is True
        assert dates_within_tolerance(d1, d2, 2) is True

    def test_dates_within_tolerance_within_range(self):
        """Test dates within tolerance."""
        d1 = datetime(2026, 4, 1)
        d2 = datetime(2026, 4, 2)
        assert dates_within_tolerance(d1, d2, 2) is True
        assert dates_within_tolerance(d1, d2, 1) is True

    def test_dates_within_tolerance_outside_range(self):
        """Test dates outside tolerance returns False."""
        d1 = datetime(2026, 4, 1)
        d2 = datetime(2026, 4, 10)
        assert dates_within_tolerance(d1, d2, 5) is False

    def test_dates_within_tolerance_nat(self):
        """Test dates with NaT returns False."""
        nat = pd.NaT
        d = datetime(2026, 4, 1)
        assert dates_within_tolerance(nat, d, 2) is False
        assert dates_within_tolerance(d, nat, 2) is False
        assert dates_within_tolerance(nat, nat, 2) is False


# ==================== FILE INGESTOR ADDITIONAL TESTS ====================

class TestFileIngestorAdditional:
    """Additional tests for FileIngestor to reach 100% coverage."""

    def test_ingest_file_json_via_ingest_file(self):
        """Test ingest_file with .json extension uses ingest_json."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([{"claim_id": "101", "patient_name": "Test", "date_of_service": "2026-04-01", "amount": "1000", "provider_id": "PRV1", "insurer": "Medicare"}], f)
            temp_path = f.name
        try:
            ingestor = FileIngestor()
            df = ingestor.ingest_file(temp_path, "claims")
            assert len(df) == 1
            assert df.iloc[0]["claim_id"] == "101"
        finally:
            os.unlink(temp_path)

    def test_ingest_file_edi_via_ingest_file(self, monkeypatch):
        """Test ingest_file with .edi extension uses ingest_edi branch."""
        # Create a dummy EDI file (content doesn't matter as we'll mock ingest_edi)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.edi', delete=False) as f:
            f.write("ISA*...")
            temp_path = f.name
        try:
            ingestor = FileIngestor()
            # Mock ingest_edi to return a valid DataFrame so validation passes
            def mock_ingest_edi(fp):
                return pd.DataFrame({
                    "claim_id": ["EDI1"],
                    "patient_name": ["Test Patient"],
                    "date_of_service": ["2026-04-01"],
                    "amount": ["1000"],
                    "provider_id": ["PRV1"],
                    "insurer": ["Medicare"]
                })
            monkeypatch.setattr(ingestor, 'ingest_edi', mock_ingest_edi)
            df = ingestor.ingest_file(temp_path, "claims")
            assert len(df) == 1
            assert df.iloc[0]["claim_id"] == "EDI1"
        finally:
            os.unlink(temp_path)

    def test_ingest_csv_exception_handling(self):
        """Test that ingest_csv propagates parsing exceptions."""
        # Create a malformed CSV that will cause pandas to raise
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write('col1,col2\n"unclosed quote,123,456\n')  # Malformed CSV
            temp_path = f.name
        try:
            ingestor = FileIngestor()
            with pytest.raises(Exception):  # Could be pandas.errors.ParserError
                ingestor.ingest_csv(temp_path)
        finally:
            os.unlink(temp_path)

    def test_ingest_json_exception_handling(self):
        """Test that ingest_json propagates parsing exceptions."""
        # Create malformed JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json')  # Malformed
            temp_path = f.name
        try:
            ingestor = FileIngestor()
            with pytest.raises(Exception):  # Could be json.JSONDecodeError
                ingestor.ingest_json(temp_path)
        finally:
            os.unlink(temp_path)

    def test_ingest_file_unsupported_extension_after_validation_bypass(self, monkeypatch):
        """Test ingest_file else branch for unsupported extension by bypassing validation."""
        # Create a temp file with .txt but we'll mock validate_file to return True
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(b"content")
            temp_path = f.name
        try:
            ingestor = FileIngestor()
            # Monkeypatch validate_file to always succeed
            monkeypatch.setattr(ingestor, 'validate_file', lambda fp: (True, ""))
            with pytest.raises(ValueError, match="Unsupported format"):
                ingestor.ingest_file(temp_path, "claims")
        finally:
            os.unlink(temp_path)

