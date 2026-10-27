"""Create synthetic labelled transactions and train the fraud classifier."""
from pathlib import Path
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR, MODEL_PATH = ROOT / "data", Path(__file__).resolve().parent / "fraud_model.joblib"
DATA_DIR.mkdir(exist_ok=True)
FEATURES = ["amount", "transaction_type", "location", "device_type", "transaction_hour", "recent_transaction_count", "account_age_days", "previous_transaction_amount", "distance_from_previous_km", "failed_attempts"]

def generate_dataset(rows=4000, seed=42):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "amount": np.round(rng.lognormal(6.2, 1.05, rows), 2),
        "transaction_type": rng.choice(["payment", "transfer", "withdrawal", "purchase", "cash_out"], rows, p=[.30,.20,.13,.27,.10]),
        "location": rng.choice(["Bengaluru", "Mumbai", "Delhi", "Kolkata", "Chennai", "International"], rows, p=[.24,.20,.18,.14,.12,.12]),
        "device_type": rng.choice(["mobile", "web", "atm", "pos"], rows, p=[.43,.27,.12,.18]),
        "transaction_hour": rng.integers(0, 24, rows),
        "recent_transaction_count": rng.poisson(3, rows),
        "account_age_days": rng.integers(1, 3650, rows),
        "previous_transaction_amount": np.round(rng.lognormal(6, 1, rows), 2),
        "distance_from_previous_km": np.round(rng.exponential(22, rows), 2),
        "failed_attempts": rng.poisson(.45, rows),
    })
    score = ((df.amount > 5000).astype(int) + (df.transaction_type == "cash_out").astype(int) + (df.location == "International").astype(int) + df.transaction_hour.isin([0,1,2,3,4]).astype(int) + (df.recent_transaction_count > 7).astype(int) + (df.account_age_days < 60).astype(int) + (df.distance_from_previous_km > 100).astype(int) + (df.failed_attempts > 1).astype(int) + (df.amount > df.previous_transaction_amount * 5).astype(int))
    # A transparent synthetic fraud rule creates meaningful learnable patterns,
    # with a small noise term so this remains a classification exercise.
    df["is_fraud"] = ((score >= 2) | (rng.random(rows) < 0.012)).astype(int)
    return df

def train():
    df = generate_dataset()
    df.to_csv(DATA_DIR / "synthetic_transactions.csv", index=False)
    X, y = df[FEATURES], df["is_fraud"]
    categorical = ["transaction_type", "location", "device_type"]
    preprocessor = ColumnTransformer([( "categories", OneHotEncoder(handle_unknown="ignore"), categorical)], remainder="passthrough")
    pipeline = Pipeline([( "preprocessor", preprocessor), ("classifier", RandomForestClassifier(n_estimators=120, min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=1))])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, stratify=y, random_state=42)
    pipeline.fit(X_train, y_train)
    pred = pipeline.predict(X_test)
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, pred, average="binary", zero_division=0)
    metrics = {"accuracy": round(float(accuracy_score(y_test, pred)), 4), "precision": round(float(precision), 4), "recall": round(float(recall), 4), "f1_score": round(float(f1), 4), "training_rows": len(df)}
    joblib.dump({"model": pipeline, "metrics": metrics, "features": FEATURES}, MODEL_PATH)
    print("Model trained and saved:", MODEL_PATH)
    print(metrics)

if __name__ == "__main__":
    train()
