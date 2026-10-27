import re

from .text import normalize_text

# Rules require a contextual demand, not a mention of jobs, money, or scholarships.
RULES = [
    {
        "id": "upfront_recruitment_fee", "indicator": "Upfront recruitment or internship fee demanded",
        "weight": 70,
        "pattern": re.compile(
            r"(?:pay|send|transfer|deposit|submit|requires?|must pay|payment of).{0,45}(?:registration|application|joining|processing|training|certificate|security).{0,18}(?:fee|charge|deposit)"
            r"|(?:demands?|asks? (?:the )?(?:applicant|candidate)s? to pay).{0,40}(?:registration|application|joining|processing|training|certificate|security|internship).{0,18}(?:fee|charge|deposit)"
            r"|(?:asks? (?:the )?(?:applicant|candidate)s? to pay|pay).{0,45}(?:processing|verification|registration|application|joining|training).{0,18}(?:fee|charge|deposit)"
            r"|(?:registration|application|joining|processing|training|certificate|security|verification) (?:fee|charge).{0,35}(?:required|mandatory|to secure|before joining|before interview|to confirm|reserve|before receiving|pehle pay|dena zaroori)"
            r"|(?:internship|job|placement).{0,55}(?:deposit|fee|charge).{0,30}(?:bhejne|dena|maang|manga|to pay|must)"
            r"|(?:internship|placement|job).{0,90}(?:demands?|asks?|requires?).{0,55}(?:refundable )?(?:deposit|fee|charge)"
            r"|(?:demands?|asks?|requires?).{0,45}(?:refundable )?(?:internship|job).{0,35}(?:deposit|fee|charge)"
            r"|(?:deposit|fee|charge).{0,35}(?:bhejne|dena|maang|manga)"
            r"|(?:government scheme|subsidy|scholarship|grant).{0,55}(?:application|processing|registration) fee"
            r"|registration ke liye pehle payment|pehle (?:paisa|paise) (?:do|karo)|(?:pahle|pehle) (?:shulk|fees?) jama"
            r"|(?:\u0936\u0941\u0932\u094d\u0915|\u092b\u0940\u0938|\u092d\u0941\u0917\u0924\u093e\u0928).{0,24}(?:\u091c\u092e\u093e|\u092e\u093e\u0902\u0917|\u0926\u0947|\u0915\u0930\u0947\u0902)"
            r"|(?:\u0907\u0902\u091f\u0930\u094d\u0928\u0936\u093f\u092a|\u0928\u094c\u0915\u0930\u0940|\u092d\u0930\u094d\u0924\u0940).{0,70}(?:\u091c\u092e\u093e \u0930\u093e\u0936\u093f|\u0921\u093f\u092a\u0949\u091c\u093f\u091f|\u0936\u0941\u0932\u094d\u0915|\u092b\u0940\u0938).{0,25}(?:\u092e\u093e\u0902\u0917\u093e|\u092e\u093e\u0902\u0917\u0940|\u0926\u0947\u0928\u0947|\u091c\u092e\u093e \u0915\u0930\u0947\u0902)"
            r"|\u092a\u0939\u0932\u0947.{0,16}\u092a\u0902\u091c\u0940\u0915\u0930\u0923 \u0936\u0941\u0932\u094d\u0915.{0,20}(?:\u091c\u092e\u093e|\u0926\u0947\u0902|\u0915\u0930\u0947\u0902)"
            r"|\u0928\u094c\u0915\u0930\u0940.{0,35}(?:\u0936\u0941\u0932\u094d\u0915|\u092b\u0940\u0938).{0,18}(?:\u091c\u092e\u093e|\u092d\u0941\u0917\u0924\u093e\u0928)", re.I),
        "strong": True,
    },
    {
        "id": "task_deposit", "indicator": "Deposit or recharge required to unlock tasks or withdrawals",
        "weight": 75,
        "pattern": re.compile(
            r"(?:deposit|recharge|top[- ]?up|pay).{0,50}(?:unlock|release|withdraw|activate).{0,35}(?:task|earning|balance|account|assignment|rating)"
            r"|(?:withdrawal|withdraw|release earnings).{0,35}(?:fee|deposit|recharge|top[- ]?up)"
            r"|(?:work from home|job|internship|role).{0,45}(?:pay|deposit|fee).{0,35}(?:before starting|to start|before joining)"
            r"|(?:task|tasks|rating|assignment).{0,45}(?:activate|unlock|start).{0,45}(?:wallet|deposit|recharge|top[- ]?up|paisa|payment)"
            r"|task (?:ke liye|unlock karne ke liye).{0,25}(?:paisa|payment|recharge)"
            r"|\u091f\u093e\u0938\u094d\u0915.{0,30}(?:\u0916\u094b\u0932\u0928\u0947|\u0928\u093f\u0915\u093e\u0932\u0928\u0947).{0,20}(?:\u091c\u092e\u093e|\u092d\u0941\u0917\u0924\u093e\u0928)"
            r"|\u091f\u093e\u0938\u094d\u0915.{0,55}(?:\u0935\u0949\u0932\u0947\u091f|\u091c\u092e\u093e \u0930\u093e\u0936\u093f).{0,35}(?:\u092a\u0948\u0938\u0947 \u0921\u093e\u0932\u094b|\u092a\u0948\u0938\u0947 \u0921\u093e\u0932\u0928\u0947|\u092d\u0941\u0917\u0924\u093e\u0928|\u091c\u092e\u093e \u0915\u0930\u094b|\u0915\u0939\u093e)", re.I),
        "strong": True,
    },
    {
        "id": "credential_theft", "indicator": "Password, OTP, or financial credential requested",
        "weight": 78,
        "pattern": re.compile(
            r"(?:share|send|enter|tell|provide|confirm|verify|request|asks? for|demands?).{0,30}(?:your )?(?:password|otp|one[- ]time password|pin|cvv|card details|card number|bank login)"
            r"|(?:otp|one[- ]time password|one[- ]time code).{0,25}(?:batao|bhejo|share karo|maang(?:ta|te)?)"
            r"|(?:otp|one[- ]time code|card details).{0,25}(?:\u092e\u093e\u0902\u0917|\u092e\u093e\u0902\u0917\u0924\u093e|\u092e\u093e\u0902\u0917\u0924\u0947)"
            r"|(?:\u0915\u093e\u0930\u094d\u0921 \u0935\u093f\u0935\u0930\u0923|\u0935\u0928-\u091f\u093e\u0907\u092e \u0915\u094b\u0921|\u0913\u091f\u0940\u092a\u0940).{0,35}\u092e\u093e\u0902\u0917\u0924\u093e"
            r"|\u0913\u091f\u0940\u092a\u0940.{0,18}(?:\u092c\u0924\u093e\u090f\u0902|\u092d\u0947\u091c\u0947\u0902|\u0938\u093e\u091d\u093e)"
            r"|\u092a\u093e\u0938\u0935\u0930\u094d\u0921.{0,18}(?:\u092d\u0947\u091c\u0947\u0902|\u092c\u0924\u093e\u090f\u0902)", re.I),
        "strong": True,
    },
    {
        "id": "benefit_payment", "indicator": "Government or scholarship benefit tied to a personal payment channel",
        "weight": 70,
        "pattern": re.compile(
            r"(?:scholarship|government scheme|subsidy|grant|benefit|\u091b\u093e\u0924\u094d\u0930\u0935\u0943\u0924\u094d\u0924\u093f|\u0938\u0930\u0915\u093e\u0930\u0940 \u092f\u094b\u091c\u0928\u093e).{0,100}(?:pay|fee|upi|wallet|personal account|private number|processing charge|personal wallet)"
            r"|(?:upi|wallet|personal account|private number|personal wallet).{0,70}(?:scholarship|government scheme|subsidy|grant|benefit|\u091b\u093e\u0924\u094d\u0930\u0935\u0943\u0924\u094d\u0924\u093f|\u0932\u093e\u092d).{0,55}(?:fee|charge|payment|\u0936\u0941\u0932\u094d\u0915|\u092d\u0941\u0917\u0924\u093e\u0928)"
            r"|(?:\u0928\u093f\u091c\u0940 \u0928\u0902\u092c\u0930|\u0928\u093f\u091c\u0940 \u0935\u0949\u0932\u0947\u091f).{0,70}(?:\u0936\u0941\u0932\u094d\u0915|\u092d\u0941\u0917\u0924\u093e\u0928).{0,60}(?:\u0932\u093e\u092d|\u0905\u0928\u0941\u0926\u093e\u0928)"
            r"|(?:selection is certain|selection is guaranteed|guaranteed (?:scholarship|award)).{0,70}(?:asks?|requests?|payment|pay).{0,55}(?:release|grant|award|scholarship)", re.I),
        "strong": True,
    },
    {
        "id": "benefit_release_fee", "indicator": "Payment demanded to release a scholarship or benefit",
        "weight": 60,
        "pattern": re.compile(
            r"(?:scholarship|grant|award|subsidy|benefit|\u091b\u093e\u0924\u094d\u0930\u0935\u0943\u0924\u094d\u0924\u093f|\u0905\u0928\u0941\u0926\u093e\u0928|\u0932\u093e\u092d).{0,90}(?:asks?|requests?|pay|payment|fee|charge).{0,60}(?:release|issue|transfer|\u091c\u093e\u0930\u0940|\u091c\u093e\u0930\u0940 \u0915\u0930\u0928\u0947)"
            r"|(?:\u0905\u0928\u0941\u0926\u093e\u0928|\u0932\u093e\u092d|\u091b\u093e\u0924\u094d\u0930\u0935\u0943\u0924\u094d\u0924\u093f).{0,75}(?:\u0936\u0941\u0932\u094d\u0915|\u092d\u0941\u0917\u0924\u093e\u0928).{0,55}(?:\u091c\u093e\u0930\u0940|\u0926\u0947\u0928\u0947|\u0915\u0930\u0928\u0947)", re.I),
        "strong": True,
    },
    {
        "id": "high_earnings", "indicator": "Unusually high or guaranteed earnings promised",
        "weight": 24,
        "pattern": re.compile(
            r"(?:guaranteed|fixed|assured).{0,25}(?:income|earning|profit|return)"
            r"|earn\s*(?:rs\.?|inr|\u20b9)?\s*[1-9]\d{3,}.{0,12}(?:daily|per day|a day|every day)"
            r"|(?:daily|per day|roz|rozana|\u0930\u094b\u091c\u093e\u0928\u093e|\u092a\u094d\u0930\u0924\u093f\u0926\u093f\u0928).{0,18}(?:\u20b9|rs\.?\s*)?[1-9]\d{3,}", re.I),
        "strong": False,
    },
    {
        "id": "pressure", "indicator": "Pressure to act immediately",
        "weight": 12,
        "pattern": re.compile(r"\b(act now|immediately|last chance|today only|limited slots|offer expires today)\b|abhi (?:apply|join|karo)|aaj hi (?:apply|join)|\u0924\u0941\u0930\u0902\u0924|\u0906\u091c \u0939\u0940 \u0906\u0935\u0947\u0926\u0928", re.I),
        "strong": False,
    },
    {
        "id": "suspicious_link", "indicator": "Suspicious link or lookalike domain present",
        "weight": 28,
        "pattern": re.compile(r"https?://[^\s]*(?:bit\.ly|tinyurl|t\.co|xn--|login[-.]|verify[-.])[^\s]*", re.I),
        "strong": False,
    },
]

