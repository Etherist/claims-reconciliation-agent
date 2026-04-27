# System Architecture

## Overview

The Claims Reconciliation Agent is built using a modular, agent-based architecture. Each agent is an independent, reusable component that performs a specific function in the reconciliation pipeline.

## High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Input Files   │────▶│  File Ingestor  │────▶│   Data Cleaner  │
│ (CSV/JSON/EDI)  │     │   Agent         │     │     Agent       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Output Reports │◀────│ Report Generator│◀────│ Discrepancy     │
│ (CSV/PDF/JSON)  │     │     Agent       │     │ Detector Agent  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                       ▲
                                                       │
                                              ┌─────────────────┐
                                              │  Fuzzy Matcher  │
                                              │     Agent       │
                                              └─────────────────┘
```

## Component Details

### File Ingestor Agent (`src/agents/file_ingestor.py`)

**Responsibilities:**
- Parse claims and payments files (CSV, JSON, EDI)
- Validate file existence, size, and format
- Check for required columns
- Return raw pandas DataFrame

**Key Methods:**
- `ingest_file(file_path: str, file_type: str) -> pd.DataFrame`
- `validate_file(file_path: str) -> Tuple[bool, str]`
- `ingest_csv()`, `ingest_json()`, `ingest_edi()`

**Error Handling:**
- Raises `ValueError` for invalid files
- Logs all operations with `logging` module

**Dependencies:** Pandas, pathlib

### Data Cleaner Agent (`src/agents/data_cleaner.py`)

**Responsibilities:**
- Standardize patient names (title case, remove punctuation)
- Parse dates into datetime objects
- Convert amount strings to floats (remove $ and commas)
- Ensure consistent data types

**Key Methods:**
- `clean_dataframe(df: pd.DataFrame, file_type: str) -> pd.DataFrame`
- `clean_patient_names()`, `clean_dates()`, `clean_amounts()`

**Data Transformations:**
| Input | Output |
|-------|--------|
| "J. Smith" | "J Smith" |
| "01/04/2026" | `datetime(2026, 4, 1)` |
| "$1,500.00" | `1500.00` |

**Dependencies:** Pandas, datetime, regex

### Fuzzy Matcher Agent (`src/agents/fuzzy_matcher.py`)

**Responsibilities:**
- Match claims to payments using multi-criteria scoring
- Apply fuzzy name matching (Levenshtein distance)
- Check date and amount tolerance
- Generate matched pairs and initial discrepancies

**Scoring Algorithm:**
```
Total Score = (Name Score × 0.5) + (Date Score × 0.3) + (Amount Score × 0.2)

Where:
- Name Score: fuzzywuzzy.token_set_ratio (0-100)
- Date Score: 100 if |date_diff| ≤ tolerance_days else 0
- Amount Score: 100 if within tolerance else 0
```

**Key Methods:**
- `_score_match(claim: pd.Series, payment: pd.Series) -> Tuple[float, Dict]`
- `match_claims_payments() -> Tuple[pd.DataFrame, list]`

**Configurable Thresholds:**
- `name_threshold`: minimum score to accept a match (default: 90)
- `date_tolerance_days`: max day difference (default: 2)
- `amount_tolerance_pct`: percentage tolerance (default: 0.01 ±1%)

**Dependencies:** fuzzywuzzy, python-Levenshtein

### Discrepancy Detector Agent (`src/agents/discrepancy_detector.py`)

**Responsibilities:**
- Categorize discrepancies: underpayment, overpayment, duplicate, unmatched
- Flag high-priority items (high value)
- Generate summary statistics

**Discrepancy Types:**

| Type | Description | Action |
|------|-------------|--------|
| `underpayment` | Payment < Claim amount | Contact insurer |
| `overpayment` | Payment > Claim amount | Refund or credit |
| `duplicate` | Same ID appears multiple times | Investigate fraud |
| `unmatched_claim` | No payment found | Follow up with insurer |
| `unmatched_payment` | No claim found | Identify source |

**Key Methods:**
- `detect_all_discrepancies() -> Dict`
- `categorize_discrepancies()`
- `flag_high_value_discrepancies(threshold=$1000)`
- `_generate_summary()`

**Summary Statistics Generated:**
- Total claims/payments
- Matched count and percentage
- Counts by discrepancy type
- Total discrepancy dollar value
- High-priority item count

**Dependencies:** Pandas

### Report Generator Agent (`src/agents/report_generator.py`)

**Responsibilities:**
- Create reconciliation reports in multiple formats
- Include summary, matched records, discrepancies
- Format data for finance team consumption

**Report Formats:**

1. **CSV** – Multi-section file with markers:
   ```
   # SECTION 1: SUMMARY (JSON)
   # SECTION 2: MATCHED RECORDS (CSV table)
   # SECTION 3: DISCREPANCIES (CSV table)
   ```

2. **JSON** – Structured data for programmatic access:
   ```json
   {
     "generated_at": "2026-04-27T...",
     "summary": { ... },
     "matched_count": 21,
     "discrepancy_count": 4,
     "discrepancies": [ ... ]
   }
   ```

3. **PDF** – Professional finance report with:
   - Summary table
   - Discrepancy listing with priority flags
   - Company header/footer (stretch)

**Key Methods:**
- `generate_report(format='csv') -> Dict[format, filepath]`
- `generate_csv_report()`, `generate_json_report()`, `generate_pdf_report()`

**Dependencies:** Pandas, Jinja2 (templating), ReportLab (PDF), Matplotlib (charts)

---

## Data Flow

### Claims Data Schema

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `claim_id` | str | Unique claim identifier | "101" |
| `patient_name` | str | Full patient name | "John Smith" |
| `date_of_service` | str/date | Service date | "2026-04-01" |
| `amount` | float | Claimed amount | 1500.00 |
| `provider_id` | str | Provider/hospital ID | "PRV123" |
| `insurer` | str | Insurance company | "Medicare" |
| `service_code` | str | Procedure code (optional) | "consult1" |

### Payments Data Schema

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `payment_id` | str | Unique payment identifier | "201" |
| `patient_name` | str | Payer patient name | "John Smith" |
| `date_of_service` | str/date | Service date | "2026-04-01" |
| `amount` | float | Payment amount | 1400.00 |
| `provider_id` | str | Provider ID | "PRV123" |
| `insurer` | str | Insurance company | "Medicare" |
| `payment_method` | str | EFT/cheque/credit | "EFT" |

### Internal Processing Columns

After cleaning, DataFrames include:
- `date_of_service_dt` – datetime object for date comparisons
- Cleaned text columns (title case, normalized whitespace)
- Numeric amounts (floats)

### Matched Record Output

| Field | Description |
|-------|-------------|
| `claim_id` | Source claim ID |
| `payment_id` | Matched payment ID |
| `patient_name` | Cleaned patient name |
| `date_of_service` | Original date string |
| `claim_amount` | Original claimed amount |
| `payment_amount` | Received payment amount |
| `match_score` | Overall similarity score (0-100) |
| `name_score`, `date_score`, `amount_score` | Component scores |
| `difference` | claim_amount - payment_amount |
| `discrepancy_type` | "exact", "underpayment", or "overpayment" |

---

## Configuration Management

All thresholds and paths controlled via `src/utils/config.py` using environment variables:

```python
from utils.config import Config

