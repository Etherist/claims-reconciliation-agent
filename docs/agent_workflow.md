# Agent Workflow Specification

## Overview

The Claims Reconciliation Agent employs a collaborative multi-agent architecture where five specialized agents work in sequence:

```
File Ingestor → Data Cleaner → Fuzzy Matcher → Discrepancy Detector → Report Generator
```

Each agent is stateless, accepts well-defined inputs, and produces deterministic outputs suitable for unit testing and independent execution.

---

## Agent Specifications

### Agent 1: File Ingestor

**File:** `src/agents/file_ingestor.py`  
**Responsibility:** Parse and validate input files

**Input Schema:**
```python
{
    "file_path": str,      # Path to input file
    "file_type": str       # "claims" or "payments"
}
```

**Output Schema:**
```python
pd.DataFrame({
    "claim_id" | "payment_id": str,
    "patient_name": str,
    "date_of_service": str,
    "amount": str,
    "provider_id": str,
    "insurer": str,
    ...  # optional columns preserved
})
```

**State:** None (stateless)

**Error Conditions:**
| Condition | Error |
|-----------|-------|
| File not found | `ValueError("File not found: {path}")` |
| File too large | `ValueError("File too large (max {MAX_FILE_SIZE_MB}MB)")` |
| Invalid extension | `ValueError("Unsupported file format: {ext}")` |
| Missing columns | `ValueError("Missing required columns: {missing}")` |
| Parse failure | `ValueError("Failed to parse {ext}: {error}")` |

**Tools Used:**
- `pandas.read_csv()` for CSV
- `pandas.read_json()` for JSON
- `edi-parser` library for EDI (stretch)

---

### Agent 2: Data Cleaner

**File:** `src/agents/data_cleaner.py`  
**Responsibility:** Normalize data for matching

**Input Schema:**
```python
pd.DataFrame  # Raw output from FileIngestor
str            # file_type: "claims" or "payments"
```

**Output Schema:**
```python
pd.DataFrame({
    "claim_id" | "payment_id": str,
    "patient_name": str,          # Cleaned: title case, no periods
    "date_of_service": str,        # Original string
    "date_of_service_dt": datetime # Parsed datetime (or NaT)
    "amount": float,              # Numeric value
    "provider_id": str,
    "insurer": str,               # Title case
    ...  # optional columns preserved
})
```

**Transformation Rules:**

| Column | Transformation | Example |
|--------|---------------|---------|
| `patient_name` | `clean_name()`: strip, title case, remove "." | `"J. Smith"` → `"J Smith"` |
| `amount` | `clean_amount()`: strip "$", ",", convert to float | `"$1,500.00"` → `1500.00` |
| `date_of_service` | `standardize_date()`: parse to datetime | `"01/04/2026"` → `2026-04-01` |
| `insurer` | `.str.title()` | `"medicare"` → `"Medicare"` |

**Error Handling:**
- Unparseable dates → `NaT`, warning logged
- Unparseable amounts → `0.0`, warning logged
- Missing values → preserved as empty strings or NaNs

**Tools Used:**
- `re` for regex (amount cleaning)
- `datetime.strptime()` for date parsing
- `fuzzywuzzy` indirectly via helper (not used here)

---

### Agent 3: Fuzzy Matcher

**File:** `src/agents/fuzzy_matcher.py`  
**Responsibility:** Find best match for each claim among payments

**Input Schema:**
```python
{
    "claims": pd.DataFrame  # Cleaned claims (with date_of_service_dt, amount)
    "payments": pd.DataFrame  # Cleaned payments (same schema)
}
```

**Output Schema:**
```python
(
    matched_df: pd.DataFrame({
        "claim_id": str,
        "payment_id": str,
        "patient_name": str,
        "date_of_service": str,
        "claim_amount": float,
        "payment_amount": float,
        "match_score": float,      # 0–100 overall
        "name_score": float,        # 0–100 component
        "date_score": float,        # 0 or 100
        "amount_score": float,      # 0 or 100
        "difference": float,        # claim_amount - payment_amount
        "discrepancy_type": str     # "exact", "underpayment", "overpayment"
    }),
    initial_discrepancies: list[dict]  # Unmatched claims/payments
)
```

**Matching Algorithm:**

