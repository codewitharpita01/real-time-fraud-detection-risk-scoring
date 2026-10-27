import re

from .config import CATEGORIES, MAX_TEXT_CHARS, MAX_URL_CHARS, OFFICIAL_SOURCES
from .model import load_thresholds, predict_text
from .rule_engine import detect_indicators, has_strong_evidence, rule_score
from .url_checks import analyze_url
from .text import normalize_text

TEXT_CATEGORIES = tuple(key for key in CATEGORIES if key not in {"auto", "url"})


def detect_category(text: str) -> str:
    clean = normalize_text(text)
    cues = [
        ("scholarship", ("scholarship", "fellowship", "छात्रवृत्ति")),
        ("government_scheme", ("government scheme", "govt scheme", "subsidy", "yojana", "सरकारी योजना", "योजना")),
        ("internship", ("internship", "intern ", "intern ke", "इंटर्नशिप")),
        ("task", ("paid task", "like and earn", "rating task", "withdrawal fee", "task upgrade", "टास्क")),
        ("work_from_home", ("work from home", "work-from-home", "ghar baithe", "घर बैठे")),
        ("phishing", ("otp", "password", "verify your account", "account suspended", "click this link", "ओटीपी", "पासवर्ड")),
    ]
    for category, terms in cues:
        if any(term in clean for term in terms):
            return category
    return "job"


def _risk_level(score: int, ambiguous_probability: float, strong: bool, thresholds: dict) -> str:
    if strong or score >= int(thresholds["high_min"]):
        return "High Risk"
    if ambiguous_probability >= float(thresholds["manual_ambiguity_probability"]):
        return "Needs Manual Review"
    if score >= int(thresholds["low_max"]) + 1:
        return "Medium Risk"
    return "Low Risk"


