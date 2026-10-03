import numpy as np
import pandas as pd
from pathlib import Path


# ============================================================
# CLAIMINTEL - FINAL TRAINING DATASET GENERATOR
# ============================================================
#
# Creates:
#     claim_training_data_final.csv
#
# Dataset:
#     8000 synthetic motor-insurance claim records
#
# Classes:
#     low / medium / high
#
# Important:
#     - No target leakage
#     - Logical third-party dependencies
#     - Realistic financial relationships
#     - Moderate class overlap
#     - Medium-risk claims are intentionally ambiguous
# ============================================================


# ------------------------------------------------------------
# SETTINGS
# ------------------------------------------------------------

SEED = 20260905
N_RECORDS = 8000

OUTPUT_FILE = "claim_training_data_final.csv"

rng = np.random.default_rng(SEED)


# ============================================================
# 1. BASIC CATEGORIES
# ============================================================

ACCIDENT_TYPES = [
    "Collision",
    "Theft",
    "Fire",
    "Natural Disaster",
    "Vandalism",
    "Hit & Run",
    "Hail/Weather",
    "Other",
]

ACCIDENT_PROBABILITIES = [
    0.40,
    0.12,
    0.05,
    0.07,
    0.09,
    0.10,
    0.08,
    0.09,
]


# ============================================================
# 2. GENERATE BASIC CLAIM INFORMATION
# ============================================================

df = pd.DataFrame()

df["accident_type"] = rng.choice(
    ACCIDENT_TYPES,
    size=N_RECORDS,
    p=ACCIDENT_PROBABILITIES
)


# ------------------------------------------------------------
# Driver age
# Mostly 25-55, but realistic full range 18-75.
# ------------------------------------------------------------

age_parts = rng.choice(
    [0, 1, 2],
    size=N_RECORDS,
    p=[0.70, 0.15, 0.15]
)

driver_age = np.empty(N_RECORDS, dtype=int)

# Main population
main_mask = age_parts == 0

driver_age[main_mask] = np.clip(
    rng.normal(40, 9, main_mask.sum()),
    25,
    60
).round().astype(int)

# Younger drivers
young_mask = age_parts == 1

driver_age[young_mask] = rng.integers(
    18,
    26,
    young_mask.sum()
)

# Older drivers
older_mask = age_parts == 2

driver_age[older_mask] = rng.integers(
    61,
    76,
    older_mask.sum()
)

df["driver_age"] = driver_age


# ------------------------------------------------------------
# Previous claims
# Most customers have 0-2 previous claims.
# ------------------------------------------------------------

df["previous_claims"] = np.clip(
    rng.poisson(0.9, N_RECORDS),
    0,
    5
).astype(int)


# ------------------------------------------------------------
# Days to report
# Most claims are reported quickly.
# Some are delayed.
# ------------------------------------------------------------

report_delay_parts = rng.choice(
    [0, 1, 2],
    size=N_RECORDS,
    p=[0.72, 0.22, 0.06]
)

days_to_report = np.zeros(N_RECORDS, dtype=int)

mask = report_delay_parts == 0
days_to_report[mask] = rng.integers(
    0,
    6,
    mask.sum()
)

mask = report_delay_parts == 1
days_to_report[mask] = rng.integers(
    6,
    15,
    mask.sum()
)

mask = report_delay_parts == 2
days_to_report[mask] = rng.integers(
    15,
    31,
    mask.sum()
)

df["days_to_report"] = days_to_report


# ============================================================
# 3. POLICE REPORT STATUS
# Depends partly on accident type.
# ============================================================

police_report_status = []

