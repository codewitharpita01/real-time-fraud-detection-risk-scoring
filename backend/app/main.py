from datetime import datetime, timedelta
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, func, or_, case
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import Transaction
from .schemas import AnalysisResult, TransactionInput, TransactionOut
from .services import analyze, model_bundle, random_transaction

app = FastAPI(title="Real-Time Fraud Detection API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup(): Base.metadata.create_all(bind=engine)

@app.get("/api/health")
def health(): return {"status": "ok"}

@app.post("/api/analyze", response_model=AnalysisResult)
def analyze_transaction(payload: TransactionInput, db: Session = Depends(get_db)):
    try:
        return analyze(payload, db)
    except RuntimeError as exc: raise HTTPException(503, str(exc))

@app.post("/api/simulate", response_model=AnalysisResult)
def simulate(db: Session = Depends(get_db)):
    try: return analyze(random_transaction(), db)
    except RuntimeError as exc: raise HTTPException(503, str(exc))

@app.get("/api/transactions", response_model=list[TransactionOut])
def transactions(search: str = "", risk_level: str = "", sort_by: str = Query("created_at", pattern="^(created_at|amount|risk_score)$"), order: str = Query("desc", pattern="^(asc|desc)$"), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    q = db.query(Transaction)
    if search: q = q.filter(or_(Transaction.location.ilike(f"%{search}%"), Transaction.transaction_type.ilike(f"%{search}%"), Transaction.prediction.ilike(f"%{search}%")))
    if risk_level in {"LOW", "MEDIUM", "HIGH"}: q = q.filter(Transaction.risk_level == risk_level)
    column = getattr(Transaction, sort_by)
    return q.order_by(column.asc() if order == "asc" else column.desc()).limit(limit).all()

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    total = db.query(func.count(Transaction.id)).scalar() or 0
    suspicious = db.query(func.count(Transaction.id)).filter(Transaction.prediction == "Suspicious").scalar() or 0
    risks = {level: db.query(func.count(Transaction.id)).filter(Transaction.risk_level == level).scalar() or 0 for level in ["HIGH", "MEDIUM", "LOW"]}
    recent = db.query(Transaction).order_by(desc(Transaction.created_at)).limit(8).all()
    return {"total_transactions": total, "suspicious_transactions": suspicious, "risk_counts": risks, "recent_transactions": recent}

@app.get("/api/analytics")
def analytics(db: Session = Depends(get_db)):
    fraud = db.query(func.count(Transaction.id)).filter(Transaction.prediction == "Suspicious").scalar() or 0
    total = db.query(func.count(Transaction.id)).scalar() or 0
    risk = [{"name": level, "value": db.query(func.count(Transaction.id)).filter(Transaction.risk_level == level).scalar() or 0} for level in ["LOW", "MEDIUM", "HIGH"]]
    since = datetime.utcnow() - timedelta(days=6)
    trend = db.query(func.date(Transaction.created_at).label("date"), func.count(Transaction.id).label("transactions"), func.sum(case((Transaction.prediction == "Suspicious", 1), else_=0)).label("fraud")).filter(Transaction.created_at >= since).group_by(func.date(Transaction.created_at)).order_by("date").all()
    return {"fraud_vs_legitimate": [{"name": "Legitimate", "value": total-fraud}, {"name": "Suspicious", "value": fraud}], "risk_distribution": risk, "transaction_trends": [{"date": r.date, "transactions": r.transactions, "fraud": int(r.fraud or 0)} for r in trend]}

@app.get("/api/model-metrics")
def metrics():
    try: return model_bundle()["metrics"]
    except RuntimeError as exc: raise HTTPException(503, str(exc))
