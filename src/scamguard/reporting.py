import csv
from datetime import datetime, timezone
from html import escape
from io import BytesIO, StringIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def report_csv(result, content_type="text") -> bytes:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["analysis_date_utc", datetime.now(timezone.utc).isoformat()])
    writer.writerow(["content_type", content_type])
    writer.writerow(["category", result["category"]])
    writer.writerow(["assessment", result["risk_assessment"]])
    writer.writerow(["indicative_score", result["indicative_score"]])
    writer.writerow(["verification_status", result.get("verification_status", "Not verified")])
    writer.writerow(["signals"])
    for item in result["evidence"]:
        writer.writerow([item["signal"], item["phrase"]])
    writer.writerow(["recommendation", result["precautions"]])
    writer.writerow(["limitations", "Screening assistance only; not proof of fraud or authenticity."])
    return buffer.getvalue().encode("utf-8-sig")


def report_pdf(result, content_type="text") -> bytes:
    def pdf_text(value):
        value = str(value)
        return value if value.isascii() else "[non-English text; see UTF-8 CSV report]"

    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, title="ScamShield analysis report")
    styles = getSampleStyleSheet()
    elements = [Paragraph("ScamShield Analysis Report", styles["Title"]),
                Paragraph(f"Date (UTC): {datetime.now(timezone.utc).isoformat()}", styles["Normal"]),
                Paragraph(f"Content type: {escape(pdf_text(content_type))}", styles["Normal"]), Spacer(1, 10),
                Paragraph(f"Category: {escape(pdf_text(result['category']))}", styles["Heading2"]),
                Paragraph(f"Assessment: {escape(pdf_text(result['risk_assessment']))}", styles["Normal"]),
                Paragraph(f"Indicative score: {result['indicative_score']}/100 (not a probability)", styles["Normal"]),
                Paragraph(f"Verification: {escape(result.get('verification_status', 'Not verified'))}", styles["Normal"]),
                Paragraph("Evidence", styles["Heading2"])]
    if result["evidence"]:
        for item in result["evidence"]:
            elements.append(Paragraph(f"- {escape(pdf_text(item['signal']))}: \"{escape(pdf_text(item['phrase']))}\"", styles["BodyText"]))
    else:
        elements.append(Paragraph("No listed warning signals matched.", styles["BodyText"]))
    elements.extend([Paragraph("Recommended next step", styles["Heading2"]),
                     Paragraph(escape(pdf_text(result["precautions"])), styles["BodyText"]),
                     Spacer(1, 12), Paragraph("Limitations", styles["Heading2"]),
                     Paragraph("Screening assistance only. A low-risk result does not prove safety; a high-risk result does not prove fraud. Submitted text is omitted from this report by default.", styles["BodyText"])])
    doc.build(elements)
    return output.getvalue()