```python
for each claim in descending amount order:
    best_match = None
    best_score = 0

    for each available payment:
        name_score = fuzz.token_set_ratio(claim.name, payment.name)
        date_score = 100 if |claim.date - payment.date| ≤ tolerance_days else 0
        amount_score = 100 if amounts within tolerance else 0

        total_score = (name_score * 0.5) + (date_score * 0.3) + (amount_score * 0.2)

        if total_score > best_score:
            best_score = total_score
            best_match = payment

    if best_score ≥ name_threshold:
        record match
    else:
        flag as unmatched_claim
```

**Configuration Parameters:**
```python
FuzzyMatcher(
    name_threshold=90,          # Min score for valid match
    date_tolerance_days=2,      # Max day diff for date_score=100
    amount_tolerance_pct=0.01,  # ±1% for amount_score=100
    amount_tolerance_abs=10.0   # ±$10 absolute tolerance
)
```

**Edge Cases:**
- Multiple payments with same score → first encountered selected
- Multiple claims matching same payment → only first claim gets it (greedy)
- Ties broken by iteration order (pandas DataFrame order)

**Tools Used:**
- `fuzzywuzzy.fuzz.token_set_ratio` for name similarity
- `datetime.timedelta` for date comparison
- Custom helpers for amount tolerance

---

### Agent 4: Discrepancy Detector

**File:** `src/agents/discrepancy_detector.py`  
**Responsibility:** Categorize and prioritize discrepancies

**Input Schema:**
```python
{
    "matched_df": pd.DataFrame,   # Output from FuzzyMatcher
    "raw_claims": pd.DataFrame,    # Original claims (pre-cleaning)
    "raw_payments": pd.DataFrame   # Original payments (pre-cleaning)
}
```

**Output Schema:**
```python
{
    "discrepancies": list[dict]  # List of discrepancy records (see below),
    "summary": dict              # Aggregate statistics
}
```

**Discrepancy Record Schema:**
```python
{
    "type": str,               # "underpayment" | "overpayment" | "duplicate" |
                                # "unmatched_claim" | "unmatched_payment"
    "claim_id": str | None,    # Present for claim-related types
    "payment_id": str | None,  # Present for payment-related types
    "patient_name": str,
    "amount": float,           # Original amount
    "difference": float | None, # For payment mismatches
    "reason": str,             # Human-readable explanation
    "severity": str,           # "high" | "medium" | "low"
    "priority": str,           # "high" | "normal"
    "match_score": float | None  # For unmatched claims
}
```

**Detection Logic:**

```python
# 1. From matched_df:
for each row where claim_amount != payment_amount:
    if claim_amount > payment_amount:
        type = "underpayment"
        severity = "high" if diff > 100 else "medium"
    else:
        type = "overpayment"
        severity = "medium"

# 2. From raw_claims:
duplicate_claim_ids = find_duplicates(raw_claims["claim_id"])
for each duplicate ID:
    type = "duplicate"
    severity = "high"
    reason = f"Duplicate claim_id appears {count} times"

# 3. From raw_payments:
duplicate_payment_ids = find_duplicates(raw_payments["payment_id"])
# similar logic

# 4. Unmatched claims (claims with no match in matched_df):
matched_claim_ids = set(matched_df["claim_id"])
for each claim in raw_claims:
    if claim_id not in matched_claim_ids:
        type = "unmatched_claim"
        severity = "medium"  # could be high if large amount

# 5. Unmatched payments (symmetrical):
matched_payment_ids = set(matched_df["payment_id"])
for each payment in raw_payments:
    if payment_id not in matched_payment_ids:
        type = "unmatched_payment"

# 6. Flag high-value:
for each discrepancy:
    value = abs(difference or amount)
    if value >= 1000:
        priority = "high"
        reason = "HIGH PRIORITY: " + reason
```

**Summary Statistics Generated:**
```python
{
    "total_claims": int,
    "total_payments": int,
    "matched_count": int,
    "match_rate_pct": float,
    "unmatched_claims": int,
    "unmatched_payments": int,
    "underpayments_count": int,
    "overpayments_count": int,
    "duplicates_count": int,
    "total_discrepancy_value": float,  # sum of all absolute differences
    "high_priority_count": int
}
```

---

