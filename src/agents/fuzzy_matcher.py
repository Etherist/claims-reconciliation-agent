"""Fuzzy Matcher Agent - Matches claims to payments using fuzzy logic."""
import pandas as pd
import logging
from typing import Tuple, List, Dict, Optional
from fuzzywuzzy import fuzz
from datetime import datetime
from utils.helpers import (
    dates_within_tolerance,
    calculate_amount_difference,
    clean_name
)
from utils.config import Config

logger = logging.getLogger(__name__)

class FuzzyMatcher:
    """Agent responsible for matching claims to payments using fuzzy logic."""

    def __init__(
        self,
        name_threshold: int = Config.FUZZY_NAME_THRESHOLD,
        date_tolerance_days: int = Config.DATE_TOLERANCE_DAYS,
        amount_tolerance_pct: float = Config.AMOUNT_TOLERANCE_PCT,
        amount_tolerance_abs: float = Config.AMOUNT_TOLERANCE_ABS
    ) -> None:
        """
        Initialize Fuzzy Matcher with thresholds.

        Args:
            name_threshold: Minimum name similarity score (0-100)
            date_tolerance_days: Maximum days difference for matching
            amount_tolerance_pct: Percentage tolerance for amounts
            amount_tolerance_abs: Absolute dollar tolerance
        """
        self.name_threshold = name_threshold
        self.date_tolerance_days = date_tolerance_days
        self.amount_tolerance_pct = amount_tolerance_pct
        self.amount_tolerance_abs = amount_tolerance_abs

    def _score_match(
        self,
        claim: pd.Series,
        payment: pd.Series
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate match score between a claim and payment.

        Args:
            claim: Claim record (Series)
            payment: Payment record (Series)

        Returns:
            Tuple of (total_score, component_scores_dict)
        """
        scores = {}

        # Name similarity (50% weight)
        claim_name = clean_name(claim["patient_name"])
        payment_name = clean_name(payment["patient_name"])
        name_score = fuzz.token_set_ratio(claim_name, payment_name)
        scores["name"] = name_score

        # Date tolerance (30% weight)
        claim_date = claim.get("date_of_service_dt")
        payment_date = payment.get("date_of_service_dt")
        if claim_date and payment_date:
            date_match = dates_within_tolerance(
                claim_date, payment_date, self.date_tolerance_days
            )
            date_score = 100 if date_match else 0
        else:
            date_score = 50  # Neutral if dates missing
        scores["date"] = date_score

        # Amount tolerance (20% weight)
        claim_amount = claim.get("amount", 0)
        payment_amount = payment.get("amount", 0)
        amount_match = calculate_amount_difference(
            claim_amount, payment_amount,
            self.amount_tolerance_pct, self.amount_tolerance_abs
        )
        amount_score = 100 if amount_match else 0
        scores["amount"] = amount_score

        # Weighted total score
        total_score = (
            name_score * 0.5 +
            date_score * 0.3 +
            amount_score * 0.2
        )

        return total_score, scores

    def match_claims_payments(
        self,
        claims: pd.DataFrame,
        payments: pd.DataFrame,
        allow_one_to_many: bool = False
    ) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Match claims to payments using greedy best-match algorithm.

        Args:
            claims: Cleaned claims DataFrame
            payments: Cleaned payments DataFrame
            allow_one_to_many: If False, each payment can only match one claim

        Returns:
            Tuple of (matched DataFrame, discrepancies list)
        """
        logger.info(f"Starting matching: {len(claims)} claims, {len(payments)} payments")

        matched_records = []
        discrepancies = []

        # Track which payments have been used
        used_payment_indices = set()

        # Sort claims by amount descending to match larger claims first (better accuracy)
        claims_sorted = claims.sort_values("amount", ascending=False).reset_index(drop=True)

        for claim_idx, claim in claims_sorted.iterrows():
            best_match = None
            best_score = 0
            best_payment_idx = None

            # Find best unmatched payment
            for payment_idx, payment in payments.iterrows():
                if payment_idx in used_payment_indices and not allow_one_to_many:
                    continue

                score, component_scores = self._score_match(claim, payment)

                if score > best_score:
                    best_score = score
                    best_match = payment
                    best_payment_idx = payment_idx
                    match_components = component_scores

            # Determine if match is acceptable
            # Accept if name similarity meets threshold AND dates are within tolerance
            # Amount difference is allowed (under/overpayment) and recorded as discrepancy
            name_score = match_components.get("name", 0) if best_match is not None else 0
            date_score = match_components.get("date", 0) if best_match is not None else 0

            if best_match is not None and name_score >= self.name_threshold and date_score == 100:
                # Create matched record
                matched_record = {
                    "claim_id": claim.get("claim_id", ""),
                    "payment_id": best_match.get("payment_id", ""),
                    "patient_name": claim["patient_name"],
                    "date_of_service": claim.get("date_of_service", ""),
                    "claim_amount": claim.get("amount", 0),
                    "payment_amount": best_match.get("amount", 0),
                    "provider_id": claim.get("provider_id", ""),
                    "insurer": claim.get("insurer", ""),
                    "match_score": round(best_score, 2),
                    "name_score": match_components.get("name", 0),
                    "date_score": match_components.get("date", 0),
                    "amount_score": match_components.get("amount", 0)
                }

                # Calculate discrepancy
                diff = claim.get("amount", 0) - best_match.get("amount", 0)
                matched_record["difference"] = round(diff, 2)

                if abs(diff) > 0.01:  # Non-zero difference
                    if diff > 0:
                        matched_record["discrepancy_type"] = "underpayment"
                    else:
                        matched_record["discrepancy_type"] = "overpayment"
                else:
                    matched_record["discrepancy_type"] = "exact"

                matched_records.append(matched_record)
                used_payment_indices.add(best_payment_idx)

                logger.debug(
                    f"Matched claim {claim.get('claim_id')} to payment {best_match.get('payment_id')} "
                    f"(score={best_score:.1f})"
                )
            else:
                # No acceptable match found - flag as discrepancy
                discrepancy = {
                    "type": "unmatched_claim",
                    "claim_id": claim.get("claim_id", ""),
                    "patient_name": claim["patient_name"],
                    "date_of_service": claim.get("date_of_service", ""),
                    "amount": claim.get("amount", 0),
                    "provider_id": claim.get("provider_id", ""),
                    "insurer": claim.get("insurer", ""),
                    "reason": "No suitable payment match found",
                    "best_score": round(best_score, 2) if best_match is not None else 0
                }
                discrepancies.append(discrepancy)
                logger.warning(f"Unmatched claim: {claim.get('claim_id')} (score={best_score:.1f})")

        # Check for unmatched payments
        for payment_idx, payment in payments.iterrows():
            if payment_idx not in used_payment_indices:
                discrepancy = {
                    "type": "unmatched_payment",
                    "payment_id": payment.get("payment_id", ""),
                    "patient_name": payment["patient_name"],
                    "date_of_service": payment.get("date_of_service", ""),
                    "amount": payment.get("amount", 0),
                    "provider_id": payment.get("provider_id", ""),
                    "insurer": payment.get("insurer", ""),
                    "reason": "No claim matched to this payment"
                }
                discrepancies.append(discrepancy)
                logger.warning(f"Unmatched payment: {payment.get('payment_id')}")

        matched_df = pd.DataFrame(matched_records)
        logger.info(f"Matching complete: {len(matched_records)} matched, {len(discrepancies)} discrepancies")
        return matched_df, discrepancies


def match_claims_payments(
    claims: pd.DataFrame,
    payments: pd.DataFrame
) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Convenience function for matching claims to payments.

    Args:
        claims: Cleaned claims DataFrame
        payments: Cleaned payments DataFrame

    Returns:
        Tuple of (matched DataFrame, discrepancies list)
    """
    matcher = FuzzyMatcher()
    return matcher.match_claims_payments(claims, payments)
