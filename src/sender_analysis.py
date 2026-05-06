import re
from typing import Dict, List

FREE_MAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
    "gmx.com",
    "mail.com",
}

PROMO_HINTS = (
    "offer", "discount", "promo", "sale", "winner", "prize", "claim", "reward",
    "bonus", "lottery", "exclusive", "limited", "cash", "gift", "urgent",
)

URGENT_HINTS = (
    "urgent", "immediately", "asap", "act now", "verify", "suspend",
    "locked", "security alert", "failure", "penalty", "expired", "deadline",
)

BRAND_KEYWORDS = {
    "google", "microsoft", "paypal", "apple", "amazon", "meta", "bank", "bdo", "bpi",
}

def _extract_sender_email(sender: str) -> str:
    s = (sender or "").strip().lower()
    m = re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", s)
    return m.group(0) if m else s

def score_sender_risk(sender: str, email_text: str) -> Dict[str, object]:
    reasons: List[str] = []
    score = 0.0

    sender_email = _extract_sender_email(sender)
    body = (email_text or "").lower()
    domain = sender_email.split("@")[-1] if "@" in sender_email else ""
    local = sender_email.split("@")[0] if "@" in sender_email else ""

    is_promo_like = any(k in body for k in PROMO_HINTS)
    is_urgent_like = any(k in body for k in URGENT_HINTS)

    if domain in FREE_MAIL_DOMAINS and is_promo_like:
        score += 35
        reasons.append("Free-mail sender used for promotional/reward content.")

    if ("noreply" in local or "no-reply" in local) and is_urgent_like:
        score += 30
        reasons.append("No-reply sender paired with urgent/manipulative message.")

    if domain:
        domain_core = domain.split(".")[0]
        mentions_brand = [b for b in BRAND_KEYWORDS if b in body]
        if mentions_brand and all(b not in domain_core for b in mentions_brand):
            score += 25
            reasons.append("Message intent references brands that don't match sender domain.")

    if not sender_email or "@" not in sender_email:
        score += 20
        reasons.append("Sender address missing/invalid.")

    if re.search(r"\d{4,}", local):
        score += 8
        reasons.append("Sender local-part has unusual long numeric pattern.")

    score = min(max(score, 0.0), 100.0)
    if score >= 65:
        risk = "high"
    elif score >= 35:
        risk = "medium"
    else:
        risk = "low"

    return {
        "score": round(score, 2),
        "risk": risk,
        "reasons": reasons,
        "sender_email": sender_email,
    }
