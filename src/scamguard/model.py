import json
from functools import lru_cache
from pathlib import Path

import joblib

from .config import MODEL_PATH


@lru_cache(maxsize=1)
def load_model(path: Path = MODEL_PATH):
    """Load the trained pipeline once per process; None means rules-only mode."""
    path = Path(path)
    if not path.exists():
        return None
    return joblib.load(path)


@lru_cache(maxsize=1)
def load_thresholds(path: Path | None = None):
    target = Path(path) if path else MODEL_PATH.parent / "risk_thresholds.json"
    defaults = {"low_max": 29, "high_min": 60, "manual_ambiguity_probability": 0.40}
    if not target.exists():
        return defaults
    try:
        values = json.loads(target.read_text(encoding="utf-8"))
        return {**defaults, **values}
    except (OSError, ValueError, TypeError):
        return defaults


def predict_text(text: str) -> dict:
    pipeline = load_model()
    if pipeline is None:
        return {"available": False, "label": "unavailable", "probabilities": {}, "scam_score": None}
    probabilities = pipeline.predict_proba([text])[0]
    classes = pipeline.classes_
    probability_map = {str(label): float(probability) for label, probability in zip(classes, probabilities)}
    label = str(classes[int(probabilities.argmax())])
    scam_score = float(probability_map.get("scam", 0.0) * 100)
    return {
        "available": True, "label": label, "probabilities": probability_map,
        "scam_score": round(scam_score, 1),
        "note": "Uncalibrated dataset-specific model score; not a probability of fraud.",
    }
