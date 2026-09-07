# Real-Time Fraud Detection & Transaction Risk Scoring System

A full-stack academic fintech project that trains a Random Forest on generated transaction data, scores live transactions through FastAPI, stores results in SQLite, and displays live operational data in a React dashboard.

## Features

- Real transaction risk analysis with fraud probability, 0–100 score, risk level, and prediction.
- Random Forest pipeline with one-hot encoding for transaction type, location, and device.
- Reproducible synthetic dataset and saved model metrics (accuracy, precision, recall, F1).
- SQLite transaction history with API-backed search, risk filtering, and sorting.
- Dashboard and analytics charts built with Recharts.
- Local simulation endpoint to produce, classify, persist, and immediately surface transactions.

## Project structure

```
frontend/                 React + Vite + CSS + Recharts
backend/app/              FastAPI API, SQLAlchemy models, schemas, services
backend/ml/train_model.py Synthetic data generation and Random Forest training
backend/data/             Generated database and dataset (not committed)
requirements.txt          Python dependencies
```

## Windows setup and run

Run the following in PowerShell from the project directory.

### 1. Create and activate a virtual environment

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once in the current shell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Install Python dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Train the ML model

This creates `backend/data/synthetic_transactions.csv` and `backend/ml/fraud_model.joblib`.

```powershell
python backend/ml/train_model.py
```

### 4. Initialize the database

The backend automatically creates the SQLite tables at startup. To explicitly initialize them:

```powershell
python -c "from backend.app.database import Base, engine; from backend.app import models; Base.metadata.create_all(bind=engine); print('Database initialized')"
```

### 5. Start the backend

```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
```

Open API documentation at http://localhost:8000/docs.

### 6. Install frontend dependencies and start Vite

Open a second PowerShell window in the project directory:

```powershell
cd frontend
npm install
npm run dev
```

Open the displayed URL, normally http://localhost:5173.

## API endpoints

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/api/analyze` | Classifies and stores a provided transaction |
| `POST` | `/api/simulate` | Generates, classifies, and stores a local simulated transaction |
| `GET` | `/api/dashboard` | Live dashboard counts and latest transactions |
| `GET` | `/api/transactions` | History with `search`, `risk_level`, `sort_by`, and `order` query filters |
| `GET` | `/api/analytics` | Chart datasets calculated from SQLite history |
| `GET` | `/api/model-metrics` | Training quality metrics from saved model |

## GitHub commands

These commands create a local repository and push it to a new GitHub repository under **codewitharpita01**. They do not require or expose a password/token; authenticate via the GitHub CLI or browser when prompted.

```powershell
git init
git add .
git commit -m "Initial commit: real-time fraud detection system"
gh repo create codewitharpita01/real-time-fraud-detection --public --source=. --remote=origin --push
```

If the repository already exists on GitHub, use:

```powershell
git init
git branch -M main
git add .
git commit -m "Initial commit: real-time fraud detection system"
git remote add origin https://github.com/codewitharpita01/real-time-fraud-detection.git
git push -u origin main
```

## Notes

This project uses synthetic data for academic demonstration only. A production fraud system requires reviewed labels, monitoring for model drift and bias, authentication, encryption, rate limiting, audit logs, and human investigation workflows.
