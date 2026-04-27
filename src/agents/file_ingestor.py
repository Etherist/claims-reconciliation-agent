"""File Ingestor Agent - Parses claims/payment files into structured DataFrames."""
import pandas as pd
import logging
import tempfile
from pathlib import Path
from typing import Tuple, Optional
from utils.helpers import validate_columns
from utils.config import Config

logger = logging.getLogger(__name__)

# Required columns for claims and payments files
CLAIMS_REQUIRED_COLS = ["claim_id", "patient_name", "date_of_service", "amount", "provider_id", "insurer"]
PAYMENTS_REQUIRED_COLS = ["payment_id", "patient_name", "date_of_service", "amount", "provider_id", "insurer"]

class FileIngestor:
    """Agent responsible for ingesting and parsing transaction files."""

    def __init__(self, max_file_size_mb: int = Config.MAX_FILE_SIZE_MB) -> None:
        """
        Initialize File Ingestor.

        Args:
            max_file_size_mb: Maximum allowed file size in megabytes
        """
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate file existence, size, extension, and path safety.

        Security: Prevents path traversal by ensuring resolved path is within
        project directory or system temp directory.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(file_path).resolve()
        base_dir = Path.cwd().resolve()
        temp_dir = Path(tempfile.gettempdir()).resolve()

        # Allow only paths inside project dir or system temp (for testing)
        try:
            path.relative_to(base_dir)
        except ValueError:
            try:
                path.relative_to(temp_dir)
            except ValueError:
                return False, f"File path outside allowed directories: {file_path}"

        if not path.exists():
            return False, f"File not found: {file_path}"

        if path.stat().st_size > self.max_file_size_bytes:
            return False, f"File too large (max {Config.MAX_FILE_SIZE_MB}MB)"

        if path.suffix.lower() not in [".csv", ".json", ".edi"]:
            return False, f"Unsupported file format: {path.suffix}"

        return True, ""

    def ingest_csv(self, file_path: str) -> pd.DataFrame:
        """
        Parse CSV file into DataFrame.

        Args:
            file_path: Path to CSV file

        Returns:
            pandas DataFrame with all columns as strings
        """
        try:
            df = pd.read_csv(file_path, dtype=str)
            logger.info(f"Successfully ingested CSV: {file_path}, shape={df.shape}")
            return df
        except Exception as e:
            logger.error(f"Failed to parse CSV {file_path}: {e}")
            raise

    def ingest_json(self, file_path: str) -> pd.DataFrame:
        """
        Parse JSON file into DataFrame.

        Args:
            file_path: Path to JSON file

        Returns:
            pandas DataFrame
        """
        try:
            df = pd.read_json(file_path, dtype=False)
            logger.info(f"Successfully ingested JSON: {file_path}, shape={df.shape}")
            return df
        except Exception as e:
            logger.error(f"Failed to parse JSON {file_path}: {e}")
            raise

    def ingest_edi(self, file_path: str) -> pd.DataFrame:
        """
        Parse EDI file into DataFrame.

        Note: This is a stub for future implementation. Currently returns
        an empty DataFrame. Production version would use an EDI parser library
        (e.g., edi-parser) and map EDI segments to DataFrame columns.

        Args:
            file_path: Path to EDI file

        Returns:
            Empty pandas DataFrame (placeholder)
        """
        logger.warning("EDI parsing not yet fully implemented - returning empty DataFrame")
        return pd.DataFrame()

    def ingest_file(self, file_path: str, file_type: str) -> pd.DataFrame:
        """
        Main entry point: ingest file based on type.

        Args:
            file_path: Path to file
            file_type: Either 'claims' or 'payments'

        Returns:
            pandas DataFrame with raw data

        Raises:
            ValueError: If validation fails or required columns missing
        """
        logger.info(f"Ingesting {file_type} file: {file_path}")

        # Validate file
        is_valid, error_msg = self.validate_file(file_path)
        if not is_valid:
            raise ValueError(f"Invalid file: {error_msg}")

        # Parse based on extension
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension == ".csv":
            df = self.ingest_csv(file_path)
        elif extension == ".json":
            df = self.ingest_json(file_path)
        elif extension == ".edi":
            df = self.ingest_edi(file_path)
        else:
            raise ValueError(f"Unsupported format: {extension}")

        # Validate required columns based on file type
        required_cols = CLAIMS_REQUIRED_COLS if file_type == "claims" else PAYMENTS_REQUIRED_COLS
        is_valid, missing = validate_columns(df, required_cols)

        if not is_valid:
            raise ValueError(f"Missing required columns in {file_type} file: {missing}")

        logger.info(f"Ingestion complete: {len(df)} rows, columns={list(df.columns)}")
        return df


def ingest_file(file_path: str, file_type: str) -> pd.DataFrame:
    """
    Convenience function for file ingestion.

    Args:
        file_path: Path to input file
        file_type: Either 'claims' or 'payments'

    Returns:
        Raw pandas DataFrame
    """
    ingestor = FileIngestor()
    return ingestor.ingest_file(file_path, file_type)
