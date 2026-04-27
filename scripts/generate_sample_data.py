"""
Generate synthetic claims/payments data for demo purposes.
Creates realistic Australian healthcare transaction samples.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# Australian insurers
INSURERS = ["Medicare", "Bupa", "Medibank", "HBF", "nib"]

# Common providers
PROVIDERS = {
    "PRV123": "Sydney General Hospital",
    "PRV456": "Melbourne Medical Centre",
    "PRV789": "Brisbane Specialist Clinic",
    "PRV012": "Perth Day Surgery",
    "PRV345": "Adelaide Health Partners",
    "PRV678": "Canberra Medical Hub",
    "PRV901": "Hobart Regional Hospital",
    "PRV234": "Darwin City Clinic",
    "PRV567": "Wollongong Medical Centre",
    "PRV890": "Newcastle Private Hospital"
}

# Sample patient names (Australian style)
SURNAMES = [
    "Smith", "Jones", "Williams", "Brown", "Wilson", "Taylor", "Johnson",
    "White", "Lee", "Harris", "Martin", "Clark", "Lewis", "Walker", "Hall",
    "Young", "Allen", "Wright", "Scott", "Thompson", "Jackson", "Moore"
]
GIVEN_NAMES = [
    "John", "Jane", "Michael", "Sarah", "David", "Emma", "Robert", "Emily",
    "Christopher", "Jessica", "Matthew", "Amanda", "Daniel", "Melissa",
    "William", "Patricia", "Andrew", "Linda", "Joshua", "Elizabeth"
]

# Service codes and amounts
SERVICES = [
    ("consult1", "General Consultation", 150.00, 300.00),
    ("consult2", "Specialist Consultation", 200.00, 500.00),
    ("consult3", "Follow-up Visit", 100.00, 250.00),
    ("consult4", "Specialist Procedure", 300.00, 800.00),
    ("consult5", "Chronic Disease Management", 150.00, 350.00),
    ("consult6", "Telehealth", 100.00, 250.00),
    ("consult7", "Health Assessment", 200.00, 400.00),
    ("consult8", "Vaccination", 80.00, 200.00),
    ("test1", "Blood Test", 50.00, 150.00),
    ("test2", "Pathology", 100.00, 300.00),
    ("test3", "X-ray", 80.00, 200.00),
    ("test4", "Ultrasound", 150.00, 400.00),
    ("test5", "ECG", 100.00, 250.00),
    ("proc1", "Endoscopy", 800.00, 2000.00),
    ("proc2", "Minor Procedure", 500.00, 1200.00),
    ("proc3", "Cataract Surgery", 1500.00, 3000.00),
    ("proc4", "Chemotherapy Administration", 1200.00, 3000.00),
    ("surg1", "Minor Surgery", 1000.00, 2500.00),
    ("surg2", "Day Surgery", 2000.00, 5000.00),
    ("surg3", "Arthroscopy", 2500.00, 6000.00),
    ("surg4", "Laparoscopic Surgery", 3000.00, 8000.00),
    ("surg5", "Orthopedic Procedure", 4000.00, 10000.00),
    ("surg6", "Hernia Repair", 2000.00, 4500.00),
    ("scan1", "MRI Scan", 600.00, 1500.00)
]


def generate_patient_name():
    """Generate a random patient name."""
    given = random.choice(GIVEN_NAMES)
    surname = random.choice(SURNAMES)
    # Occasionally include middle initial or typo
    if random.random() < 0.1:  # 10% chance of typo
        surname = surname.replace('c', 'k').replace('ie', 'y')  # e.g., Smith → Smyth
    return f"{given} {surname}"


def generate_claim(
    claim_id: int,
    start_date: datetime,
    end_date: datetime
) -> dict:
    """Generate a single claim record."""
    patient = generate_patient_name()
    service_code, description, min_amt, max_amt = random.choice(SERVICES)
    amount = round(random.uniform(min_amt, max_amt), 2)
    provider_id = random.choice(list(PROVIDERS.keys()))
    insurer = random.choice(INSURERS)
    service_date = start_date + timedelta(
        days=random.randint(0, (end_date - start_date).days)
    )

    return {
        "claim_id": str(claim_id),
        "patient_name": patient,
        "date_of_service": service_date.strftime("%Y-%m-%d"),
        "amount": f"${amount:,.2f}",
        "provider_id": provider_id,
        "insurer": insurer.lower(),  # Sometimes lowercase
        "service_code": service_code,
        "procedure_description": description
    }


def generate_payment(
    payment_id: int,
    claim: dict,
    underpay_prob: float = 0.1,
    overpay_prob: float = 0.05,
    duplicate_prob: float = 0.02
) -> dict:
    """
    Generate a payment for a given claim.
    May intentionally introduce discrepancies.
    """
    patient = claim["patient_name"]
    service_date = claim["date_of_service"]
    base_amount = float(claim["amount"].replace("$", "").replace(",", ""))
    provider_id = claim["provider_id"]
    insurer = claim["insurer"].title()  # Standardize

    # Simulate discrepancy
    r = random.random()
    if r < underpay_prob:
        # Underpayment: 80-95% of claim
        pct = random.uniform(0.80, 0.95)
        amount = round(base_amount * pct, 2)
    elif r < underpay_prob + overpay_prob:
        # Overpayment: 105-120% of claim
        pct = random.uniform(1.05, 1.20)
        amount = round(base_amount * pct, 2)
    else:
        # Exact or rounding difference
        amount = base_amount

    # Handle duplicate payment IDs (stretch: duplicate detection test)
    payment_id_str = str(payment_id)
    if random.random() < duplicate_prob:
        payment_id_str = str(random.randint(1000, 1999))  # Potential duplicate block

    return {
        "payment_id": payment_id_str,
        "patient_name": patient,
        "date_of_service": service_date,
        "amount": f"${amount:,.2f}",
        "provider_id": provider_id,
        "insurer": insurer,
        "payment_method": random.choice(["EFT", "EFT", "EFT", "Cheque"]),
        "reference_number": f"REF{payment_id:06d}"
    }


def generate_dataset(
    num_claims: int = 25,
    start_date: str = "2026-04-01",
    end_date: str = "2026-04-30",
    seed: int = 42
):
    """
    Generate complete claims and payments dataset.

    Args:
        num_claims: Number of claims to generate
        start_date: Inclusive start date (YYYY-MM-DD)
        end_date: Inclusive end date
        seed: Random seed for reproducibility

    Returns:
        Tuple of (claims_df, payments_df)
    """
    random.seed(seed)
    np.random.seed(seed)

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    claims = []
    for i in range(1, num_claims + 101):  # Extra IDs to allow gaps
        claims.append(generate_claim(i, start, end))

    claims_df = pd.DataFrame(claims)

    # Generate payments (some may be duplicates/unmatched)
    payments = []
    payment_id_counter = 1
    for _, claim in claims_df.iterrows():
        # Each claim gets at least one payment (maybe with discrepancy)
        payment = generate_payment(payment_id_counter, claim)
        payments.append(payment)
        payment_id_counter += 1

    # Add some extra payments that have no matching claims (unmatched)
    num_extra_payments = max(1, num_claims // 10)  # ~10% unmatched
    for i in range(num_extra_payments):
        extra_payment = generate_payment(payment_id_counter, {
            "patient_name": generate_patient_name(),
            "date_of_service": (start + timedelta(days=random.randint(0, 29))).strftime("%Y-%m-%d"),
            "amount": f"${random.uniform(200, 3000):,.2f}",
            "provider_id": random.choice(list(PROVIDERS.keys())),
            "insurer": random.choice(INSURERS).lower()
        })
        # Use payment IDs that won't match any claim ID
        extra_payment["payment_id"] = str(1000 + payment_id_counter)
        payments.append(extra_payment)
        payment_id_counter += 1

    payments_df = pd.DataFrame(payments)

    return claims_df, payments_df


if __name__ == "__main__":
    # Output directory
    output_dir = os.path.join("src", "data")
    os.makedirs(output_dir, exist_ok=True)

    print("🏥 Generating sample claims and payments data...")

    claims, payments = generate_dataset(num_claims=25, seed=42)

    # Save
    claims_path = os.path.join(output_dir, "sample_claims.csv")
    payments_path = os.path.join(output_dir, "sample_payments.csv")

    claims.to_csv(claims_path, index=False)
    payments.to_csv(payments_path, index=False)

    print(f"✅ Generated {len(claims)} claims → {claims_path}")
    print(f"✅ Generated {len(payments)} payments → {payments_path}")

    # Show stats
    print("\n📊 Sample Stats:")
    print(f"Claims date range: {claims['date_of_service'].min()} to {claims['date_of_service'].max()}")
    print(f"Payments date range: {payments['date_of_service'].min()} to {payments['date_of_service'].max()}")
    print(f"Unique insurers: {claims['insurer'].nunique()}")
    print(f"Unique providers: {claims['provider_id'].nunique()}")

    print("\n💡 Run: streamlit run src/app/streamlit_app.py")