def analyze_message(text: str, category: str | None = None) -> dict:
    """Run one local hybrid inference pass and return evidence-rich screening results."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Enter a message before analyzing it.")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"Message exceeds the {MAX_TEXT_CHARS:,}-character input limit.")
    clean = normalize_text(text)
    selected = category or "auto"
    if selected not in CATEGORIES:
        raise ValueError("Choose a supported detection category.")
    detected_category = detect_category(clean) if selected == "auto" else selected
    indicators = detect_indicators(clean)
    rules_score = rule_score(indicators)
    model_prediction = predict_text(clean)
    scam_score = model_prediction["scam_score"] or 0.0

    # The score is a documented blend, not a calibrated probability. Rules have more weight.
    risk_score = round(0.60 * rules_score + 0.40 * scam_score)
    strong_evidence = has_strong_evidence(indicators)
    if strong_evidence:
        risk_score = max(60, risk_score)
    thresholds = load_thresholds()
    ambiguous_probability = model_prediction["probabilities"].get("ambiguous", 0.0)
    risk_level = _risk_level(risk_score, ambiguous_probability, strong_evidence, thresholds)
    if not model_prediction["available"] and not indicators:
        risk_level = "Needs Manual Review"
    if detected_category in {"government_scheme", "scholarship"} and not indicators and risk_level != "High Risk":
        risk_level = "Needs Manual Review"

    if strong_evidence:
        explanation = "A contextual rule found a strong demand or credential request. This can warrant a high-risk review even if the text model score is lower."
    elif indicators:
        explanation = "The result combines contextual warning rules and, when available, a text-model score. These signals can be wrong and do not prove fraud."
    elif risk_level == "Needs Manual Review":
        explanation = "There is too little reliable evidence to classify this message. Verify the organization and offer through independent official channels."
    elif risk_level == "Low Risk":
        explanation = "The available checks found few warning signals. A low score does not establish that the offer is genuine."
    else:
        explanation = "The text model found language associated with risk, but no strong rule confirmed a specific demand. Review the message manually."

    actions = ["Verify the organization using contact details found independently.", "Do not pay a fee to secure a job, internship, task, or withdrawal.", "Never share passwords, OTPs, bank logins, or card security codes."]
    if any(item["id"] == "credential_theft" for item in indicators):
        actions = ["Do not share the requested password, OTP, PIN, or financial credential.", "Contact the named organization through a known official website or phone number.", "If credentials were already shared, contact the relevant provider immediately through its official channel."]
    elif any(item["id"] in {"upfront_recruitment_fee", "task_deposit", "benefit_payment"} for item in indicators):
        actions = ["Pause before paying or transferring money.", "Check the employer, scheme, or scholarship through an independently found official source.", "Do not pay to unlock tasks, confirm a placement, or release a benefit."]
    elif detected_category in {"government_scheme", "scholarship"}:
        actions = ["Treat the claim as unverified until it appears on an official government or institution portal.", "Check eligibility and deadlines on that portal, reached independently.", "Do not pay an individual or share OTPs to claim a benefit."]

    verification_status = "Not verified" if detected_category in {"government_scheme", "scholarship"} else "Unable to verify organization"
    if risk_level == "Needs Manual Review":
        verification_status = "Manual verification recommended"
    evidence = [{"indicator": item["indicator"], "signal": _legacy_signal(item), "phrase": item["evidence"]} for item in indicators]
    compatibility_assessment = {
        "Low Risk": "Low risk", "Medium Risk": "Medium risk", "High Risk": "High risk",
        "Needs Manual Review": "Needs manual verification",
    }[risk_level]
    return {
        "risk_level": risk_level,
        "risk_score": int(max(0, min(100, risk_score))),
        "detected_category": detected_category,
        "detected_category_name": CATEGORIES[detected_category],
        "detected_indicators": [item["indicator"] for item in indicators],
        "evidence": evidence,
        "explanation": explanation,
        "recommended_actions": actions,
        "verification_steps": actions,
        "model_prediction": model_prediction,
        "verification_status": verification_status,
        "rules_score": rules_score,
        "score_method": "0.60 x contextual rule score + 0.40 x uncalibrated model scam score; strong contextual evidence can escalate to High Risk.",
        # Compatibility fields used by the existing Streamlit UI and SQLite history.
        "category": CATEGORIES[detected_category],
        "category_key": detected_category,
        "risk_assessment": compatibility_assessment,
        "indicative_score": int(max(0, min(100, risk_score))),
        "score_label": "Hybrid risk indicator (0-100), not a calibrated probability",
        "signals": [_legacy_signal(item) for item in indicators],
        "precautions": " ".join(actions),
        "official_sources": OFFICIAL_SOURCES if detected_category in {"government_scheme", "scholarship"} else {},
        "optional_model_suggestion": model_prediction if model_prediction["available"] else None,
    }


def _legacy_signal(item: dict) -> str:
    """Keep existing UI labels stable while exposing richer indicator IDs."""
    labels = {
        "upfront_recruitment_fee": "Advance payment requested",
        "task_deposit": "Deposit, upgrade, or withdrawal payment mentioned",
        "credential_theft": "Password, OTP, or credential request",
        "benefit_payment": "Official identity or benefit claim should be checked at its source",
        "benefit_release_fee": "Advance payment requested",
        "high_earnings": "Guaranteed or unusually high earnings promised",
        "pressure": "Urgency or pressure language",
        "suspicious_link": "Suspicious link or lookalike domain present",
    }
    return labels.get(item["id"], item["indicator"])


def analyze(text: str = "", category: str = "auto", url: str = "") -> dict:
    """Compatibility wrapper for existing app/API calls, including URL inspection."""
    text = text.strip()
    url = url.strip()
    if len(url) > MAX_URL_CHARS:
        raise ValueError(f"URL exceeds the {MAX_URL_CHARS:,}-character limit.")
    if not text and not url:
        raise ValueError("Enter message text or a URL to analyze.")
    result = analyze_message(text or url, category if category != "url" else "url") if text else analyze_message(url, "url")
    url_result = analyze_url(url) if url else None
    if url_result and url_result["valid"]:
        result["url_analysis"] = url_result
        for signal in url_result["signals"]:
            result["detected_indicators"].append(signal)
            result["signals"].append(signal)
            result["evidence"].append({"indicator": signal, "signal": signal, "phrase": url_result["host"]})
        if url_result["score"]:
            result["risk_score"] = max(result["risk_score"], min(100, result["rules_score"] + url_result["score"]))
            result["indicative_score"] = result["risk_score"]
        if not text and not url_result["signals"]:
            result["risk_level"] = "Needs Manual Review"
            result["risk_assessment"] = "Needs manual verification"
    else:
        result["url_analysis"] = url_result
    return result
