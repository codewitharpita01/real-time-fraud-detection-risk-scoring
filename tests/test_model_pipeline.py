from src.scamguard import analyzer
from src.scamguard.analyzer import analyze_message


def test_analyze_message_returns_the_documented_fields():
    result = analyze_message("A recruiter asks candidates to pay a registration fee to secure a job.", "job")
    expected = {"risk_level", "risk_score", "detected_category", "detected_indicators", "evidence",
                "explanation", "recommended_actions", "model_prediction", "verification_status"}
    assert expected.issubset(result)
    assert result["risk_level"] == "High Risk"
    assert result["risk_score"] >= 60


def test_scam_prevention_discussion_is_not_flagged_as_a_demand():
    result = analyze_message("Scam prevention: never pay a registration fee for a job.", "job")
    assert "Upfront recruitment or internship fee demanded" not in result["detected_indicators"]
    assert result["risk_level"] != "High Risk"


def test_strong_rules_escalate_even_when_model_is_low(monkeypatch):
    monkeypatch.setattr(analyzer, "predict_text", lambda text: {
        "available": True, "label": "legitimate", "probabilities": {"scam": 0.05, "legitimate": 0.85, "ambiguous": 0.10}, "scam_score": 5.0,
    })
    result = analyze_message("Pay a registration fee to secure this job before the interview.", "job")
    assert result["model_prediction"]["label"] == "legitimate"
    assert result["risk_level"] == "High Risk"
    assert result["risk_score"] >= 60


def test_heldout_seed_data_is_balanced_and_multilingual():
    import pandas as pd
    from pathlib import Path

    data = pd.read_csv(Path("data/test.csv"))
    assert data.label.value_counts().nunique() == 1
    assert set(data.language) == {"en", "hinglish", "hi"}
    assert data.category.nunique() == 8
    assert set(data.source_type) == {"synthetic"}
