from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(40), nullable=False)
    location: Mapped[str] = mapped_column(String(80), nullable=False)
    device_type: Mapped[str] = mapped_column(String(40), nullable=False)
    transaction_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    recent_transaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    account_age_days: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_transaction_amount: Mapped[float] = mapped_column(Float, nullable=False)
    distance_from_previous_km: Mapped[float] = mapped_column(Float, nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    fraud_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    prediction: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    @property
    def transaction_id(self) -> int:
        """API-friendly identifier used by the analysis result schema."""
        return self.id