### Agent 5: Report Generator

**File:** `src/agents/report_generator.py`  
**Responsibility:** Produce formatted output for finance teams

**Input Schema:**
```python
{
    "matched_df": pd.DataFrame,   # From FuzzyMatcher
    "discrepancies": list[dict],  # From DiscrepancyDetector
    "summary": dict,              # From DiscrepancyDetector
    "format": str                # "csv", "json", "pdf", or "all"
}
```

**Output Schema:**
```python
{
    "<format>": str  # File path to generated report
    for each requested format
}
```

**Format Details:**

#### CSV Report

File structure:
```
# CLAIMS RECONCILIATION REPORT
# Generated: 2026-04-27T15:30:45
# ============================================================

# SECTION 1: SUMMARY (JSON)
{"total_claims": 25, "matched_count": 21, ...}

# SECTION 2: MATCHED RECORDS
claim_id,payment_id,patient_name,claim_amount,payment_amount,match_score,discrepancy_type
101,201,John Smith,1500.0,1400.0,87.5,underpayment
...

# SECTION 3: DISCREPANCIES
type,claim_id,patient_name,amount,difference,reason,priority
underpayment,101,John Smith,1500.0,100.0,"Payment less than claimed",normal
...
```

**Advantages:** Human-readable, Excel-compatible, supports comments

#### JSON Report

```json
{
  "generated_at": "2026-04-27T15:30:45",
  "summary": { ... },
  "matched_count": 21,
  "discrepancy_count": 4,
  "discrepancies": [ ... ],      // Full discrepancy objects
  "matched_records": [ ... ]     // Optional (full matched rows)
}
```

**Advantages:** Machine-readable, API-ready, preserves data types

#### PDF Report (Requires reportlab)

- Title: "Claims Reconciliation Report"
- Subtitle with timestamp
- Summary statistics table (8–10 rows)
- Discrepancy table (top 50 by priority)
- Footer with company name (customizable)

**Advantages:** Professional, printable, shareable with non-technical stakeholders

---

## Agent Collaboration Flow

### Success Path

```
User uploads files
    ↓
FileIngestor.ingest() → Raw DataFrames
    ↓ validation passed
DataCleaner.clean() → Standardized DataFrames
    ↓ clean complete
FuzzyMatcher.match() → Matched pairs + initial discrepancies
    ↓ matching done
DiscrepancyDetector.detect() → Categorized discrepancies + summary
    ↓ analysis complete
ReportGenerator.generate() → Files on disk
    ↓
User downloads reports / views dashboard
```

### Error Handling & Recovery

| Failure Point | Agent Behavior | Recovery |
|---------------|---------------|----------|
| File not found | FileIngestor raises `ValueError` | CLI exits with error code 1; Streamlit shows error message |
| Missing column | FileIngestor raises `ValueError` with missing column names | User fixes CSV header |
| Invalid date | DataCleaner logs warning, sets `NaT` | Matching may fail (date_score = 0); flagged as discrepancy |
| No matches found | FuzzyMatcher returns empty matched_df | All claims become "unmatched_claim" discrepancies |
| PDF lib missing | ReportGenerator logs warning, skips PDF | CSV/JSON still generated |

**Logging at Each Stage:**
- INFO: key metrics (row counts, match rates)
- WARNING: data quality issues (parse failures, no matches)
- ERROR: fatal errors (file read failures)
- DEBUG: per-record details (match scores, decisions)

---

## Performance Considerations

### Current Implementation
- **In-memory processing:** All data loaded into RAM
- **Greedy matching:** O(N×M) comparisons (N claims × M payments)
- **No indexing:** Linear scan for each claim

### Optimization Opportunities (for scale)

1. **Blocking/Canopy Clustering:**
   - Group by `provider_id` first
   - Only match claims/payments within same provider
   - Reduces comparisons from N×M to Σ(N_i × M_i)

2. **Indexing:**
   - Build BK-tree or Trie for patient names
   - O(log N) fuzzy lookup vs O(N)

3. **Vectorization:**
   - Use `pandas.merge()` for exact joins on provider_id + date + amount
   - Only fuzzy match remaining candidates

4. **Batch Processing:**
   - For 100k+ records, process in chunks of 1000
   - Write intermediate results to disk

