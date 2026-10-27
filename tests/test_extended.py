import sqlite3
from pathlib import Path

import pytest
import pymupdf

from src.scamguard import database
from src.scamguard.analyzer import analyze
from src.scamguard.company_check import check_company
from src.scamguard.file_scanner import FileScanError, extract_image_text, extract_pdf_text
from src.scamguard.reporting import report_csv, report_pdf
from src.scamguard.url_checks import analyze_url


def test_hinglish_fee_and_high_earning_signals():
    result = analyze("Work from home job hai, daily ₹3000 kamao. Registration ke liye pehle payment karo.", "auto")
    assert result["category_key"] == "work_from_home"
    assert result["risk_assessment"] == "High risk"
    assert "Advance payment requested" in result["signals"]
    assert "daily ₹3000" in result["evidence"][0]["phrase"] or any("daily ₹3000" in row["phrase"] for row in result["evidence"])


def test_devanagari_fee_request_is_detected():
    result = analyze("पंजीकरण शुल्क जमा करें", "internship")
    assert "Advance payment requested" in result["signals"]


def test_harmless_urgent_and_free_words_do_not_raise_rule_score():
    result = analyze("Free tea at the student club. Urgent reminder: room closes at 6 PM.", "job")
    assert result["detected_indicators"] == []
    assert result["risk_assessment"] == "Low risk"
    assert result["indicative_score"] < 30


@pytest.mark.parametrize("category,text,signal", [
    ("work_from_home", "Work from home. Pay a deposit before starting.", "Deposit, upgrade, or withdrawal payment mentioned"),
    ("task", "Pay a withdrawal fee to release task earnings.", "Deposit, upgrade, or withdrawal payment mentioned"),
    ("phishing", "Send your OTP immediately to verify your account.", "Password, OTP, or credential request"),
    ("government_scheme", "Government scheme subsidy has an application fee.", "Advance payment requested"),
])
def test_category_signals_remain_advisory(category, text, signal):
    result = analyze(text, category)
    assert signal in result["signals"]
    if category == "government_scheme":
        assert result["verification_status"] == "Not verified"


def test_shortener_is_flagged_without_visiting_it():
    result = analyze_url("https://bit.ly/example")
    assert result["valid"]
    assert any("shortening" in signal for signal in result["signals"])


def test_invalid_and_oversized_uploads_are_rejected():
    with pytest.raises(FileScanError, match="Unsupported image"):
        extract_image_text(b"not-an-image", "notice.gif")
    with pytest.raises(FileScanError, match="valid PDF"):
        extract_pdf_text(b"not-a-pdf", "notice.pdf")
    with pytest.raises(FileScanError, match="15 MB"):
        extract_image_text(b"x" * (15 * 1024 * 1024 + 1), "notice.png")


def test_pdf_text_extraction_and_page_limit():
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Job offer for a software intern. Verify independently.")
    data = document.tobytes()
    document.close()
    assert "software intern" in extract_pdf_text(data, "notice.pdf")

    large_document = pymupdf.open()
    for _ in range(21):
        large_document.new_page()
    large_data = large_document.tobytes()
    large_document.close()
    with pytest.raises(FileScanError, match="20-page limit"):
        extract_pdf_text(large_data, "long.pdf")


def test_ocr_failure_is_a_recoverable_message(monkeypatch):
    from io import BytesIO
    from PIL import Image
    import src.scamguard.file_scanner as scanner

    image_bytes = BytesIO()
    Image.new("RGB", (40, 20), "white").save(image_bytes, format="PNG")
    monkeypatch.setattr(scanner, "_ocr", lambda image: (_ for _ in ()).throw(FileScanError("OCR could not read this image.")))
    with pytest.raises(FileScanError, match="OCR could not read"):
        extract_image_text(image_bytes.getvalue(), "notice.png")


def test_report_outputs_are_created_without_source_content():
    result = analyze("पंजीकरण शुल्क जमा करें", "scholarship")
    csv_content = report_csv(result).decode("utf-8-sig")
    pdf_content = report_pdf(result)
    assert "पंजीकरण शुल्क जमा करें" not in csv_content
    assert "indicative_score" in csv_content
    assert pdf_content.startswith(b"%PDF")


def test_history_saves_summary_only_with_opt_in(monkeypatch):
    test_db = Path(__file__).with_name("_test_history.sqlite")
    if test_db.exists():
        test_db.unlink()
    monkeypatch.setattr(database, "DB_PATH", test_db)
    try:
        database.initialize()
        result = analyze("Employer text with registration fee", "job")
        analysis_id = database.save(result, "text")
        database.add_feedback(analysis_id, True)
        rows = database.list_rows()
        assert rows[0]["signals_json"]
        assert "text" not in rows[0]
        assert database.summary()["feedback_helpful"] == 1
        conn = sqlite3.connect(database.DB_PATH)
        try:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(analyses)")}
        finally:
            conn.close()
        assert not {"text", "url", "result_json"} & columns
    finally:
        if test_db.exists():
            test_db.unlink()


def test_recruiter_verification_does_not_make_identity_claim():
    result = check_company("Example Company", "person@gmail.com", "https://example.org")
    assert result["status"] == "Unable to verify"
    assert any("free email" in signal for signal in result["signals"])
