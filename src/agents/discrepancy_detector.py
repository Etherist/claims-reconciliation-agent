"""Discrepancy Detector Agent - Flags issues in matched and unmatched records."""
import pandas as pd
import logging
from typing import List, Dict
from utils.config import Config
from utils.helpers import clean_amount

logger = logging.getLogger(__name__)

class DiscrepancyDetector:
    """Agent responsible for detecting and categorizing discrepancies."""

    def __init__(self) -> None:
        """Initialize Discrepancy Detector."""
        pass

    def detect_duplicates(
        self,
        matched_df: pd.DataFrame,
        column: str = "claim_id"
    ) -> List[Dict]:
        """
        Detect duplicate IDs in matched records.

        Args:
            matched_df: DataFrame of matched claim-payment pairs
            column: Column to check for duplicates

        Returns:
            List of duplicate discrepancy records
        """
        duplicates = []
        if column in matched_df.columns:
            dup_counts = matched_df[column].value_counts()
            dup_values = dup_counts[dup_counts > 1]

            for val, count in dup_values.items():
                dup_rows = matched_df[matched_df[column] == val]
                for idx, row in dup_rows.iterrows():
                    duplicates.append({
                        "type": "duplicate",
                        "subtype": f"duplicate_{column}",
                        "claim_id": row.get("claim_id", ""),
                        "payment_id": row.get("payment_id", ""),
                        "patient_name": row.get("patient_name", ""),
                        "amount": row.get("claim_amount", 0),
                        "reason": f"Duplicate {column}: {val} appears {count} times",
                        "severity": "high"
                    })

        return duplicates

    def categorize_discrepancies(
        self,
        matched_df: pd.DataFrame,
        existing_discrepancies: List[Dict]
    ) -> List[Dict]:
        """
        Categorize discrepancies from matched records (underpayments, overpayments).

        Args:
            matched_df: DataFrame of matched pairs
            existing_discrepancies: List of existing discrepancy dicts

        Returns:
            Extended list of categorized discrepancies
        """
        discrepancies = existing_discrepancies.copy()

        if "discrepancy_type" in matched_df.columns:
            for _, row in matched_df.iterrows():
                disc_type = row["discrepancy_type"]

                if disc_type == "underpayment":
                    discrepancy = {
                        "type": "underpayment",
                        "claim_id": row.get("claim_id", ""),
                        "payment_id": row.get("payment_id", ""),
                        "patient_name": row.get("patient_name", ""),
                        "claim_amount": row.get("claim_amount", 0),
                        "payment_amount": row.get("payment_amount", 0),
                        "difference": row.get("difference", 0),
                        "reason": "Payment less than claimed amount",
                        "severity": "high" if row.get("difference", 0) > 100 else "medium"
                    }
                    discrepancies.append(discrepancy)

                elif disc_type == "overpayment":
                    discrepancy = {
                        "type": "overpayment",
                        "claim_id": row.get("claim_id", ""),
                        "payment_id": row.get("payment_id", ""),
                        "patient_name": row.get("patient_name", ""),
                        "claim_amount": row.get("claim_amount", 0),
                        "payment_amount": row.get("payment_amount", 0),
                        "difference": abs(row.get("difference", 0)),
                        "reason": "Payment exceeds claimed amount",
                        "severity": "medium"
                    }
                    discrepancies.append(discrepancy)

        return discrepancies

    def flag_high_value_discrepancies(
        self,
        discrepancies: List[Dict],
        threshold: float = 1000.0
    ) -> List[Dict]:
        """
        Flag high-value discrepancies for priority attention.

        Args:
            discrepancies: List of all discrepancies
            threshold: Minimum dollar amount to flag as high priority

        Returns:
            Updated list with priority flags
        """
        for disc in discrepancies:
            amount_field = "difference" if "difference" in disc else "amount"
            amount = abs(disc.get(amount_field, 0))

            if amount >= threshold:
                disc["priority"] = "high"
                disc["reason"] = f"HIGH PRIORITY: {disc.get('reason', '')}"
            else:
                disc["priority"] = "normal"

        return discrepancies

    def detect_all_discrepancies(
        self,
        matched_df: pd.DataFrame,
        raw_claims: pd.DataFrame,
        raw_payments: pd.DataFrame
    ) -> Dict[str, List[Dict]]:
        """
        Run all discrepancy detection analyses.

        Args:
            matched_df: DataFrame of matched pairs
            raw_claims: Original claims DataFrame
            raw_payments: Original payments DataFrame

        Returns:
            Dictionary with categorized discrepancies
        """
        logger.info("Starting discrepancy detection")

        all_discrepancies = []

        # 1. Extract underpayments/overpayments from matched records
        matched_discrepancies = []
        for _, row in matched_df.iterrows():
            disc_type = row.get("discrepancy_type")
            if disc_type and disc_type != "exact":
                record = {
                    "type": disc_type,
                    "claim_id": row.get("claim_id", ""),
                    "payment_id": row.get("payment_id", ""),
                    "patient_name": row.get("patient_name", ""),
                    "claim_amount": row.get("claim_amount", 0),
                    "payment_amount": row.get("payment_amount", 0),
                    "difference": abs(row.get("difference", 0)),
                    "match_score": row.get("match_score", 0),
                    "reason": f"{disc_type.title()}: Payment ${row.get('payment_amount', 0):.2f} vs Claim ${row.get('claim_amount', 0):.2f}",
                    "severity": "high" if disc_type == "underpayment" else "medium"
                }
                matched_discrepancies.append(record)

        all_discrepancies.extend(matched_discrepancies)

        # 2. Check for duplicate claim IDs in original claims
        claim_duplicates = self.detect_duplicates(raw_claims, "claim_id")
        all_discrepancies.extend(claim_duplicates)

        # 3. Check for duplicate payment IDs in original payments
        payment_duplicates = self.detect_duplicates(raw_payments, "payment_id")
        all_discrepancies.extend(payment_duplicates)

        # 4. Check for duplicate matches (same claim or payment appears in matched pairs multiple times)
        if not matched_df.empty:
            # Duplicate claim_id in matched (one claim matched to multiple payments)
            matched_claim_dups = self.detect_duplicates(matched_df, "claim_id")
            for d in matched_claim_dups:
                d["reason"] = f"Claim {d['claim_id']} matched to multiple payments"
                d["severity"] = "high"
            all_discrepancies.extend(matched_claim_dups)

            # Duplicate payment_id in matched (one payment used for multiple claims)
            matched_payment_dups = self.detect_duplicates(matched_df, "payment_id")
            for d in matched_payment_dups:
                d["reason"] = f"Payment {d['payment_id']} matched to multiple claims"
                d["severity"] = "high"
            all_discrepancies.extend(matched_payment_dups)

        # 5. Detect unmatched claims (claims with no matching payment)
        matched_claim_ids = set(matched_df["claim_id"].astype(str)) if not matched_df.empty else set()
        for _, claim in raw_claims.iterrows():
            claim_id_str = str(claim.get("claim_id", ""))
            if claim_id_str not in matched_claim_ids:
                raw_amount = claim.get("amount", 0)
                amount = clean_amount(str(raw_amount)) if not isinstance(raw_amount, (int, float)) else float(raw_amount)
                all_discrepancies.append({
                    "type": "unmatched_claim",
                    "claim_id": claim_id_str,
                    "patient_name": claim.get("patient_name", ""),
                    "date_of_service": claim.get("date_of_service", ""),
                    "amount": amount,
                    "provider_id": claim.get("provider_id", ""),
                    "insurer": claim.get("insurer", ""),
                    "reason": "No payment matched to this claim",
                    "severity": "medium"
                })

        # 5. Detect unmatched payments (payments with no matching claim)
        matched_payment_ids = set(matched_df["payment_id"].astype(str)) if not matched_df.empty else set()
        for _, payment in raw_payments.iterrows():
            payment_id_str = str(payment.get("payment_id", ""))
            if payment_id_str not in matched_payment_ids:
                raw_amount = payment.get("amount", 0)
                amount = clean_amount(str(raw_amount)) if not isinstance(raw_amount, (int, float)) else float(raw_amount)
                all_discrepancies.append({
                    "type": "unmatched_payment",
                    "payment_id": payment_id_str,
                    "patient_name": payment.get("patient_name", ""),
                    "date_of_service": payment.get("date_of_service", ""),
                    "amount": amount,
                    "provider_id": payment.get("provider_id", ""),
                    "insurer": payment.get("insurer", ""),
                    "reason": "No claim matched to this payment",
                    "severity": "medium"
                })

        # 6. Flag high-value discrepancies
        all_discrepancies = self.flag_high_value_discrepancies(all_discrepancies)

        # 7. Generate summary statistics
        summary = self._generate_summary(all_discrepancies, matched_df, raw_claims, raw_payments)

        logger.info(f"Detected {len(all_discrepancies)} total discrepancies")
        return {
            "discrepancies": all_discrepancies,
            "summary": summary
        }

    def _generate_summary(
        self,
        discrepancies: List[Dict],
        matched_df: pd.DataFrame,
        raw_claims: pd.DataFrame,
        raw_payments: pd.DataFrame
    ) -> Dict:
        """Generate summary statistics."""
        total_claims = len(raw_claims)
        total_payments = len(raw_payments)
        matched_count = len(matched_df)
        unmatched_claims = total_claims - matched_count
        unmatched_payments = total_payments - matched_count

        underpayments = [d for d in discrepancies if d["type"] == "underpayment"]
        overpayments = [d for d in discrepancies if d["type"] == "overpayment"]
        duplicates = [d for d in discrepancies if d["type"] == "duplicate"]
        unmatched_claim_disc = [d for d in discrepancies if d["type"] == "unmatched_claim"]
        unmatched_payment_disc = [d for d in discrepancies if d["type"] == "unmatched_payment"]

        total_discrepancy_value = sum(d.get("difference", 0) for d in discrepancies)

        return {
            "total_claims": total_claims,
            "total_payments": total_payments,
            "matched_count": matched_count,
            "match_rate_pct": round(matched_count / total_claims * 100, 1) if total_claims > 0 else 0,
            "unmatched_claims": unmatched_claims,
            "unmatched_payments": unmatched_payments,
            "underpayments_count": len(underpayments),
            "overpayments_count": len(overpayments),
            "duplicates_count": len(duplicates),
            "total_discrepancy_value": round(total_discrepancy_value, 2),
            "high_priority_count": len([d for d in discrepancies if d.get("priority") == "high"])
        }


def detect_discrepancies(
    matched_df: pd.DataFrame,
    raw_claims: pd.DataFrame,
    raw_payments: pd.DataFrame
) -> Dict[str, List[Dict]]:
    """
    Convenience function for discrepancy detection.

    Args:
        matched_df: Matched claims-payments DataFrame
        raw_claims: Original claims data
        raw_payments: Original payments data

    Returns:
        Dictionary with discrepancies and summary
    """
    detector = DiscrepancyDetector()
    return detector.detect_all_discrepancies(matched_df, raw_claims, raw_payments)
