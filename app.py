import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.scamguard.analyzer import analyze
from src.scamguard.company_check import check_company
from src.scamguard.config import CATEGORIES, MAX_TEXT_CHARS, OFFICIAL_SOURCES
from src.scamguard.database import add_feedback, delete_all, initialize, list_rows, save, summary
from src.scamguard.file_scanner import FileScanError, extract_image_text, extract_pdf_text
from src.scamguard.model import load_model, load_thresholds
from src.scamguard.reporting import report_csv, report_pdf

st.set_page_config(page_title="Fraud Detection for Indian Students", page_icon="🛡️", layout="wide")
initialize()
load_model()
load_thresholds()
st.markdown("""
<style>
:root { --ink: #172033; --muted: #68738A; --accent: #5B5CE2; --line: #E7EAF2; }
html, body, [class*="css"] { font-family: 'Segoe UI', Arial, sans-serif; }
.stApp { background: radial-gradient(ellipse at 80% -10%, rgba(112, 111, 240, .10), transparent 36%), #F6F7FB; }
h1, h2, h3 { font-family: 'Segoe UI', Arial, sans-serif !important; letter-spacing: -.035em; color: var(--ink); }
h1 { font-weight: 800 !important; }
section[data-testid="stSidebar"] { background: #11182C; border-right: 1px solid #29324B; }
section[data-testid="stSidebar"] * { color: #F4F6FF; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius: 10px; padding: 4px 8px; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: rgba(255,255,255,.08); }
[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid var(--line); border-radius: 16px; padding: 18px 20px; box-shadow: 0 5px 18px rgba(31,42,76,.045); }
[data-testid="stMetricLabel"] { color: var(--muted); font-size: .83rem; font-weight: 600; }
[data-testid="stMetricValue"] { color: var(--ink); font-family: 'Segoe UI', Arial, sans-serif; font-weight: 800; }
[data-testid="stVerticalBlockBorderWrapper"] { background: #FFFFFF; border: 1px solid var(--line); border-radius: 16px; box-shadow: 0 5px 18px rgba(31,42,76,.04); }
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input { background: #FFFFFF; border-radius: 12px; border-color: #DDE2ED; }
[data-testid="stTextArea"] textarea:focus, [data-testid="stTextInput"] input:focus { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(91,92,226,.12); }
.stButton > button, .stDownloadButton > button { min-height: 44px; border-radius: 11px; border: 1px solid #DDE2ED; font-weight: 700; transition: all .16s ease; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #6264EA, #4849C8); color: white; border: 0; box-shadow: 0 7px 16px rgba(82,83,211,.22); }
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); border-color: #8586EE; box-shadow: 0 7px 18px rgba(31,42,76,.10); }
.hero { padding: 38px 42px; border-radius: 24px; color: #fff; background: radial-gradient(circle at 85% 5%, rgba(255,255,255,.24), transparent 22%), linear-gradient(120deg, #242B55 0%, #4B4DC2 57%, #7775F1 100%); box-shadow: 0 18px 42px rgba(47,52,130,.20); margin: 8px 0 26px; }
.hero-kicker { display: inline-block; font-size: .76rem; letter-spacing: .11em; text-transform: uppercase; color: #E1E3FF; font-weight: 700; margin-bottom: 12px; }
.hero h1 { color: white !important; font-size: clamp(2rem, 4vw, 3rem); line-height: 1.08; margin: 0 0 12px; }
.hero p { max-width: 760px; color: #ECECFF; font-size: 1.03rem; line-height: 1.6; margin: 0; }
.hero-pill { display: inline-block; margin: 20px 8px 0 0; padding: 7px 11px; border: 1px solid rgba(255,255,255,.28); background: rgba(255,255,255,.10); border-radius: 999px; color: #F7F7FF; font-size: .78rem; }
.section-note { color: var(--muted); margin-top: -8px; margin-bottom: 20px; }
div[data-testid="stAlert"] { border-radius: 13px; }
@media (max-width: 700px) { .hero { padding: 26px 22px; border-radius: 18px; } [data-testid="stMetric"] { padding: 13px; } }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ ScamShield")
    nav_pages = ["Home", "Text scam checker", "Screenshot and PDF scanner", "Website and URL checker", "Government & scholarship", "Company and recruiter", "Analysis history", "Analytics dashboard", "About, privacy & help"]
    page = st.radio("Navigate", nav_pages, key="page_nav")
    st.caption("Local screening assistance. Not a guarantee of fraud or authenticity.")


def navigate_to(target):
    st.session_state["page_nav"] = target

stats = summary()


def show_result(result, content_type):
    st.divider()
    st.subheader("Analysis result")
    icon = {"Low risk": "🟢", "Medium risk": "🟠", "High risk": "🔴", "Needs manual verification": "🔎"}.get(result["risk_assessment"], "ℹ️")
    a, b, c = st.columns(3)
    a.metric("Assessment", f"{icon} {result['risk_assessment']}")
    b.metric("Indicative score", f"{result['indicative_score']} / 100")
    c.write(result["score_label"])
    st.caption(f"Category: {result['category']} · Verification: {result.get('verification_status', 'Not verified')}")
    st.write(result["explanation"])
    if result.get("optional_model_suggestion"):
        suggestion = result["optional_model_suggestion"]
        model_score = "" if suggestion["scam_score"] is None else f" · uncalibrated model score {suggestion['scam_score']:.0f}/100"
        st.info(f"Text model: **{suggestion['label']}**{model_score}. This is one component of the hybrid score, not a calibrated probability.")
    left, right = st.columns(2)
    with left:
        st.markdown("**Warning indicators and matched evidence**")
        if result["evidence"]:
            for item in result["evidence"]:
                st.markdown(f"- **{item['signal']}** — `{item['phrase']}`")
        else:
            st.write("No listed indicator matched.")
    with right:
        st.markdown("**Student safety guidance**")
        for step in result["verification_steps"]:
            st.markdown(f"- {step}")
    if result.get("url_analysis"):
        st.caption(f"Parsed host: {result['url_analysis']['host'] or 'not available'}. No website was visited.")
    if result.get("official_sources"):
        st.markdown("**Official reference links (not live verification of this claim)**")
        for name, link in result["official_sources"].items():
            st.markdown(f"- [{name}]({link})")
    csv_bytes = report_csv(result, content_type)
    pdf_bytes = report_pdf(result, content_type)
    d1, d2 = st.columns(2)
    d1.download_button("Download redacted CSV report", csv_bytes, "scamshield-report.csv", "text/csv")
    d2.download_button("Download redacted PDF report", pdf_bytes, "scamshield-report.pdf", "application/pdf")
    if result.get("history_id"):
        st.markdown("**Was this result useful?**")
        f1, f2 = st.columns(2)
        if f1.button("Yes, useful", key="feedback_yes"):
            add_feedback(result["history_id"], True)
            st.success("Thanks. Feedback is stored separately and is not used as a verified label or to retrain the model.")
        if f2.button("No / seems incorrect", key="feedback_no"):
            add_feedback(result["history_id"], False)
            st.info("Thanks. Feedback is stored separately and is not used as a verified label or to retrain the model.")


def run_analysis(text, category, url, content_type, consent):
    try:
        result = analyze(text=text, category=category, url=url)
        if consent:
            result["history_id"] = save(result, content_type)
        st.session_state["last_result"] = result
        st.session_state["last_content_type"] = content_type
        st.session_state["last_result_page"] = page
    except ValueError as exc:
        st.error(str(exc))


def consent_control(key="consent_history"):
    return st.checkbox("Save a minimal summary in local history (category, score, warning signals only; no submitted text or files)", key=key)


if page == "Home":
    st.markdown("""
    <div class="hero">
      <div class="hero-kicker">Student safety toolkit</div>
      <h1>Spot the warning signs<br>before you trust the offer.</h1>
      <p>Screen job, internship, task, scholarship, government-scheme, phishing, and website claims with clear evidence and practical next steps.</p>
      <span class="hero-pill">English + Hindi/Hinglish signals</span>
      <span class="hero-pill">Private, local-first checks</span>
      <span class="hero-pill">No links opened</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### Your safety overview")
    st.markdown('<div class="section-note">Saved counts include only analyses you chose to keep.</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Saved analyses", stats["total"])
    c2.metric("High-risk results", stats["by_assessment"].get("High risk", 0))
    c3.metric("Needs manual verification", stats["by_assessment"].get("Needs manual verification", 0))
    st.subheader("Choose a checker")
    descriptions = [
        ("01", "Text scam checker", "Analyze job, internship, work-from-home, task, or phishing text."),
        ("02", "Screenshot and PDF scanner", "Extract text from image and PDF notices using local OCR."),
        ("03", "Website and URL checker", "Inspect URL structure without opening the submitted site."),
        ("04", "Government & scholarship", "Review benefit claims and find official reference portals."),
        ("05", "Company and recruiter", "Check contact and domain consistency; no identity is asserted."),
        ("06", "Analytics dashboard", "View distributions from consented local analyses."),
    ]
    for start in (0, 3):
        cols = st.columns(3)
        for col, (number, title, desc) in zip(cols, descriptions[start:start + 3]):
            with col:
                with st.container(border=True):
                    st.caption(f"MODULE {number}")
                    st.button(title, key=f"open_{number}", on_click=navigate_to, args=(title,), use_container_width=True)
                    st.caption(desc)
    st.info("Never share passwords, OTPs, bank credentials, or unnecessary identity documents. A low-risk result does not prove safety.")

elif page == "Text scam checker":
    st.title("Text Scam Checker")
    category = st.selectbox("Detection category", list(CATEGORIES), format_func=lambda key: CATEGORIES[key], index=0)
    text = st.text_area("Paste a message or advertisement", max_chars=MAX_TEXT_CHARS, height=220, placeholder="Example: Work from home job hai, daily ₹3000 kamao. Registration ke liye pehle payment karo.")
    consent = consent_control()
    if st.button("Analyze text", type="primary"):
        run_analysis(text, category, "", "text", consent)
    if st.session_state.get("last_result_page") == page:
        show_result(st.session_state["last_result"], st.session_state.get("last_content_type", "text"))

elif page == "Screenshot and PDF scanner":
    st.title("Screenshot and PDF Scanner")
    st.caption("Images and PDFs are processed in memory for text extraction. Uploaded files are not saved. Limit: 15 MB and 20 PDF pages.")
    category = st.selectbox("What does the document concern?", [key for key in CATEGORIES if key not in ("auto", "url")], format_func=lambda key: CATEGORIES[key])
    upload_kind = st.radio("File type", ["Image (PNG/JPG/JPEG)", "PDF"], horizontal=True)
    upload = st.file_uploader("Choose a screenshot or PDF", type=["png", "jpg", "jpeg"] if upload_kind.startswith("Image") else ["pdf"], max_upload_size=15)
    if upload and st.button("Extract text"):
        try:
            raw = upload.getvalue()
            extracted = extract_image_text(raw, upload.name) if upload_kind.startswith("Image") else extract_pdf_text(raw, upload.name)
            st.session_state["ocr_text"] = extracted[:MAX_TEXT_CHARS]
            st.success("Text extracted. Review and correct it before analysis.")
        except FileScanError as exc:
            st.error(str(exc))
    corrected = st.text_area("Review or edit extracted text", value=st.session_state.get("ocr_text", ""), max_chars=MAX_TEXT_CHARS, height=220, key="corrected_ocr_text")
    consent = consent_control("consent_upload_history")
    if st.button("Analyze extracted text", type="primary"):
        run_analysis(corrected, category, "", "image OCR" if upload_kind.startswith("Image") else "PDF text", consent)
    if st.session_state.get("last_result_page") == page:
        show_result(st.session_state["last_result"], st.session_state.get("last_content_type", "document"))

elif page == "Website and URL checker":
    st.title("Website and URL Checker")
    st.warning("The checker never opens a submitted URL or requests its content. HTTPS does not prove that a website is legitimate.")
    url = st.text_input("URL to inspect", max_chars=2_048, placeholder="https://example.org/path")
    text = st.text_area("Optional message containing this URL", max_chars=MAX_TEXT_CHARS, height=130)
    consent = consent_control("consent_url_history")
    if st.button("Inspect URL", type="primary"):
        run_analysis(text, "url", url, "url", consent)
    if st.session_state.get("last_result_page") == page:
        show_result(st.session_state["last_result"], st.session_state.get("last_content_type", "url"))

elif page == "Government & scholarship":
    st.title("Government Scheme and Scholarship Checker")
    category = st.radio("Claim type", ["government_scheme", "scholarship"], format_func=lambda key: CATEGORIES[key], horizontal=True)
    st.caption("This prototype does not query live government records. Links below are official starting points, not verification of the specific claim.")
    text = st.text_area("Paste the full announcement or message", max_chars=MAX_TEXT_CHARS, height=210)
    consent = consent_control("consent_official_history")
    if st.button("Review claim", type="primary"):
        run_analysis(text, category, "", "official claim text", consent)
    st.markdown("**Configured official references**")
    for name, link in OFFICIAL_SOURCES.items():
        st.markdown(f"- [{name}]({link})")
    if st.session_state.get("last_result_page") == page:
        show_result(st.session_state["last_result"], st.session_state.get("last_content_type", "text"))

elif page == "Company and recruiter":
    st.title("Company and Recruiter Checks")
    st.caption("Local consistency checks only. No live company registry, DNS, or website verification is configured.")
    company = st.text_input("Company or institution name")
    email = st.text_input("Recruiter email (optional)")
    website = st.text_input("Claimed company website (optional)")
    if st.button("Check details"):
        check = check_company(company, email, website)
        st.subheader(check["status"])
        for signal in check["signals"]:
            st.markdown(f"- {signal}")
        if check.get("host"):
            st.caption(f"Website host entered: {check['host']}")
        st.write(check.get("next_step", ""))

elif page == "Analysis history":
    st.title("Analysis History")
    st.caption("History contains only category, time, score, warning indicators, and verification status. It does not retain submitted message text or uploaded files.")
    query = st.text_input("Search category or warning indicator")
    assessment = st.selectbox("Filter risk level", ["All", "Low risk", "Medium risk", "High risk", "Needs manual verification"])
    rows = list_rows(query, assessment)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No saved analyses match. Saving is optional and off by default.")
    confirm = st.checkbox("I understand this deletes all locally saved summaries")
    if st.button("Delete all history", disabled=not confirm):
        delete_all()
        st.success("Local analysis history and associated feedback deleted.")
        st.rerun()

elif page == "Analytics dashboard":
    st.title("Analytics Dashboard")
    st.caption("Charts show only consented, real local application history. No demo activity is mixed in.")
    a, b, c = st.columns(3)
    a.metric("Analyses", stats["total"])
    b.metric("Feedback entries", stats["feedback_count"])
    c.metric("Feedback marked useful", stats["feedback_helpful"])
    if stats["total"]:
        import plotly.express as px
        left, right = st.columns(2)
        with left:
            st.plotly_chart(px.bar(pd.DataFrame(stats["by_category"].items(), columns=["Category", "Count"]), x="Category", y="Count", title="Analyses by category"), use_container_width=True)
        with right:
            st.plotly_chart(px.pie(pd.DataFrame(stats["by_assessment"].items(), columns=["Risk level", "Count"]), names="Risk level", values="Count", title="Risk-level distribution"), use_container_width=True)
        if stats["by_signal"]:
            st.plotly_chart(px.bar(pd.DataFrame(stats["by_signal"].items(), columns=["Warning signal", "Count"]).sort_values("Count", ascending=False), x="Warning signal", y="Count", title="Common warning signals"), use_container_width=True)
    else:
        st.info("No consented analyses yet. Complete an analysis and opt into saving its minimal summary.")
    metrics_path = Path("artifacts/metrics.json")
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        st.subheader(f"Test metrics: {metrics.get('dataset_status', 'documented dataset')} (not live activity)")
        st.json({"test_text_classification_report": metrics.get("test_text_classification_report"), "text_confusion_matrix_rows_scam_legitimate_ambiguous": metrics.get("test_confusion_matrix_labels_scam_legitimate_ambiguous"), "hybrid_risk_confusion_matrix_rows_low_medium_high_manual": metrics.get("test_risk_confusion_matrix_labels_low_medium_high_manual"), "false_positive_negative_summary": metrics.get("false_positive_negative_summary"), "limitations": metrics.get("limitations")})
        st.caption("Text-model false positives/negatives count scam vs non-scam labels. Hybrid false positives/negatives count High Risk results against scam labels. These are synthetic benchmark results only.")
    else:
        st.info("No trained-model evaluation metrics are available. Train with a documented labeled dataset to create artifacts/metrics.json. No results are fabricated.")

else:
    st.title("About, Privacy & Help")
    st.markdown("""
### What this tool does
It performs immediate local hybrid screening: contextual rules plus a cached TF-IDF model when a model artifact exists, and offline URL structure checks. Selected payment and credential phrases are supported in Hindi and Hinglish as well as English.

### Limitations
This is not continuous monitoring and does not watch WhatsApp, email, browsers, or the internet. It does not verify company identity, visit URLs, query DNS/reputation, or compare government claims with live records. Government and scholarship results remain **Not verified**. Local pattern checks can miss scams and can flag legitimate text. Current bundled model metrics use synthetic examples only, not naturally occurring messages.

### Privacy
Analysis history is off by default. If you opt in, only timestamp, category, risk score, warning labels, content type, and verification status are saved in local SQLite. Submitted text, URLs, uploaded files, and feedback comments are not stored. Feedback is separate from ground truth and never retrains the model. You can delete all history.

### Upload and local setup
Image/PDF uploads are processed in memory, limited to 15 MB and 20 PDF pages. Install Tesseract OCR separately and add it to PATH for OCR; extraction errors fall back to manual text entry. Setup commands and dataset sources are in the project README.
""")
