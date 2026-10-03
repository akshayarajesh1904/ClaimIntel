import os
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import joblib


# ------------------------------------------------------------
# File paths
# ------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(
    BASE_DIR,
    'claim_training_data_v2.csv'
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    'claim_risk_model.pkl'
)


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

data = pd.read_csv(DATA_PATH)

X = data.drop('risk_level', axis=1)
y = data['risk_level']


# ------------------------------------------------------------
# Same train/test split used during training
# ------------------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


# ------------------------------------------------------------
# Load best model
# ------------------------------------------------------------

model = joblib.load(MODEL_PATH)


# ------------------------------------------------------------
# Predictions
# ------------------------------------------------------------

predictions = model.predict(X_test)


# ------------------------------------------------------------
# Confusion matrix
# ------------------------------------------------------------

labels = ['low', 'medium', 'high']

matrix = confusion_matrix(
    y_test,
    predictions,
    labels=labels
)


print()
print("============================================================")
print("             CLAIMINTEL CONFUSION MATRIX")
print("============================================================")
print()

print("                    PREDICTED")
print("                 Low  Medium  High")
print()

print(
    "ACTUAL Low       ",
    matrix[0][0],
    "   ",
    matrix[0][1],
    "     ",
    matrix[0][2]
)

print(
    "ACTUAL Medium    ",
    matrix[1][0],
    "   ",
    matrix[1][1],
    "     ",
    matrix[1][2]
)

print(
    "ACTUAL High      ",
    matrix[2][0],
    "   ",
    matrix[2][1],
    "     ",
    matrix[2][2]
)


# ------------------------------------------------------------
# Correct / wrong predictions
# ------------------------------------------------------------

print()
print("============================================================")
print("             CORRECT / WRONG PREDICTIONS")
print("============================================================")
print()

for i, label in enumerate(labels):

    correct = matrix[i][i]
    total = matrix[i].sum()
    wrong = total - correct

    print(
        label.upper(),
        ":",
        correct,
        "correct out of",
        total,
        "|",
        wrong,
        "wrong"
    )


# ------------------------------------------------------------
# Overall
# ------------------------------------------------------------

total_correct = matrix.diagonal().sum()
total_predictions = matrix.sum()
total_wrong = total_predictions - total_correct

print()
print("------------------------------------------------------------")

print(
    "TOTAL CORRECT:",
    total_correct
)

print(
    "TOTAL WRONG:",
    total_wrong
)

print(
    "TOTAL TESTED:",
    total_predictions
)

print("------------------------------------------------------------")

print()