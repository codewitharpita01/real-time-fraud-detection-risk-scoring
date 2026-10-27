import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
DB_PATH = Path(os.getenv("SCAMSHIELD_DB_PATH", str(ROOT / "scamshield.db")))
MODEL_PATH = Path(os.getenv("SCAMSHIELD_MODEL_PATH", str(ROOT / "artifacts" / "text_model.joblib")))
MAX_TEXT_CHARS = 20_000
MAX_URL_CHARS = 2_048
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_PDF_PAGES = 20

CATEGORIES = {
    "auto": "Automatic detection",
    "job": "Job offer",
    "internship": "Internship",
    "work_from_home": "Work from home",
    "task": "Online task offer",
    "government_scheme": "Government scheme",
    "scholarship": "Scholarship",
    "phishing": "Message / phishing",
    "url": "Website / URL",
}

OFFICIAL_SOURCES = {
    "Scholarship verification": "https://scholarships.gov.in/",
    "Government schemes": "https://www.myscheme.gov.in/",
    "Job and career services": "https://www.ncs.gov.in/",
}
