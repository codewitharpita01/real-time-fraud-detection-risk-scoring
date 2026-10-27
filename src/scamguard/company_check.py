from urllib.parse import urlsplit

FREE_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "proton.me"}


def check_company(company: str = "", recruiter_email: str = "", claimed_website: str = "") -> dict:
    signals = []
    host = ""
    if recruiter_email and "@" in recruiter_email:
        mail_host = recruiter_email.rsplit("@", 1)[1].lower().strip()
        if mail_host in FREE_EMAIL_DOMAINS:
            signals.append("Recruiter uses a free email domain; this alone does not establish fraud.")
        if claimed_website:
            candidate = claimed_website if "://" in claimed_website else f"https://{claimed_website}"
            try:
                host = (urlsplit(candidate).hostname or "").lower()
            except ValueError:
                pass
            if host and mail_host != host and not host.endswith("." + mail_host) and not mail_host.endswith("." + host):
                signals.append("Recruiter email domain differs from the supplied website domain; independently confirm the relationship.")
    if not company and not recruiter_email and not claimed_website:
        return {"status": "Unable to verify", "signals": ["Enter a company name, recruiter email, or claimed website."], "host": ""}
    return {
        "status": "Unable to verify",
        "signals": signals or ["No reliable company registry or live official-site check is configured."],
        "host": host,
        "next_step": "Find the organisation's official website independently and contact it using details published there. These local checks do not establish identity.",
    }
