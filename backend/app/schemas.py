from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class TransactionInput(BaseModel):
    amount: float = Field(gt=0, le=10_000_000)
    transaction_type: Literal["payment", "transfer", "withdrawal", "purchase", "cash_out"]
    location: str = Field(min_length=2, max_length=80)
    device_type: Literal["mobile", "web", "atm", "pos"]
    transaction_hour: int = Field(ge=0, le=23)
    recent_transaction_count: int = Field(ge=0, le=1000)
    account_age_days: int = Field(ge=0, le=36500)
    previous_transaction_amount: float = Field(ge=0, le=10_000_000)
    distance_from_previous_km: float = Field(ge=0, le=50000)
    failed_attempts: int = Field(ge=0, le=100)

class AnalysisResult(BaseModel):
    transaction_id: int
    fraud_probability: float
    risk_score: int
    risk_level: str
    prediction: str

class TransactionOut(TransactionInput, AnalysisResult):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime
