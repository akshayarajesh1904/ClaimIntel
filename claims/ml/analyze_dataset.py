import pandas as pd

df = pd.read_csv("claim_training_data_final.csv")

print("\n========== DATASET INFO ==========")
print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\n========== COLUMNS ==========")
print(df.columns.tolist())

print("\n========== CLASS DISTRIBUTION ==========")
print(df["risk_level"].value_counts())

print("\n========== DATA TYPES ==========")
print(df.dtypes)

print("\n========== MISSING VALUES ==========")
print(df.isnull().sum())

print("\n========== DUPLICATES ==========")
print("Duplicate rows:", df.duplicated().sum())

print("\n========== NUMERICAL STATISTICS ==========")
print(df.describe(include="all").to_string())

print("\n========== CATEGORICAL DISTRIBUTIONS ==========")

categorical_columns = [
    "accident_type",
    "police_report_status",
    "driver_authorised",
    "third_party_involved",
    "third_party_injury",
    "third_party_damage"
]

for column in categorical_columns:

    if column in df.columns:

        print("\n---", column, "---")
        print(df[column].value_counts(dropna=False))

print("\n========== MEANS BY RISK LEVEL ==========")

numerical_columns = [
    "driver_age",
    "previous_claims",
    "days_to_report",
    "estimated_damage",
    "claim_amount",
    "claim_to_damage_ratio",
    "claim_to_insured_value_ratio"
]

available_numerical = [
    column for column in numerical_columns
    if column in df.columns
]

print(
    df.groupby("risk_level")[available_numerical]
    .mean()
    .round(2)
    .to_string()
)

print("\n========== MEDIANS BY RISK LEVEL ==========")

print(
    df.groupby("risk_level")[available_numerical]
    .median()
    .round(2)
    .to_string()
)

print("\n========== CROSS-TABS ==========")

for column in categorical_columns:

    if column in df.columns:

        print("\n---", column, "vs risk_level ---")

        print(
            pd.crosstab(
                df[column],
                df["risk_level"],
                normalize="index"
            )
            .round(3)
            .to_string()
        )
    