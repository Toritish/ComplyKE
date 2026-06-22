"""
sms/sender.py
Formats the compliance report and delivers it via Africa's Talking SMS API.
"""

import os
import africastalking
from ai.explainer import simplify_for_sms

# Initialise Africa's Talking SDK once at import time
_AT_USERNAME = os.environ.get("AT_USERNAME", "sandbox")
_AT_API_KEY = os.environ.get("AT_API_KEY", "")

africastalking.initialize(_AT_USERNAME, _AT_API_KEY)
_sms = africastalking.SMS


RISK_LABELS = {
    "low":    "🟢 LOW   – Minor gaps. Review obligations below.",
    "medium": "🟡 MEDIUM – Action needed. See obligations below.",
    "high":   "🔴 HIGH  – Urgent! Address these obligations now.",
}

MAX_SMS_CHARS = 459  # 3 SMS pages @ 153 chars each (concatenated)


def format_report(report: dict) -> str:
    """
    Convert a compliance report dict into an SMS-safe string.
    Truncates gracefully if too long.
    """
    biz_label = report["business_label"]
    risk = report["risk"]
    obligations = report["obligations"]

    risk_line = RISK_LABELS.get(risk["level"], risk["level"].upper())

    lines = [
        f"=== Micro-GRC Report ===",
        f"Business: {biz_label}",
        f"Risk: {risk_line}",
        "",
        "YOUR OBLIGATIONS:",
    ]

    for i, obl in enumerate(obligations, 1):
        lines.append(f"{i}. {obl['title']}")
        lines.append(f"   {obl['description'][:80]}")
        lines.append(f"   ACTION: {obl['action'][:80]}")
        lines.append("")

    lines.append("Dial *384*GRC# anytime to re-check.")
    lines.append("micro-grc.africa")

    full_text = "\n".join(lines)

    # Truncate gracefully if over limit
    if len(full_text) > MAX_SMS_CHARS:
        full_text = full_text[:MAX_SMS_CHARS - 3] + "..."

    return full_text


def send_sms_report(phone_number: str, report: dict, language: str = "en") -> bool:
    """
    Format and send the compliance report SMS.
    Uses AI simplification if CLAUDE_API_KEY is set, else falls back to
    the plain structured format.
    Returns True on success, False on failure.
    """
    use_ai = bool(os.environ.get("CLAUDE_API_KEY"))
    message = simplify_for_sms(report, language=language) if use_ai else format_report(report)

    try:
        response = _sms.send(message, [phone_number])
        recipients = response.get("SMSMessageData", {}).get("Recipients", [])
        if recipients:
            status = recipients[0].get("status", "")
            return status == "Success"
        return False
    except Exception as e:
        print(f"[SMS ERROR] Failed to send to {phone_number}: {e}")
        return False
