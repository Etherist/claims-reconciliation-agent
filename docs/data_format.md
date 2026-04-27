# Data Format Specifications

## Claims File Format

The claims file contains healthcare services rendered by a provider that need to be reconciled against received payments.

### Required Columns

| Column Name | Type | Description | Example |
|-------------|------|-------------|---------|
| `claim_id` | string | Unique identifier for the claim | "101" |
| `patient_name` | string | Full patient name (can include initials) | "John Smith" or "J. Smith" |
| `date_of_service` | string | Date care was provided (various formats accepted) | "2026-04-01", "01/04/2026" |
| `amount` | string/float | Amount claimed in AUD (can include currency symbols) | "$1,500.00" or 1500.00 |
| `provider_id` | string | Provider/hospital identifier | "PRV123" |
| `insurer` | string | Insurance company name | "Medicare", "Bupa", "Medibank" |

**Optional Columns:**
- `service_code` – procedure code (e.g., "consult1")
- `procedure_description` – human-readable description
- `patient_id` – internal patient reference (ignored by matcher)

### Supported Date Formats

The system automatically parses these formats:
- `YYYY-MM-DD` (ISO) → `2026-04-01`
- `DD/MM/YYYY` → `01/04/2026`
- `DD-MM-YYYY` → `01-04-2026`
- `YYYY/MM/DD` → `2026/04/01`

Invalid dates are logged as warnings and treated as missing.

### Supported Amount Formats

The cleaner strips these characters:
- Currency symbols: `$`, `£`, `€` (though AUD expected)
- Thousands separators: `,` (comma)
- Leading/trailing whitespace

**Examples:**
- `"$1,500.00"` → `1500.00`
- `"1500"` → `1500.00`
- `"  $2,250.50 "` → `2250.50`

### Sample Claims CSV

```csv
claim_id,patient_name,date_of_service,amount,provider_id,insurer,service_code
101,John Smith,2026-04-01,1500.00,PRV123,Medicare,consult1
102,Jane Doe,2026-04-02,2000.00,PRV456,Bupa,consult2
103,John Smyth,2026-04-01,1500.00,PRV123,Medicare,consult1
```

---

## Payments File Format

Payments file contains remittance advice or EFT records from insurers.

### Required Columns

| Column Name | Type | Description | Example |
|-------------|------|-------------|---------|
| `payment_id` | string | Unique payment identifier | "201" |
| `patient_name` | string | Patient name as recorded by insurer | "John Smith" |
| `date_of_service` | string | Service date (same formats as claims) | "2026-04-01" |
| `amount` | string/float | Payment amount received in AUD | "$1,400.00" |
| `provider_id` | string | Provider identifier | "PRV123" |
| `insurer` | string | Insurance company | "Medicare" |

**Optional Columns:**
- `payment_method` – "EFT", "Cheque", "Credit Card"
- `reference_number` – insurer's transaction ID
- `payment_date` – date payment was sent (separate from service date)

### Sample Payments CSV

```csv
payment_id,patient_name,date_of_service,amount,provider_id,insurer,payment_method
201,John Smith,2026-04-01,1400.00,PRV123,Medicare,EFT
202,Jane Doe,2026-04-02,2000.00,PRV456,Bupa,EFT
203,John Smyth,2026-04-01,1500.00,PRV123,Medicare,EFT
```

---

## Australian Insurer Considerations

### Supported Insurers (Demo)

The demo includes these Australian health insurers (case-insensitive):

1. **Medicare** – Australian Government Medicare
2. **Bupa** – Bupa Australia
3. **Medibank** – Medibank Private
4. **HBF** – Western Australia's HBF
5. **nib** – nib Health Insurance

**Note:** Insurer names are standardized to title case internally (e.g., "medicare" → "Medicare").

### Real-World EDI Formats (Stretch)

In production, you'd encounter:

**EDI 837 (Healthcare Claim):**
- Detailed claim submissions to Medicare/insurers
- Complex looping structures (2000A, 2300, 2400)
- UB-04 or HCF claim forms encoded

**EDI 835 (Remittance Advice):**
- Payment advices from insurers
- Includes adjustment codes (CO, OA, PI)
- Patient responsibility amounts

These would require an EDI parser library like `edi-parser` and custom mapping tables.

---

## Data Quality Issues Handled

| Issue | detection | Handling |
|-------|-----------|----------|
| **Name variations** ("J. Smith" vs "John Smith") | Fuzzy matching | Token-set ratio scoring |
| **Typos in names** ("Smyth" vs "Smith") | Fuzzy matching | Levenshtein distance |
| **Date differences** (service recorded 1–2 days apart) | Tolerance check | ±2 days by default |
| **Amount rounding** (bank rounding vs calculated) | Percentage tolerance | ±1% or $10 absolute |
| **Missing leading zeros** ("PRV1" vs "PRV001") | String comparison | Direct match required |
| **Duplicate claim IDs** | Detection agent | Flagged as high severity |
| **Unmatched items** | No match above threshold | Flagged for manual review |

---

## File Size & Performance Limits

### Demo Limits
- **Max file size:** 10 MB per file (configurable via `MAX_FILE_SIZE_MB`)
- **Max rows:** ~10,000 (for demo performance)
- **File types:** CSV and JSON (EDI is stretch)

### Production Recommendations
- Use chunked processing for files >100k rows
- Implement streaming EDI parsing
- Use database backend for history

---

## Validation Rules

The system validates:

1. **File existence** – path must exist
2. **File size** – ≤ `MAX_FILE_SIZE_MB`
3. **Extension** – in `ALLOWED_EXTENSIONS`
4. **Required columns** – all mandatory fields present
5. **Data types** – amounts convertible to float, dates parseable
6. **Value ranges** – amounts ≥ 0, dates not in future (optional)

**Validation Error Example:**
```
ValueError: Missing required columns in claims file: ['provider_id']
```

---

## Column Mapping Reference

If your data uses different column names, pre-process to match required schema:

```python
# Example: rename columns before ingestion
df = df.rename(columns={
    "ClaimID": "claim_id",
    "Patient": "patient_name",
    "ServiceDate": "date_of_service",
    "TotalAmount": "amount",
    "DoctorID": "provider_id",
    "FundName": "insurer"
})
```

---

## Sample Data Generation

To generate more sample files:

```bash
python scripts/generate_sample_data.py
```

This creates:
- `src/data/sample_claims.csv` – 25 mock claims
- `src/data/sample_payments.csv` – 25 mock payments (with intentional discrepancies)

The sample data includes:
- Exact matches (patient, date, amount identical)
- Name typos (Smyth vs Smith)
- Underpayments (payment < claim)
- Overpayments (payment > claim)
- Duplicate payment IDs
- Unmatched claims/payments

---

## Next Steps

- See `docs/demo_guide.md` for running the demo with sample data
- Review `docs/architecture.md` for agent internals
- Read `docs/agent_workflow.md` for pipeline orchestration