for accident in df["accident_type"]:

    if accident in ["Theft", "Hit & Run"]:
        status = rng.choice(
            ["reported", "not_reported", "not_required"],
            p=[0.78, 0.15, 0.07]
        )

    elif accident == "Collision":
        status = rng.choice(
            ["reported", "not_reported", "not_required"],
            p=[0.62, 0.20, 0.18]
        )

    elif accident == "Fire":
        status = rng.choice(
            ["reported", "not_reported", "not_required"],
            p=[0.55, 0.15, 0.30]
        )

    elif accident in ["Natural Disaster", "Hail/Weather"]:
        status = rng.choice(
            ["reported", "not_reported", "not_required"],
            p=[0.25, 0.10, 0.65]
        )

    elif accident == "Vandalism":
        status = rng.choice(
            ["reported", "not_reported", "not_required"],
            p=[0.38, 0.42, 0.20]
        )

    else:
        status = rng.choice(
            ["reported", "not_reported", "not_required"],
            p=[0.40, 0.35, 0.25]
        )

    police_report_status.append(status)

df["police_report_status"] = police_report_status


# ============================================================
# 4. DRIVER AUTHORISATION
# ============================================================

df["driver_authorised"] = rng.choice(
    [True, False],
    size=N_RECORDS,
    p=[0.93, 0.07]
)


# ============================================================
# 5. THIRD PARTY INFORMATION
# ============================================================

# First decide whether a third party exists.
df["third_party_involved"] = rng.choice(
    [True, False],
    size=N_RECORDS,
    p=[0.35, 0.65]
)


# Injury is ONLY possible when a third party is involved.
third_party_injury = np.zeros(N_RECORDS, dtype=bool)

involved_mask = df["third_party_involved"].to_numpy()

third_party_injury[involved_mask] = rng.choice(
    [True, False],
    size=involved_mask.sum(),
    p=[0.12, 0.88]
)

df["third_party_injury"] = third_party_injury


# Damage is ONLY possible when a third party is involved.
third_party_damage = np.zeros(N_RECORDS, dtype=bool)

third_party_damage[involved_mask] = rng.choice(
    [True, False],
    size=involved_mask.sum(),
    p=[0.62, 0.38]
)

df["third_party_damage"] = third_party_damage


# ============================================================
# 6. VEHICLE VALUE / DAMAGE / CLAIM AMOUNT
# ============================================================

# Hidden insured value.
# NOT included in final dataset.

insured_value = np.clip(
    rng.lognormal(
        mean=np.log(850000),
        sigma=0.42,
        size=N_RECORDS
    ),
    250000,
    2500000
)


# Estimated damage.
estimated_damage = np.clip(
    rng.lognormal(
        mean=np.log(85000),
        sigma=0.65,
        size=N_RECORDS
    ),
    5000,
    600000
)


# ------------------------------------------------------------
# Claim amount
#
# Most cases:
#     claim < estimated damage
#
# Smaller group:
#     claim approximately equal to estimated damage
#
# Small inflated group:
#     claim > estimated damage
# ------------------------------------------------------------

claim_ratio = np.zeros(N_RECORDS)

ratio_group = rng.choice(
    [0, 1, 2],
    size=N_RECORDS,
    p=[0.72, 0.13, 0.15]
)

# Normal claims
mask = ratio_group == 0

claim_ratio[mask] = np.clip(
    rng.normal(0.80, 0.10, mask.sum()),
    0.55,
    0.98
)

# Nearly full claims
mask = ratio_group == 1

claim_ratio[mask] = np.clip(
    rng.normal(1.00, 0.05, mask.sum()),
    0.92,
    1.08
)

# Inflated claims
mask = ratio_group == 2

claim_ratio[mask] = np.clip(
    rng.normal(1.05, 0.07, mask.sum()),
    0.98,
    1.22
)


claim_amount = estimated_damage * claim_ratio

# Keep amounts inside reasonable bounds.
claim_amount = np.clip(
    claim_amount,
    3000,
    650000
)


# ============================================================
# 7. DERIVED RATIOS
# ============================================================

claim_to_damage_ratio = (
    claim_amount / estimated_damage
)

claim_to_insured_value_ratio = (
    claim_amount / insured_value
)


# ============================================================
# 8. STORE FINANCIAL FEATURES
# ============================================================

df["estimated_damage"] = np.round(
    estimated_damage
).astype(int)

df["claim_amount"] = np.round(
    claim_amount
).astype(int)

df["claim_to_damage_ratio"] = np.round(
    claim_to_damage_ratio,
    3
)

