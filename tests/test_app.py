"""
Tests for CLI and Streamlit App.
"""
import pytest
import subprocess
import sys
import os

# CLI tests
class TestCLI:
    """Test command-line interface."""

    def test_cli_help(self):
        """Test CLI help message."""
        result = subprocess.run(
            [sys.executable, "src/app/cli.py", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "claims reconciliation" in result.stdout.lower()
        assert "--claims" in result.stdout

    def test_cli_missing_args(self):
        """Test CLI without required arguments."""
        result = subprocess.run(
            [sys.executable, "src/app/cli.py"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower()

    def test_cli_with_sample_data(self):
        """Test CLI with sample data files."""
        claims = "src/data/sample_claims.csv"
        payments = "src/data/sample_payments.csv"

        if not os.path.exists(claims) or not os.path.exists(payments):
            pytest.skip("Sample data not found")

        result = subprocess.run(
            [sys.executable, "src/app/cli.py",
             "--claims", claims,
             "--payments", payments,
             "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "reconciliation complete" in result.stdout.lower()
        assert "reports/" in result.stdout

    def test_cli_invalid_file(self):
        """Test CLI with non-existent file."""
        result = subprocess.run(
            [sys.executable, "src/app/cli.py",
             "--claims", "nonexistent.csv",
             "--payments", "src/data/sample_payments.csv"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()
