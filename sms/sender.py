"""
sms/sender.py
Formats the compliance report and delivers it via Africa's Talking SMS API.
"""

import os
import requests
from ai.explainer import simplify_for_sms

RISK_LABELS = {
    "low":    "🟢 LOW   - Minor gaps. Review obligations below.",
    "medium": "🟡 MEDIUM - Action needed. See obligations below.",
    "high":   "🔴 HIGH  - Urgent! Address these obligations now.",
}

MAX_SMS_CHARS = 459


def format_report(report: dict) -> str:
    biz_label = report["business_label"]
    risk = report["risk"]
    obligations = report["obligations"]
    risk_line = RISK_LABELS.get(risk["level"], risk["level"].upper())

    lines = [
        f"=== ComplyKE Report ===",
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

    lines.append("Dial *384*29319# anytime to re-check.")

    full_text = "\n".join(lines)
    if len(full_text) > MAX_SMS_CHARS:
        full_text = full_text[:MAX_SMS_CHARS - 3] + "..."
    return full_text


def send_sms_report(phone_number: str, report: dict, language: str = "en") -> bool:
    use_ai = bool(os.environ.get("CLAUDE_API_KEY"))
    print(f"[SMS] AI enabled: {use_ai}")

    message = simplify_for_sms(report, language=language) if use_ai else format_report(report)
    message = message.replace('%', 'percent')

    print(f"[SMS] Sending to: {phone_number}")
    print(f"[SMS] Message:\n{message}")

    username = os.environ.get("AT_USERNAME", "sandbox")
    api_key = os.environ.get("AT_API_KEY", "")

    if not api_key:
        print(f"[SMS] No AT API key found.")
        return False

    try:
        response = requests.post(
            "https://api.sandbox.africastalking.com/version1/messaging",
            headers={
                "apiKey": api_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            },
            data={
                "username": username,
                "to": phone_number,
                "message": message
            },
            verify=False,
            timeout=10
        )
        print(f"[SMS] Response: {response.status_code} {response.text}")
        return response.status_code == 201
    except Exception as e:
        print(f"[SMS ERROR] {e}")
        return False