PREVENTION_CONTEXT = re.compile(
    r"\b(don't|do not|never|avoid|beware|warning against|scam prevention|not pay|should not|report this scam|fake offer)\b"
    r"|scam se bache|paise mat do|payment mat karo|\u092e\u0924 \u0926\u0947\u0902|\u0928 \u0926\u0947\u0902|\u0938\u0947 \u092c\u091a\u0947\u0902|\u0927\u094b\u0916\u093e\u0927\u0921\u093c\u0940 \u0938\u0947 \u0938\u093e\u0935\u0927\u093e\u0928", re.I)


def _is_prevention_context(text: str, start: int, end: int) -> bool:
    left = text[max(0, start - 90):start]
    right = text[end:min(len(text), end + 140)]
    sentence_left = re.split(r"[.!?\n;]", left)[-1]
    return bool(PREVENTION_CONTEXT.search(sentence_left) or PREVENTION_CONTEXT.search(right))


def detect_indicators(text: str) -> list[dict]:
    clean = normalize_text(text)
    found = []
    for rule in RULES:
        for match in rule["pattern"].finditer(clean):
            if _is_prevention_context(clean, match.start(), match.end()):
                continue
            found.append({
                "id": rule["id"], "indicator": rule["indicator"],
                "weight": rule["weight"], "strong": rule["strong"],
                "evidence": match.group(0),
            })
            break
    return found


def rule_score(indicators: list[dict]) -> int:
    return min(100, sum(item["weight"] for item in indicators))


def has_strong_evidence(indicators: list[dict]) -> bool:
    strong_count = sum(bool(item["strong"]) for item in indicators)
    return strong_count >= 1 and rule_score(indicators) >= 60 or strong_count >= 2
