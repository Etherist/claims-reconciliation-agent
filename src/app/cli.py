"""Command-Line Interface for Claims Reconciliation Agent."""
import argparse
import sys
import os
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.file_ingestor import ingest_file
from agents.data_cleaner import clean_data
from agents.fuzzy_matcher import match_claims_payments
from agents.discrepancy_detector import detect_discrepancies
from agents.report_generator import ReportGenerator
from utils.config import Config
from utils.logging_utils import configure_logging

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Claims Reconciliation Agent - Match healthcare claims to payments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --claims claims.csv --payments payments.csv
  %(prog)s --claims claims.json --payments payments.json --output report.csv
  %(prog)s --claims data/claims.csv --payments data/payments.csv --format json
        """
    )
    parser.add_argument(
        "--claims",
        required=True,
        help="Path to claims file (CSV/JSON/EDI)"
    )
    parser.add_argument(
        "--payments",
        required=True,
        help="Path to payments file (CSV/JSON/EDI)"
    )
    parser.add_argument(
        "--output-dir",
        default=Config.REPORT_DIR,
        help=f"Output directory for reports (default: {Config.REPORT_DIR})"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json", "pdf", "all"],
        default="csv",
        help="Report format (default: csv)"
    )
    parser.add_argument(
        "--name-threshold",
        type=int,
        default=Config.FUZZY_NAME_THRESHOLD,
        help=f"Name similarity threshold 0-100 (default: {Config.FUZZY_NAME_THRESHOLD})"
    )
    parser.add_argument(
        "--date-tolerance",
        type=int,
        default=Config.DATE_TOLERANCE_DAYS,
        help=f"Date tolerance in days (default: {Config.DATE_TOLERANCE_DAYS})"
    )
    parser.add_argument(
        "--amount-tolerance",
        type=float,
        default=Config.AMOUNT_TOLERANCE_PCT,
        help=f"Amount tolerance as decimal (default: {Config.AMOUNT_TOLERANCE_PCT})"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()

def print_banner():
    """Print tool banner."""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║       🏥 CLAIMS RECONCILIATION AGENT v1.0                 ║
║       Australian Healthcare Revenue Cycle Management      ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_summary(summary: dict):
    """Print formatted summary to console."""
    print("\n" + "=" * 60)
    print("RECONCILIATION SUMMARY")
    print("=" * 60)
    print(f" Total Claims:          {summary['total_claims']}")
    print(f" Total Payments:        {summary['total_payments']}")
    print(f" Matched:               {summary['matched_count']} ({summary['match_rate_pct']:.1f}%)")
    print(f" Unmatched Claims:      {summary['unmatched_claims']}")
    print(f" Unmatched Payments:    {summary['unmatched_payments']}")
    print("-" * 60)
    print(f" Underpayments:         {summary['underpayments_count']}")
    print(f" Overpayments:          {summary['overpayments_count']}")
    print(f" Duplicates:            {summary['duplicates_count']}")
    print(f" Total Discrepancy Val: ${summary['total_discrepancy_value']:,.2f}")
    print(f" High Priority Items:   {summary['high_priority_count']}")
    print("=" * 60)

def print_discrepancies(discrepancies: list, limit: int = 20):
    """Print formatted discrepancy list."""
    if not discrepancies:
        print("\n✅ No discrepancies detected!")
        return

    print(f"\n⚠️  TOP {min(limit, len(discrepancies))} DISCREPANCIES:")
    print("-" * 80)
    print(f"{'Type':<12} {'Patient':<20} {'Amount':<15} {'Reason':<40}")
    print("-" * 80)

    for i, disc in enumerate(discrepancies[:limit]):
        disc_type = disc.get("type", "").title()
        patient = disc.get("patient_name", "")[:19]
        amount = disc.get("difference", disc.get("amount", 0))
        amount_str = f"${amount:,.2f}"
        reason = disc.get("reason", "")[:39]
        priority = "🔴" if disc.get("priority") == "high" else "  "

        print(f"{priority} {disc_type:<10} {patient:<20} {amount_str:<15} {reason:<40}")

    if len(discrepancies) > limit:
        print(f"... and {len(discrepancies) - limit} more (see report for full list)")

def main():
    # Configure logging (with optional PII sanitization)
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    configure_logging()

    print_banner()
    args = parse_args()

    # Validate files exist
    if not os.path.exists(args.claims):
        print(f"❌ Error: Claims file not found: {args.claims}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.payments):
        print(f"❌ Error: Payments file not found: {args.payments}", file=sys.stderr)
        sys.exit(1)

    try:
        # 1. Ingest files
        print("\n📂 Ingesting files...")
        claims_raw = ingest_file(args.claims, "claims")
        payments_raw = ingest_file(args.payments, "payments")
        print(f"   Loaded {len(claims_raw)} claims, {len(payments_raw)} payments")

        # 2. Clean data
        print("\n🧹 Cleaning and standardizing data...")
        claims_clean = clean_data(claims_raw, "claims")
        payments_clean = clean_data(payments_raw, "payments")

        # 3. Match claims to payments
        print("\n🔗 Matching claims to payments...")
        from agents.fuzzy_matcher import FuzzyMatcher
        matcher = FuzzyMatcher(
            name_threshold=args.name_threshold,
            date_tolerance_days=args.date_tolerance,
            amount_tolerance_pct=args.amount_tolerance
        )
        matched_df, _ = matcher.match_claims_payments(claims_clean, payments_clean)
        print(f"   Matched {len(matched_df)} claim-payment pairs")

        # 4. Detect discrepancies
        print("\n🔍 Detecting discrepancies...")
        detection_result = detect_discrepancies(matched_df, claims_raw, payments_raw)
        summary = detection_result["summary"]
        discrepancies = detection_result["discrepancies"]

        # 5. Generate reports
        print("\n📊 Generating reports...")
        os.makedirs(args.output_dir, exist_ok=True)
        report_gen = ReportGenerator(report_dir=args.output_dir)
        outputs = report_gen.generate_report(
            matched_df, discrepancies, summary, args.format
        )

        # 6. Output results
        print_summary(summary)
        print_discrepancies(discrepancies)

        print("\n📄 Reports generated:")
        for fmt, path in outputs.items():
            print(f"   {fmt.upper()}: {path}")

        print(f"\n✅ Reconciliation complete! ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