df["claim_to_insured_value_ratio"] = np.round(
    claim_to_insured_value_ratio,
    3
)


# ============================================================
# 9. CREATE LATENT RISK SCORE
# ============================================================
#
# Important:
# risk_level is NOT directly assigned from a single feature.
#
# Multiple claim characteristics interact to create the score.
# Moderate noise is added so the classes overlap.
# ============================================================

risk_score = np.zeros(N_RECORDS)


# ------------------------------------------------------------
# Accident type
# ------------------------------------------------------------

risk_score += df["accident_type"].map({
    "Collision": 0.10,
    "Theft": 0.55,
    "Fire": 0.30,
    "Natural Disaster": -0.05,
    "Vandalism": 0.25,
    "Hit & Run": 0.60,
    "Hail/Weather": -0.10,
    "Other": 0.05,
}).to_numpy()


# ------------------------------------------------------------
# Reporting delay
# ------------------------------------------------------------

risk_score += np.clip(
    df["days_to_report"].to_numpy() / 8.0,
    0,
    3
) * 0.38


# ------------------------------------------------------------
# Previous claims
# ------------------------------------------------------------

risk_score += (
    np.clip(
        df["previous_claims"].to_numpy(),
        0,
        5
    ) * 0.38
)


# ------------------------------------------------------------
# Police report
# ------------------------------------------------------------

risk_score += df["police_report_status"].map({
    "reported": -0.20,
    "not_reported": 0.45,
    "not_required": 0.05,
}).to_numpy()


# ------------------------------------------------------------
# Driver authorisation
# ------------------------------------------------------------

risk_score += np.where(
    df["driver_authorised"],
    -0.25,
    1.10
)


# ------------------------------------------------------------
# Third-party information
# ------------------------------------------------------------

risk_score += np.where(
    df["third_party_involved"],
    0.25,
    0.00
)

risk_score += np.where(
    df["third_party_injury"],
    0.45,
    0.00
)

risk_score += np.where(
    df["third_party_damage"],
    0.25,
    0.00
)


# ------------------------------------------------------------
# Claim-to-damage ratio
# ------------------------------------------------------------

risk_score += (
    np.clip(
        df["claim_to_damage_ratio"].to_numpy() - 0.80,
        -0.30,
        0.40
    ) * 1.50
)


# ------------------------------------------------------------
# Claim-to-insured-value ratio
# ------------------------------------------------------------

risk_score += (
    np.clip(
        df["claim_to_insured_value_ratio"].to_numpy() - 0.08,
        -0.06,
        0.30
    ) * 1.65
)


# ------------------------------------------------------------
# Age
# Small contribution only.
# ------------------------------------------------------------

age_array = df["driver_age"].to_numpy()

risk_score += np.where(
    age_array < 23,
    0.18,
    0.00
)

risk_score += np.where(
    age_array > 70,
    0.12,
    0.00
)


# ============================================================
# 10. INTERACTION EFFECTS
# ============================================================

# Delayed reporting + no police report
risk_score += np.where(
    (
        df["days_to_report"].to_numpy() >= 7
    ) &
    (
        df["police_report_status"].to_numpy()
        == "not_reported"
    ),
    0.40,
    0.00
)


# Multiple previous claims + high claim ratio
risk_score += np.where(
    (
        df["previous_claims"].to_numpy() >= 2
    ) &
    (
        df["claim_to_damage_ratio"].to_numpy() >= 0.95
    ),
    0.35,
    0.00
)


# Theft / hit-and-run + delayed reporting
risk_score += np.where(
    (
        df["accident_type"].isin(
            ["Theft", "Hit & Run"]
        )
    ) &
    (
        df["days_to_report"].to_numpy() >= 5
    ),
    0.30,
    0.00
)


# Unauthorised driver + third party
risk_score += np.where(
    (
        ~df["driver_authorised"].to_numpy()
    ) &
    (
        df["third_party_involved"].to_numpy()
    ),
    0.40,
    0.00
)


# ============================================================
# 11. REALISTIC RANDOM VARIATION
# ============================================================

