import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix
)


# ============================================================
# CLAIMINTEL V3.1 MODEL TRAINING
# Random Forest vs Gradient Boosting
# ============================================================

DATA_FILE = "claim_training_data_final.csv"

df = pd.read_csv(DATA_FILE)

print("=" * 70)
print("CLAIMINTEL V3.1 MODEL TRAINING")
print("=" * 70)

print(f"\nDataset: {DATA_FILE}")
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")

print("\nRisk-level distribution:")
print(df["risk_level"].value_counts())


# ============================================================
# FEATURES AND TARGET
# ============================================================

X = df.drop("risk_level", axis=1)
y = df["risk_level"]


# ============================================================
# FEATURE GROUPS
# ============================================================

categorical_features = [
    "accident_type",
    "police_report_status",
    "driver_authorised",
    "third_party_involved",
    "third_party_injury",
    "third_party_damage",
]

numerical_features = [
    "driver_age",
    "previous_claims",
    "days_to_report",
    "estimated_damage",
    "claim_amount",
    "claim_to_damage_ratio",
    "claim_to_insured_value_ratio",
]


# ============================================================
# PREPROCESSING
# ============================================================

categorical_pipeline = Pipeline([
    (
        "imputer",
        SimpleImputer(strategy="most_frequent")
    ),
    (
        "onehot",
        OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=False
        )
    ),
])

numerical_pipeline = Pipeline([
    (
        "imputer",
        SimpleImputer(strategy="median")
    )
])


preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            categorical_pipeline,
            categorical_features
        ),
        (
            "numerical",
            numerical_pipeline,
            numerical_features
        ),
    ]
)


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nTraining records:", len(X_train))
print("Testing records :", len(X_test))


# ============================================================
# RANDOM FOREST
# ============================================================

rf_model = Pipeline([
    (
        "preprocessor",
        preprocessor
    ),
    (
        "classifier",
        RandomForestClassifier(
            n_estimators=250,
            random_state=42,
            class_weight="balanced",
            min_samples_leaf=3,
            max_features="sqrt",
            n_jobs=-1
        )
    )
])

print("\n" + "=" * 70)
print("TRAINING RANDOM FOREST")
print("=" * 70)

rf_model.fit(X_train, y_train)

rf_predictions = rf_model.predict(X_test)

rf_accuracy = accuracy_score(
    y_test,
    rf_predictions
)

rf_f1 = f1_score(
    y_test,
    rf_predictions,
    average="macro"
)

print(f"\nRandom Forest Accuracy : {rf_accuracy * 100:.2f}%")
print(f"Random Forest Macro F1 : {rf_f1:.4f}")

print("\nRandom Forest Classification Report:")

print(
    classification_report(
        y_test,
        rf_predictions,
        labels=["low", "medium", "high"],
        zero_division=0
    )
)

print("Random Forest Confusion Matrix:")

rf_cm = confusion_matrix(
    y_test,
    rf_predictions,
    labels=["low", "medium", "high"]
)

print(rf_cm)


# ============================================================
# GRADIENT BOOSTING
# ============================================================

gb_model = Pipeline([
    (
        "preprocessor",
        preprocessor
    ),
    (
        "classifier",
        GradientBoostingClassifier(
            n_estimators=180,
            learning_rate=0.06,
            max_depth=2,
            min_samples_leaf=6,
            random_state=42
        )
    )
])

print("\n" + "=" * 70)
print("TRAINING GRADIENT BOOSTING")
print("=" * 70)

gb_model.fit(X_train, y_train)

gb_predictions = gb_model.predict(X_test)

gb_accuracy = accuracy_score(
    y_test,
    gb_predictions
)

gb_f1 = f1_score(
    y_test,
    gb_predictions,
    average="macro"
)

print(f"\nGradient Boosting Accuracy : {gb_accuracy * 100:.2f}%")
print(f"Gradient Boosting Macro F1 : {gb_f1:.4f}")

print("\nGradient Boosting Classification Report:")

print(
    classification_report(
        y_test,
        gb_predictions,
        labels=["low", "medium", "high"],
        zero_division=0
    )
)

print("Gradient Boosting Confusion Matrix:")

gb_cm = confusion_matrix(
    y_test,
    gb_predictions,
    labels=["low", "medium", "high"]
)

print(gb_cm)


# ============================================================
# SELECT BEST MODEL
# ============================================================

if gb_f1 > rf_f1:
    best_model = gb_model
    best_name = "Gradient Boosting"
    best_accuracy = gb_accuracy
    best_f1 = gb_f1
else:
    best_model = rf_model
    best_name = "Random Forest"
    best_accuracy = rf_accuracy
    best_f1 = rf_f1


# ============================================================
# SAVE BEST MODEL
# ============================================================

MODEL_FILE = "claim_risk_model.pkl"

joblib.dump(
    best_model,
    MODEL_FILE
)


# ============================================================
# SAVE COMPARISON REPORT
# ============================================================

REPORT_FILE = "model_comparison_v3_1.txt"

with open(REPORT_FILE, "w", encoding="utf-8") as report:

    report.write("ClaimIntel V3.1 Model Comparison\n")
    report.write("=" * 70 + "\n\n")

    report.write(f"Dataset: {DATA_FILE}\n")
    report.write(f"Records: {len(df)}\n")
    report.write(f"Training records: {len(X_train)}\n")
    report.write(f"Testing records: {len(X_test)}\n\n")

    report.write("Random Forest\n")
    report.write("-" * 70 + "\n")
    report.write(
        f"Accuracy: {rf_accuracy * 100:.2f}%\n"
    )
    report.write(
        f"Macro F1: {rf_f1:.4f}\n\n"
    )

    report.write(
        classification_report(
            y_test,
            rf_predictions,
            labels=["low", "medium", "high"],
            zero_division=0
        )
    )

    report.write("\nConfusion Matrix:\n")
    report.write(str(rf_cm))
    report.write("\n\n")

    report.write("Gradient Boosting\n")
    report.write("-" * 70 + "\n")
    report.write(
        f"Accuracy: {gb_accuracy * 100:.2f}%\n"
    )
    report.write(
        f"Macro F1: {gb_f1:.4f}\n\n"
    )

    report.write(
        classification_report(
            y_test,
            gb_predictions,
            labels=["low", "medium", "high"],
            zero_division=0
        )
    )

    report.write("\nConfusion Matrix:\n")
    report.write(str(gb_cm))
    report.write("\n\n")

    report.write("Selected Model\n")
    report.write("-" * 70 + "\n")
    report.write(f"Model: {best_name}\n")
    report.write(
        f"Accuracy: {best_accuracy * 100:.2f}%\n"
    )
    report.write(
        f"Macro F1: {best_f1:.4f}\n"
    )


# ============================================================
# FINAL RESULT
# ============================================================

print("\n" + "=" * 70)
print("MODEL SELECTION")
print("=" * 70)

print(f"\nSelected model: {best_name}")
print(f"Accuracy: {best_accuracy * 100:.2f}%")
print(f"Macro F1: {best_f1:.4f}")

print(f"\nSaved model to: {MODEL_FILE}")
print(f"Saved report to: {REPORT_FILE}")

print("\nTraining completed successfully.")