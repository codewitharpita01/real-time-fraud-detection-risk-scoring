from pathlib import Path
import random
import joblib
import pandas as pd
from sqlalchemy.orm import Session
from .models import Transaction
from .schemas import TransactionInput

MODEL_PATH = Path(__file__).resolve().parents[1] / "ml" / "fraud_model.joblib"

def model_bundle():
    if not MODEL_PATH.exists():
        raise RuntimeError("Model not found. Run: python backend/ml/train_model.py")
    return joblib.load(MODEL_PATH)

def analyze(data: TransactionInput, db: Session):
    bundle = model_bundle()
    values = data.model_dump()
    probability = float(bundle["model"].predict_proba(pd.DataFrame([values]))[0][1])
    risk_score = round(probability * 100)
    level = "HIGH" if risk_score >= 70 else "MEDIUM" if risk_score >= 35 else "LOW"
    prediction = "Suspicious" if probability >= .5 else "Legitimate"
    transaction = Transaction(**values, fraud_probability=round(probability, 4), risk_score=risk_score, risk_level=level, prediction=prediction)
    db.add(transaction); db.commit(); db.refresh(transaction)
    return transaction

def random_transaction():
    return TransactionInput(amount=round(random.lognormvariate(6.2, 1.1), 2), transaction_type=random.choice(["payment", "transfer", "withdrawal", "purchase", "cash_out"]), location=random.choice(["Bengaluru", "Mumbai", "Delhi", "Kolkata", "Chennai", "International"]), device_type=random.choice(["mobile", "web", "atm", "pos"]), transaction_hour=random.randrange(24), recent_transaction_count=random.randint(0, 12), account_age_days=random.randint(1, 3650), previous_transaction_amount=round(random.lognormvariate(6, 1), 2), distance_from_previous_km=round(random.expovariate(1/30), 2), failed_attempts=random.choices([0,1,2,3], [70,20,8,2])[0])
