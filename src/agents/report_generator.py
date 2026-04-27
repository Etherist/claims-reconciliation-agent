"""Report Generator Agent - Creates reconciliation reports in various formats."""
import pandas as pd
import logging
import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from jinja2 import Template
import json
from pathlib import Path
from utils.config import Config

logger = logging.getLogger(__name__)

def sanitize_csv_value(value):
    """
    Sanitize value for CSV output to prevent formula injection.
    Prefixes with single quote if starts with =, +, -, @, |, or tab.
    """
    if isinstance(value, str) and value:
        # Check for potentially dangerous leading characters
        if value[0] in ('=', '+', '-', '@', '|', '\t'):
            return "'" + value
    return value

class ReportGenerator:
    """Agent responsible for generating reconciliation reports."""

    def __init__(self, report_dir: str = Config.REPORT_DIR):
        """
        Initialize Report Generator.

        Args:
            report_dir: Directory for report output
        """
        self.report_dir = self._validate_report_dir(report_dir)
        os.makedirs(self.report_dir, exist_ok=True)
        logger.info(f"Report Generator initialized, output dir: {self.report_dir}")

    def _validate_report_dir(self, report_dir: str) -> str:
        """
        Validate report directory to prevent path traversal.

        Returns:
            Absolute path string
        Raises:
            ValueError if path escapes project directory
        """
        base_dir = Path.cwd().resolve()
        abs_path = Path(report_dir).resolve()

        # Ensure the report directory is within the project
        if not str(abs_path).startswith(str(base_dir)):
            raise ValueError(
                f"Report directory '{report_dir}' resolves outside project directory"
            )

        return str(abs_path)

    def _generate_filename(self, prefix: str, extension: str) -> str:
        """Generate timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.report_dir, f"{prefix}_{timestamp}.{extension}")

    def _sanitize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sanitize DataFrame for CSV output to prevent formula injection.

        Applies sanitize_csv_value to all string/object columns.
        """
        if df.empty:
            return df

        df_safe = df.copy()
        for col in df_safe.select_dtypes(include=['object']).columns:
            df_safe[col] = df_safe[col].apply(
                lambda x: sanitize_csv_value(x) if pd.notna(x) else x
            )
        return df_safe

    def generate_csv_report(
        self,
        matched_df: pd.DataFrame,
        discrepancies: List[Dict],
        summary: Dict
    ) -> str:
        """
        Generate CSV report with matched records and discrepancies.

        Args:
            matched_df: DataFrame of matched pairs
            discrepancies: List of discrepancy records
            summary: Summary statistics dict

        Returns:
            Path to generated CSV file
        """
        filepath = self._generate_filename("reconciliation_report", "csv")

        # Sanitize DataFrames to prevent CSV injection
        summary_df = pd.DataFrame([summary])
        matched_export = self._sanitize_dataframe(matched_df.copy()) if not matched_df.empty else pd.DataFrame()
        discrepancies_df = self._sanitize_dataframe(pd.DataFrame(discrepancies)) if discrepancies else pd.DataFrame()

        # Write multi-section CSV with sanitization and full quoting
        with open(filepath, 'w', newline='') as f:
            f.write("# CLAIMS RECONCILIATION REPORT\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write("#" + "=" * 80 + "\n\n")

            f.write("# SECTION 1: SUMMARY\n")
            f.write(json.dumps(summary, indent=2))
            f.write("\n\n")

            f.write("# SECTION 2: MATCHED RECORDS\n")
            if not matched_export.empty:
                matched_export.to_csv(
                    f, index=False, quoting=csv.QUOTE_ALL
                )
            else:
                f.write("No matched records\n")
            f.write("\n\n")

            f.write("# SECTION 3: DISCREPANCIES\n")
            if not discrepancies_df.empty:
                discrepancies_df.to_csv(
                    f, index=False, quoting=csv.QUOTE_ALL
                )
            else:
                f.write("No discrepancies found\n")

        logger.info(f"CSV report generated: {filepath}")
        return filepath

    def generate_pdf_report(
        self,
        matched_df: pd.DataFrame,
        discrepancies: List[Dict],
        summary: Dict
    ) -> str:
        """
        Generate PDF report (stretch - basic implementation).

        Args:
            matched_df: DataFrame of matched pairs
            discrepancies: List of discrepancy records
            summary: Summary statistics dict

        Returns:
            Path to generated PDF file
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors

            filepath = self._generate_filename("reconciliation_report", "pdf")
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Title
            story.append(Paragraph("Claims Reconciliation Report", styles['Title']))
            story.append(Spacer(1, 12))

            # Summary Table
            story.append(Paragraph("Summary Statistics", styles['Heading2']))
            summary_data = [["Metric", "Value"]] + [
                ["Total Claims", summary.get("total_claims", 0)],
                ["Total Payments", summary.get("total_payments", 0)],
                ["Matched", summary.get("matched_count", 0)],
                ["Match Rate", f"{summary.get('match_rate_pct', 0)}%"],
                ["Underpayments", summary.get("underpayments_count", 0)],
                ["Overpayments", summary.get("overpayments_count", 0)],
                ["Duplicates", summary.get("duplicates_count", 0)],
                ["Unmatched Claims", summary.get("unmatched_claims", 0)],
                ["Unmatched Payments", summary.get("unmatched_payments", 0)],
                ["Total Discrepancy Value", f"${summary.get('total_discrepancy_value', 0):,.2f}"],
                ["High Priority Items", summary.get("high_priority_count", 0)]
            ]
            table = Table(summary_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
            story.append(Spacer(1, 12))

            # Discrepancies Section
            story.append(Paragraph("Discrepancies", styles['Heading2']))
            if discrepancies:
                disc_data = [["Type", "Patient", "Amount", "Reason", "Priority"]]
                for d in discrepancies[:50]:  # Limit to first 50 for PDF
                    disc_data.append([
                        d.get("type", ""),
                        d.get("patient_name", ""),
                        f"${d.get('difference', d.get('amount', 0)):,.2f}",
                        d.get("reason", "")[:40] + "...",
                        d.get("priority", "normal").title()
                    ])
                disc_table = Table(disc_data, colWidths=[80, 100, 80, 150, 60])
                disc_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(disc_table)
            else:
                story.append(Paragraph("No discrepancies found.", styles['Normal']))

            doc.build(story)
            logger.info(f"PDF report generated: {filepath}")
            return filepath

        except ImportError:
            logger.warning("reportlab not installed, skipping PDF generation")
            return ""

    def generate_json_report(
        self,
        matched_df: pd.DataFrame,
        discrepancies: List[Dict],
        summary: Dict
    ) -> str:
        """
        Generate JSON report for programmatic consumption.

        Args:
            matched_df: Matched records
            discrepancies: Discrepancy list
            summary: Summary statistics

        Returns:
            Path to JSON file
        """
        filepath = self._generate_filename("reconciliation_report", "json")

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "matched_count": len(matched_df),
            "discrepancy_count": len(discrepancies),
            "discrepancies": discrepancies
        }

        if not matched_df.empty:
            report["matched_records"] = matched_df.to_dict(orient="records")

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"JSON report generated: {filepath}")
        return filepath

    def generate_report(
        self,
        matched_df: pd.DataFrame,
        discrepancies: List[Dict],
        summary: Dict,
        format: str = Config.DEFAULT_REPORT_FORMAT
    ) -> Dict[str, str]:
        """
        Generate reports in specified format(s).

        Args:
            matched_df: Matched records DataFrame
            discrepancies: List of discrepancy dicts
            summary: Summary statistics
            format: Report format ('csv', 'pdf', 'json', or 'all')

        Returns:
            Dictionary mapping format -> filepath
        """
        outputs = {}

        if format in ["csv", "all"]:
            outputs["csv"] = self.generate_csv_report(matched_df, discrepancies, summary)

        if format in ["pdf", "all"]:
            pdf_path = self.generate_pdf_report(matched_df, discrepancies, summary)
            if pdf_path:
                outputs["pdf"] = pdf_path

        if format in ["json", "all"]:
            outputs["json"] = self.generate_json_report(matched_df, discrepancies, summary)

        logger.info(f"Reports generated: {list(outputs.keys())}")
        return outputs


def generate_report(
    matched_df: pd.DataFrame,
    discrepancies: List[Dict],
    summary: Dict,
    format: str = "csv"
) -> Dict[str, str]:
    """
    Convenience function for report generation.

    Args:
        matched_df: Matched DataFrame
        discrepancies: Discrepancy list
        summary: Summary dict
        format: Output format

    Returns:
        Dict of format -> filepath
    """
    generator = ReportGenerator()
    return generator.generate_report(matched_df, discrepancies, summary, format)
