"""
Streamlit Dashboard for Claims Reconciliation Agent.
Interactive UI for file upload, matching, and reporting.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.file_ingestor import FileIngestor, ingest_file
from agents.data_cleaner import clean_data
from agents.fuzzy_matcher import match_claims_payments, FuzzyMatcher
from agents.discrepancy_detector import detect_discrepancies
from agents.report_generator import ReportGenerator
from utils.config import Config
from utils.logging_utils import configure_logging

# Configure logging (with optional PII sanitization)
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
configure_logging()

# Get logger for this module
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Claims Reconciliation Agent",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success { color: #2e7d32; }
    .warning { color: #f57c00; }
    .error { color: #c62828; }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("🏥 Claims Reconciliation Agent")
    st.markdown("**AI-Powered Healthcare Claims Matching for Australian Providers**")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Upload section
        st.subheader("📁 Upload Files")
        claims_file = st.file_uploader(
            "Claims File (CSV/JSON)",
            type=["csv", "json"],
            help="Upload claims data with columns: claim_id, patient_name, date_of_service, amount, provider_id, insurer"
        )
        payments_file = st.file_uploader(
            "Payments File (CSV/JSON)",
            type=["csv", "json"],
            help="Upload payments data with columns: payment_id, patient_name, date_of_service, amount, provider_id, insurer"
        )

        st.divider()

        # Matching thresholds
        st.subheader("🎯 Matching Thresholds")
        name_threshold = st.slider(
            "Name Similarity Threshold",
            min_value=50,
            max_value=100,
            value=Config.FUZZY_NAME_THRESHOLD,
            help="Minimum similarity percentage for patient name matching"
        )
        date_tolerance = st.slider(
            "Date Tolerance (days)",
            min_value=0,
            max_value=7,
            value=Config.DATE_TOLERANCE_DAYS,
            help="Maximum days difference allowed for date matching"
        )
        amount_tolerance_pct = st.slider(
            "Amount Tolerance (%)",
            min_value=0.0,
            max_value=10.0,
            value=Config.AMOUNT_TOLERANCE_PCT * 100,
            help="Percentage tolerance for amount matching"
        ) / 100

        # Sample data option
        use_sample = st.checkbox(
            "Use Sample Data",
            value=False,
            help="Load pre-generated sample claims and payments"
        )

        # Process button
        process_button = st.button("🔍 Reconcile", type="primary", use_container_width=True)

    # Main content
    if process_button:
        with st.spinner("Processing reconciliation..."):

            try:
                # Load data
                if use_sample:
                    st.info("Loading sample data...")
                    claims_path = os.path.join("src", "data", "sample_claims.csv")
                    payments_path = os.path.join("src", "data", "sample_payments.csv")

                    claims_raw = pd.read_csv(claims_path, dtype=str)
                    payments_raw = pd.read_csv(payments_path, dtype=str)
                    st.success(f"✅ Loaded {len(claims_raw)} claims and {len(payments_raw)} payments")
                else:
                    if not claims_file or not payments_file:
                        st.error("❌ Please upload both claims and payments files, or check 'Use Sample Data'")
                        st.stop()

                    # Save uploaded files to temp
                    claims_raw = pd.read_csv(claims_file, dtype=str)
                    payments_raw = pd.read_csv(payments_file, dtype=str)
                    st.success(f"✅ Loaded {len(claims_raw)} claims and {len(payments_raw)} payments")

                # Step 1: Clean data
                st.subheader("🧹 Step 1: Data Cleaning")
                claims_clean = clean_data(claims_raw, "claims")
                payments_clean = clean_data(payments_raw, "payments")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Claims after cleaning", len(claims_clean))
                with col2:
                    st.metric("Payments after cleaning", len(payments_clean))

                # Step 2: Match
                st.subheader("🔗 Step 2: Fuzzy Matching")
                matcher = FuzzyMatcher(
                    name_threshold=name_threshold,
                    date_tolerance_days=date_tolerance,
                    amount_tolerance_pct=amount_tolerance_pct
                )
                matched_df, discrepancies_list = matcher.match_claims_payments(
                    claims_clean, payments_clean
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Matched", len(matched_df))
                with col2:
                    match_rate = len(matched_df) / len(claims_clean) * 100 if len(claims_clean) > 0 else 0
                    st.metric("Match Rate", f"{match_rate:.1f}%")
                with col3:
                    st.metric("Discrepancies", len(discrepancies_list))

                # Step 3: Detect discrepancies
                st.subheader("🚨 Step 3: Discrepancy Analysis")
                detection_result = detect_discrepancies(
                    matched_df, claims_raw, payments_raw
                )
                summary = detection_result["summary"]
                all_discrepancies = detection_result["discrepancies"]

                # Display summary
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Claims", summary["total_claims"])
                with col2:
                    st.metric("Matched", summary["matched_count"])
                with col3:
                    st.metric("Underpayments", summary["underpayments_count"])
                with col4:
                    st.metric("High Priority", summary["high_priority_count"])

                # Visualizations
                st.subheader("📊 Reconciliation Dashboard")

                col1, col2 = st.columns(2)

                with col1:
                    # Match status pie chart
                    labels = ['Matched', 'Unmatched Claims', 'Unmatched Payments']
                    values = [
                        summary['matched_count'],
                        summary['unmatched_claims'],
                        summary['unmatched_payments']
                    ]
                    fig_match = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
                    fig_match.update_layout(title_text="Match Status")
                    st.plotly_chart(fig_match, use_container_width=True)

                with col2:
                    # Discrepancy types bar chart
                    disc_types = {
                        'Underpayments': summary['underpayments_count'],
                        'Overpayments': summary['overpayments_count'],
                        'Duplicates': summary['duplicates_count'],
                        'Unmatched': summary['unmatched_claims'] + summary['unmatched_payments']
                    }
                    fig_types = go.Figure(data=[
                        go.Bar(
                            x=list(disc_types.keys()),
                            y=list(disc_types.values()),
                            marker_color=['#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6']
                        )
                    ])
                    fig_types.update_layout(
                        title_text="Discrepancy Types",
                        xaxis_title="Type",
                        yaxis_title="Count"
                    )
                    st.plotly_chart(fig_types, use_container_width=True)

                # Detailed discrepancies table
                st.subheader("📋 Detailed Discrepancies")
                if all_discrepancies:
                    disc_df = pd.DataFrame(all_discrepancies)
                    # Format amounts
                    if 'difference' in disc_df.columns:
                        disc_df['difference'] = disc_df['difference'].apply(lambda x: f"${x:,.2f}")
                    if 'amount' in disc_df.columns:
                        disc_df['amount'] = disc_df['amount'].apply(lambda x: f"${x:,.2f}")

                    st.dataframe(
                        disc_df,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.success("✅ No discrepancies found!")

                # Matched records
                with st.expander("📄 View All Matched Records"):
                    if not matched_df.empty:
                        display_df = matched_df.copy()
                        for col in ['claim_amount', 'payment_amount', 'difference']:
                            if col in display_df.columns:
                                display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(display_df, use_container_width=True)
                    else:
                        st.warning("No matched records")

                # Generate reports
                st.subheader("📥 Generate Reports")
                col1, col2, col3 = st.columns(3)

                report_gen = ReportGenerator()

                if col1.button("Download CSV Report"):
                    outputs = report_gen.generate_report(matched_df, all_discrepancies, summary, "csv")
                    if "csv" in outputs:
                        with open(outputs["csv"], "r") as f:
                            st.download_button(
                                label="⬇️ Download CSV",
                                data=f.read(),
                                file_name=os.path.basename(outputs["csv"]),
                                mime="text/csv"
                            )

                if col2.button("Download JSON Report"):
                    outputs = report_gen.generate_report(matched_df, all_discrepancies, summary, "json")
                    if "json" in outputs:
                        with open(outputs["json"], "r") as f:
                            st.download_button(
                                label="⬇️ Download JSON",
                                data=f.read(),
                                file_name=os.path.basename(outputs["json"]),
                                mime="application/json"
                            )

                if col3.button("Generate PDF Report"):
                    outputs = report_gen.generate_report(matched_df, all_discrepancies, summary, "pdf")
                    if "pdf" in outputs and outputs["pdf"]:
                        with open(outputs["pdf"], "rb") as f:
                            st.download_button(
                                label="⬇️ Download PDF",
                                data=f.read(),
                                file_name=os.path.basename(outputs["pdf"]),
                                mime="application/pdf"
                            )
                    else:
                        st.warning("PDF generation requires reportlab. Install: pip install reportlab")

            except Exception as e:
                st.error(f"❌ Error during reconciliation: {str(e)}")
                logger.error(f"Reconciliation error: {e}", exc_info=True)

    # Footer
    st.divider()
    st.markdown("""
    **🏥 Claims Reconciliation Agent** | Built for Australian Healthcare

    🔒 **Privacy**: All processing happens locally. No data is transmitted to external servers.

    💡 **Need Help?** Check the [documentation](docs/).
    """)

if __name__ == "__main__":
    main()