5. **Parallelization:**
   - `multiprocessing.Pool.map()` across claims
   - Or `concurrent.futures.ThreadPoolExecutor` for I/O-bound (file reads)

---

## Testing Strategy Per Agent

### Unit Tests (tests/test_agents.py)

| Agent | Test Cases |
|-------|-----------|
| FileIngestor | Valid CSV, invalid path, missing columns, wrong format |
| DataCleaner | Name normalization, date parsing, amount cleaning, full pipeline |
| FuzzyMatcher | Exact match, fuzzy name, date tolerance, amount tolerance, no match |
| DiscrepancyDetector | Underpayment, overpayment, duplicates, unmatched, high-value flag |
| ReportGenerator | CSV multi-section, JSON structure, PDF generation |

### Integration Tests

**Full Pipeline Test:**
```python
def test_full_pipeline():
    claims_raw = pd.DataFrame(...)
    payments_raw = pd.DataFrame(...)

    claims = clean_data(claims_raw, "claims")
    payments = clean_data(payments_raw, "payments")
    matched, _ = match_claims_payments(claims, payments)
    result = detect_discrepancies(matched, claims_raw, payments_raw)

    assert result["summary"]["match_rate_pct"] > 80
    assert len(result["discrepancies"]) > 0
```

**Property-Based Testing (stretch):**
- Generate random claims/payments with known matching rules
- Verify matcher recovers ground truth matches
- Check discrepancy detection completeness

---

## Extensibility Points

### Adding a New Matching Criterion

In `FuzzyMatcher._score_match()`:
```python
def _score_match(self, claim, payment):
    scores = {
        "name": self._name_score(claim, payment),
        "date": self._date_score(claim, payment),
        "amount": self._amount_score(claim, payment)
    }

    # NEW: Add insurer weighting (bonus if same insurer)
    if claim["insurer"] == payment["insurer"]:
        scores["insurer"] = 100
    else:
        scores["insurer"] = 0

    weights = {"name": 0.5, "date": 0.3, "amount": 0.2, "insurer": 0.1}
    total = sum(scores[k] * weights[k] for k in scores)

    # Renormalize weights to sum to 1.0
    total /= sum(weights.values())

    return total, scores
```

### Adding a New Discrepancy Type

In `DiscrepancyDetector.detect_all_discrepancies()`:
```python
# Add after existing checks
for _, row in matched_df.iterrows():
    # NEW: Check for late submissions (> 90 days)
    service_date = row.get("date_of_service_dt")
    if service_date and (datetime.now() - service_date).days > 90:
        discrepancies.append({
            "type": "late_submission",
            "claim_id": row["claim_id"],
            "days_overdue": (datetime.now() - service_date).days,
            "reason": "Claim submitted > 90 days after service"
        })
```

### Adding a New Report Format

In `ReportGenerator.generate_report()`:
```python
def generate_excel_report(self, matched_df, discrepancies, summary):
    # Use openpyxl or xlsxwriter
    pass

def generate_report(self, ...):
    outputs = {}
    if format in ["csv", "all"]:
        outputs["csv"] = self.generate_csv_report(...)
    if format == "excel":  # NEW
        outputs["xlsx"] = self.generate_excel_report(...)
    return outputs
```

---

## Agent Independence Principles

1. **No shared mutable state:** Each agent receives data, returns new data
2. **No side effects on inputs:** DataFrames are copied (`df.copy()`) before modification
3. **Clear contracts:** Input/output schemas documented
4. **Testable in isolation:** Mock inputs, verify outputs
5. **Configurable via constructor:** Thresholds injected, not hardcoded

**Violation example (bad):**
```python
# BAD: Global state
matched_global = None

def match(...):
    global matched_global
    matched_global = result  # Side effect
```

**Good:**
```python
def match(...):
    result = ...  # Local variable
    return result  # Pure function
```

---

## Summary

This agent architecture enables:

- **Modularity:** Agents can be swapped or extended independently
- **Maintainability:** Each agent has single responsibility
- **Testability:** Unit tests per agent, integration tests for pipeline
- **Debugging:** Logging at each stage isolates issues
- **Performance:** Bottlenecks can be optimized per-agent

See individual agent source files (`src/agents/*.py`) for implementation details.
