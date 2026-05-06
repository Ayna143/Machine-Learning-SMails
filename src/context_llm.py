import json
import os
import re
from typing import Any, Dict

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TIMEOUT_SECONDS = float(os.environ.get("GEMINI_TIMEOUT_SECONDS", "20"))

SYSTEM_PROMPT = (
    "You are a spam detection expert. Analyze the following email and "
    "determine if it is spam based on INTENT, urgency, deception, "
    "manipulation, and phishing signals — NOT based on specific keywords. "
    "Even if the email avoids typical spam words, judge it by its "
    "overall meaning and purpose. Return ONLY a JSON response."
)

def _extract_json_blob(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t).strip()
        t = re.sub(r"\n?```$", "", t).strip()
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in Gemini response")
    return t[start : end + 1]

def _normalize_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    verdict = str(raw.get("verdict", "")).strip().lower()
    if verdict in ("not spam", "legit", "legitimate"):
        verdict = "ham"
    if verdict not in ("spam", "ham"):
        raise ValueError(f"Invalid verdict '{verdict}'")

    conf = raw.get("confidence", 50)
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        conf = 50.0
    conf = min(max(conf, 0.0), 100.0)

    reason = str(raw.get("reason", "")).strip()
    if not reason:
        reason = "No explanation returned by Gemini."

    return {
        "verdict": verdict,
        "confidence": conf,
        "reason": reason,
        "ok": True,
        "error": None,
    }

def analyze_with_gemini(email_text: str, sender: str) -> Dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {
            "verdict": "ham",
            "confidence": 50.0,
            "reason": "Gemini not configured.",
            "ok": False,
            "error": "Missing GEMINI_API_KEY",
        }

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Sender: {sender}\n"
            f"Email:\n{email_text}\n\n"
            "Return JSON only with keys: verdict, confidence, reason."
        )
        resp = model.generate_content(
            prompt,
            request_options={"timeout": GEMINI_TIMEOUT_SECONDS},
        )
        blob = _extract_json_blob(getattr(resp, "text", ""))
        parsed = json.loads(blob)
        return _normalize_result(parsed)
    except Exception as e:
        return {
            "verdict": "ham",
            "confidence": 50.0,
            "reason": "Gemini unavailable; used ML+sender fallback.",
            "ok": False,
            "error": str(e),
        }
