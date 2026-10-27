import pytest

from src.scamguard.analyzer import analyze
from src.scamguard.url_checks import analyze_url


def test_fee_request_is_flagged():
    result = analyze("Pay a registration fee to get selected today", "internship")
    assert result["risk_assessment"] in {"Medium risk", "High risk"}
    assert "Advance payment requested" in result["signals"]


def test_scholarship_unusual_text_alone_needs_verification():
    result = analyze("Scholarship applications open now", "scholarship")
    assert result["risk_assessment"] == "Needs manual verification"
    assert "Scholarship verification" in result["official_sources"]


def test_url_is_parsed_without_network():
    result = analyze_url("http://192.0.2.5/login")
    assert result["valid"]
    assert result["host"] == "192.0.2.5"
    assert len(result["signals"]) >= 2


def test_url_without_enough_evidence_requires_manual_verification():
    result = analyze("", "url", "https://example.org")
    assert result["risk_assessment"] == "Needs manual verification"


def test_empty_input_rejected():
    with pytest.raises(ValueError):
        analyze("", "job", "")


def test_all_categories_are_accepted():
    for category in ("job", "internship", "work_from_home", "task", "government_scheme", "scholarship", "phishing"):
        assert analyze("Limited offer; verify independently", category)["category_key"] == category
