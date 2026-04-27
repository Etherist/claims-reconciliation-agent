"""Data Cleaner Agent - Standardizes and normalizes transaction data."""
import pandas as pd
import logging
from datetime import datetime
from typing import Tuple
from utils.helpers import clean_name, standardize_date, clean_amount

logger = logging.getLogger(__name__)

class DataCleaner:
    """Agent responsible for cleaning and standardizing claim/payment data."""

    def __init__(self) -> None:
        """Initialize Data Cleaner."""
        pass

    def clean_patient_names(self, df: pd.DataFrame, column: str = "patient_name") -> pd.DataFrame:
        """
        Standardize patient names: strip whitespace, convert to title case, remove periods.

        Example: "J. Smith" → "J Smith", "  jane doe  " → "Jane Doe"

        Args:
            df: Input DataFrame
            column: Column containing patient names (default: 'patient_name')

        Returns:
            DataFrame with cleaned names in the same column
        """
        df = df.copy()
        df[column] = df[column].apply(clean_name)
        logger.info(f"Cleaned patient names in {len(df)} rows")
        return df

    def clean_dates(self, df: pd.DataFrame, column: str = "date_of_service") -> pd.DataFrame:
        """
        Parse date strings and create a new datetime column.

        Supported formats: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, YYYY/MM/DD
        Unparseable dates become NaT (Not a Time).

        Args:
            df: Input DataFrame
            column: Column containing date strings (default: 'date_of_service')

        Returns:
            DataFrame with new '{column}_dt' column containing datetime objects
        """
        df = df.copy()
        df[f"{column}_dt"] = df[column].apply(standardize_date)
        logger.info(f"Standardized dates in column '{column}'")
        return df

    def clean_amounts(self, df: pd.DataFrame, column: str = "amount") -> pd.DataFrame:
        """
        Convert amount strings to numeric floats.

        Removes currency symbols ($, £, €) and commas, then converts to float.

        Args:
            df: Input DataFrame
            column: Column containing amount strings (default: 'amount')

        Returns:
            DataFrame with new '{column}_clean' column containing numeric amounts
        """
        df = df.copy()
        df[f"{column}_clean"] = df[column].apply(clean_amount)
        logger.info(f"Cleaned amounts in column '{column}'")
        return df

    def clean_dataframe(
        self,
        df: pd.DataFrame,
        file_type: str,
        id_column: str = None
    ) -> pd.DataFrame:
        """
        Apply complete cleaning pipeline to a DataFrame.

        Steps:
        1. Convert string columns to strings (handle NaN)
        2. Clean patient names (title case, no punctuation)
        3. Parse dates → {column}_dt
        4. Convert amounts → numeric
        5. Standardize insurer names to title case
        6. Ensure ID columns are strings for consistent matching

        Args:
            df: Raw input DataFrame
            file_type: Either 'claims' or 'payments' (determines ID column)
            id_column: Optional explicit ID column name (auto-detected if None)

        Returns:
            Cleaned DataFrame ready for matching
        """
        logger.info(f"Starting data cleaning for {file_type} file")

        df_clean = df.copy()

        # Ensure string columns are strings (convert NaN to empty string)
        for col in ["patient_name", "provider_id", "insurer"]:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str).fillna("")

        # Apply cleaning steps
        df_clean = self.clean_patient_names(df_clean)
        df_clean = self.clean_dates(df_clean)

        amount_col = "amount"
        df_clean = self.clean_amounts(df_clean, column=amount_col)
        df_clean[amount_col] = df_clean[f"{amount_col}_clean"]
        df_clean.drop(columns=[f"{amount_col}_clean"], inplace=True)

        # Ensure ID column is string for consistent matching
        id_col = id_column or ("claim_id" if file_type == "claims" else "payment_id")
        if id_col in df_clean.columns:
            df_clean[id_col] = df_clean[id_col].astype(str)

        # Standardize insurer names (title case)
        if "insurer" in df_clean.columns:
            df_clean["insurer"] = df_clean["insurer"].str.title()

        logger.info(f"Data cleaning complete: {len(df_clean)} rows")
        return df_clean


def clean_data(df: pd.DataFrame, file_type: str) -> pd.DataFrame:
    """
    Convenience function to clean data.

    Args:
        df: Raw DataFrame
        file_type: 'claims' or 'payments'

    Returns:
        Cleaned DataFrame
    """
    cleaner = DataCleaner()
    return cleaner.clean_dataframe(df, file_type)