# This creates overlap between classes without making
# the problem completely random.

risk_score += rng.normal(
    0,
    0.38,
    N_RECORDS
)


# A small number of atypical claims.
atypical_indices = rng.choice(
    N_RECORDS,
    size=int(N_RECORDS * 0.05),
    replace=False
)

risk_score[atypical_indices] += rng.normal(
    0,
    0.30,
    len(atypical_indices)
)


# ============================================================
# 12. ASSIGN BALANCED RISK LEVELS
# ============================================================

# Sort by latent score and divide into three groups.
# This gives a balanced target without copying risk_level
# into any feature.

sorted_indices = np.argsort(risk_score)

risk_level = np.empty(
    N_RECORDS,
    dtype=object
)

risk_level[
    sorted_indices[:2667]
] = "low"

risk_level[
    sorted_indices[2667:5334]
] = "medium"

risk_level[
    sorted_indices[5334:]
] = "high"


df["risk_level"] = risk_level


# ============================================================
# 13. SHUFFLE FINAL DATASET
# ============================================================

df = df.sample(
    frac=1,
    random_state=SEED
).reset_index(
    drop=True
)


# ============================================================
# 14. FINAL COLUMN ORDER
# ============================================================

columns = [
    "accident_type",
    "driver_age",
    "previous_claims",
    "days_to_report",
    "police_report_status",
    "driver_authorised",
    "third_party_involved",
    "third_party_injury",
    "third_party_damage",
    "estimated_damage",
    "claim_amount",
    "claim_to_damage_ratio",
    "claim_to_insured_value_ratio",
    "risk_level",
]

df = df[columns]


# ============================================================
# 15. VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("CLAIMINTEL FINAL DATASET")
print("=" * 70)

print("\nRows:", len(df))
print("Columns:", len(df.columns))

print("\nClass distribution:")
print(
    df["risk_level"]
    .value_counts()
    .sort_index()
)

print("\nMissing values:")
print(
    df.isnull()
    .sum()
    .sum()
)

print("\nDuplicate rows:")
print(
    df.duplicated()
    .sum()
)


# ------------------------------------------------------------
# Logical dependency checks
# ------------------------------------------------------------

invalid_injury = (
    (~df["third_party_involved"]) &
    (df["third_party_injury"])
).sum()

invalid_damage = (
    (~df["third_party_involved"]) &
    (df["third_party_damage"])
).sum()


print("\nLogical consistency:")
print(
    "Invalid third_party_injury rows:",
    invalid_injury
)

print(
    "Invalid third_party_damage rows:",
    invalid_damage
)


# ------------------------------------------------------------
# Financial statistics
# ------------------------------------------------------------

numeric_columns = [
    "driver_age",
    "previous_claims",
    "days_to_report",
    "estimated_damage",
    "claim_amount",
    "claim_to_damage_ratio",
    "claim_to_insured_value_ratio",
]

print("\nOverall numerical statistics:")
print(
    df[numeric_columns]
    .describe()
    .round(3)
    .to_string()
)


# ------------------------------------------------------------
# Statistics by risk level
# ------------------------------------------------------------

print("\nMean values by risk level:")

print(
    df.groupby("risk_level")[numeric_columns]
    .mean()
    .round(3)
    .to_string()
)


print("\nMedian values by risk level:")

print(
    df.groupby("risk_level")[numeric_columns]
    .median()
    .round(3)
    .to_string()
)


# ------------------------------------------------------------
# Accident type vs risk
# ------------------------------------------------------------

print("\nAccident type vs risk:")
print(
    pd.crosstab(
        df["accident_type"],
        df["risk_level"],
        normalize="index"
    )
    .round(3)
    .to_string()
)


# ============================================================
# 16. SAVE CSV
# ============================================================

output_path = Path(OUTPUT_FILE)

df.to_csv(
    output_path,
    index=False
)

print("\n" + "=" * 70)
print("DATASET CREATED SUCCESSFULLY")
print("=" * 70)

print(
    "\nFile:",
    output_path.resolve()
)

print(
    "\nYou can now use this file to train the ClaimIntel ML model."
)