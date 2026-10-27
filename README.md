# Real-Time AI-Based Fraud Detection System for Indian Students

ScamShield is a local Streamlit prototype for screening job, internship, work-from-home, online task, government scheme, scholarship, phishing, and URL submissions. It provides evidence and safety guidance; it does not prove fraud or authenticity.

## Architecture

```text
Browser -> Streamlit (app.py) -> explainable text/rule analyzer
                               -> offline URL structure checks
                               -> optional local OCR (Tesseract)
                               -> consent-based SQLite summary history
Optional API -> FastAPI (src/scamguard/api.py) -> same analyzer
Labeled splits -> word/character TF-IDF + Logistic Regression -> cached local text model
                            -> contextual rule engine -> blended risk indicator
```

No URL is opened, fetched, or sent to a reputation service. The app does not monitor WhatsApp, email, browsers, or the internet. Government and scholarship claims are not checked against live registries; the official links shown are reference starting points only. The hybrid score combines 60% of the contextual rule score with 40% of the uncalibrated model scam score; a strong rule can force High Risk. This is an indicator, not a calibrated probability.

## Project layout

```text
app.py                         Streamlit pages and dashboard
src/scamguard/analyzer.py      multilingual phrase signals and risk explanation
src/scamguard/url_checks.py    offline URL features
src/scamguard/file_scanner.py  bounded image/PDF extraction and OCR
src/scamguard/company_check.py cautious local company/recruiter consistency checks
src/scamguard/database.py      consent-based summary history and feedback
src/scamguard/reporting.py    CSV/PDF report generation
src/scamguard/api.py           optional FastAPI service
scripts/train_model.py         reproducible train/validation/test evaluation
data/README.md                 dataset sources, label definitions, limitations
tests/                          unit and input-validation tests
```

## Windows setup in VS Code

Use Python 3.10 or newer. In the VS Code terminal, from the project folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again. The OCR Python package is included, but the Tesseract OCR engine must also be installed separately. Follow the [Tesseract Windows installation guide](https://tesseract-ocr.github.io/tessdoc/Installation.html), add the install directory to PATH, and restart VS Code. To enable Hindi OCR, install Hindi language data in Tesseract and set `SCAMSHIELD_OCR_LANG=eng+hin` in `.env`. Typed Hindi/Hinglish phrase checks work without OCR.

Start the application:

```powershell
python -m streamlit run app.py
```

Optional API, in another terminal:

```powershell
python -m uvicorn src.scamguard.api:app --reload
```

Open the local address Streamlit prints, normally `http://localhost:8501`. API docs are at `http://127.0.0.1:8000/docs`.

## Features and limits

- Eight categories plus automatic category selection. Screening rules include English and selected Devanagari/Hinglish payment, earning, and OTP phrases. Language alone is never a warning signal.
- Image upload accepts PNG/JPG/JPEG. PDF uploads are limited to 15 MB and 20 pages. Extracted text is shown for correction before analysis. Files are processed in memory and are not saved.
- OCR failure gives a manual text-entry fallback. Scanned PDFs require the separate Tesseract engine. Password-protected PDFs are rejected.
- URL checks look for syntax issues, shorteners, raw IPs, punycode, long/multi-level hosts, HTTP, suspicious tokens, and configured official-domain lookalikes. No DNS, certificate, reputation, or page-content check is made.
- Company/recruiter checks identify a few local inconsistencies such as free email domains and a mismatch with the supplied website. They always report `Unable to verify`; no identity or employment claim is confirmed.
- Government/scholarship checking shows known official starting points: [National Scholarship Portal](https://scholarships.gov.in/), [myScheme](https://www.myscheme.gov.in/), and [National Career Service](https://www.ncs.gov.in/). It does not validate the submitted scheme or award.
- Analysis history is off by default. Opting in stores only time, category, risk level/score, warning labels, content type, and verification status. It does not save submitted text, URLs, images, PDFs, or feedback comments. History and associated feedback can be deleted.
- User feedback is separate from ground-truth labels and is never used to retrain a model.
- CSV and PDF reports omit the submitted content and include an explicit limitation statement.
- Analytics show consented local activity separately from labeled-dataset model metrics. No demo metrics or fake activity are included.

Risk categories use configurable cutoffs: the initial scale is 0-29 Low, 30-59 Medium, and 60-100 High; strong contextual evidence can escalate to High Risk, while ambiguous or benefit claims may need manual review. The training run tunes cutoffs on the validation split and saves them in `artifacts/risk_thresholds.json`. The current synthetic validation split selected 25 as the Low Risk maximum and 55 as the High Risk threshold. A score is an indicator, not a calibrated probability; a low-risk result is not a safety guarantee.

## Dataset and optional text model

The project includes balanced, explicitly synthetic train, validation, and held-out test files, plus locally generated model artifacts under ignored `artifacts/`. The dataset plan lists suitable public sources and explains why their label meanings and age limit what can be inferred. For example, the SMS Spam Collection labels spam/ham, not fraud/phishing, while EMSCAD covers historical job postings rather than all eight categories. See [data/README.md](data/README.md).

The repository includes balanced synthetic train, validation, and held-out test files. Recreate them and train the model with:

```powershell
python data/build_seed_dataset.py
python scripts/train_model.py --data-dir data --output artifacts
```

Training and inference share Unicode normalization, word n-grams, character n-grams, and class-weighted Logistic Regression. The trainer rejects duplicate normalized messages or shared source IDs across splits, tunes the score cutoffs on validation data, and evaluates the held-out test split. It writes the model, vectorizer, tuned thresholds, precision/recall/F1 reports, confusion matrices, and false-positive/false-negative examples under `artifacts/`. The current data are synthetic; all metrics are only results on these authored examples and are not real-world model performance. Replace or supplement them with legally usable and independently labeled data before drawing deployment conclusions. See [data/README.md](data/README.md).

## Tests

```powershell
python -m pytest tests -q
```

The tests cover English, Hindi/Hinglish, benign urgent/free wording, prevention-context suppression, strong-rule escalation, shortener detection, invalid and oversized uploads, privacy-preserving history, and company-check caveats. OCR recognition quality depends on local Tesseract installation and language packs.

## Common setup issues

- `streamlit` or `uvicorn` not found: activate `.venv` and run `python -m pip install -r requirements.txt`.
- OCR engine not found: install Tesseract separately, add it to PATH, restart VS Code, or paste extracted text manually.
- `ModuleNotFoundError: src`: run Streamlit or Uvicorn from the project root.
- Empty input: provide text or a URL; blank analyses are rejected.
- No history after restart: confirm that the app uses the project root and check `SCAMSHIELD_DB_PATH` in `.env`.
- No model suggestion: no optional artifact is bundled. Prepare a labeled dataset and run the training command.
- URL lacks a reputation result: the project intentionally performs offline structure checks only.