# Access config values
threshold = Config.FUZZY_NAME_THRESHOLD
tolerance = Config.DATE_TOLERANCE_DAYS
output_dir = Config.REPORT_DIR
```

**Environment Variables (`.env`):**

| Variable | Default | Purpose |
|----------|---------|---------|
| `MAX_FILE_SIZE_MB` | 10 | Max upload size |
| `FUZZY_NAME_THRESHOLD` | 90 | Name match minimum |
| `DATE_TOLERANCE_DAYS` | 2 | Date difference tolerance |
| `AMOUNT_TOLERANCE_PCT` | 0.01 | ±1% amount tolerance |
| `REPORT_DIR` | `reports/` | Output directory |
| `LOG_LEVEL` | INFO | Logging verbosity |

---

## Error Handling & Logging

Each agent logs its operations at appropriate levels:

- **INFO**: Successful operations, counts, file paths
- **WARNING**: Data quality issues (unparseable dates, missing values)
- **ERROR**: Failures (file not found, invalid format)
- **DEBUG**: Detailed matching decisions (per-record scoring)

Log output includes timestamps, agent names, and relevant IDs for traceability.

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Ingested {len(df)} rows")
logger.warning(f"Unmatched claim: claim_id={claim_id}")
logger.error(f"Failed to parse file: {e}")
```

---

## Scalability Considerations

Current implementation is optimized for demo (≤1000 records). For production-scale:

- **Batch Processing**: Process millions of records in chunks
- **Parallel Matching**: Use multiprocessing or Dask for matching
- **Database Storage**: PostgreSQL with PostGIS for geographic claims
- **Caching**: Redis cache for previously matched records
- **Streaming**: Apache Kafka for real-time claim ingestion

---

## Testing Strategy

| Test Type | Scope | Tools | Location |
|-----------|-------|-------|----------|
| Unit Tests | Individual agent functions | pytest | `tests/test_agents.py` |
| Integration | Full pipeline (ingest → report) | pytest | `tests/test_agents.py::TestIntegration` |
| CLI Tests | Command-line interface | pytest + subprocess | `tests/test_app.py` |
| E2E Tests | Streamlit UI | Selenium/Playwright | `tests/test_e2e.py` (stretch) |

**Test Coverage Goal:** ≥80%

---

## Deployment Options

### Local
```bash
python src/app/cli.py --claims data.csv --payments data.csv
```

### Streamlit Cloud
1. Push to GitHub
2. Connect repo at [share.streamlit.io](https://share.streamlit.io)
3. Set `requirements.txt` auto-detected
4. Main file path: `src/app/streamlit_app.py`

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "src/app/streamlit_app.py", "--server.port=8501"]
```

---

## Security Considerations

### Input Validation
- **File Ingestor** validates file size, extension, and required columns
- **Path Traversal Protection**: File paths are resolved and checked to be within project directory or system temp
- **Type Safety**: All agent inputs are type-hinted and validated

### Output Sanitization
- **CSV Injection Prevention**: `ReportGenerator` sanitizes all string fields (prefixes `=`, `+`, `-`, `@` with `'`) and uses `csv.QUOTE_ALL`
- **Path Safety**: Report directory validated to prevent directory traversal

### Data Privacy
- Logging can be configured to redact PII via `LOG_SANITIZE_PII=true`
- Sample data uses synthetic names only
- No real patient data included in repository

### Dependency Security
- Automated scanning via GitHub Actions (`safety check`)
- Regular updates recommended (use `pip list --outdated`)

### Configuration Security
- Secrets stored in `.env` (gitignored)
- API keys not committed
- Environment variables validated

See [SECURITY.md](./SECURITY.md) for full security policy.

---

## Next Steps

- Review `docs/agent_workflow.md` for agent interaction flows
- See `docs/data_format.md` for file format specifications
- Read `docs/demo_guide.md` for demo walkthrough instructions
