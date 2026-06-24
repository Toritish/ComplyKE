"""
ai/explainer.py
Uses Google Gemini API to simplify compliance obligations into plain language.
"""

import os
import json
import urllib.request

_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"

_SYSTEM_PROMPT = """You are a compliance advisor for small business owners in Africa. 

Rewrite compliance obligations in this exact format:
[Business Type] Compliance:
1. [Short action - max 10 words]
2. [Short action - max 10 words]
3. [Short action - max 10 words]
4. [Short action - max 10 words]

Rules:
- Numbered list only
- Each item max 10 words
- No explanations
- No legal jargon
- Plain text only
- Total response under 200 characters"""

def simplify_for_sms(report: dict, language: str = "en") -> str:
    obligations = report["obligations"]
    business_label = report["business_label"]
    risk_level = report["risk"]["level"]

    if not obligations:
        return "Good news! No immediate compliance issues found."

    obl_text = "\n".join(
        f"{i}. {o['title']}: {o['description']} ACTION: {o['action']}"
        for i, o in enumerate(obligations, 1)
    )

    lang_instruction = "Respond in simple Swahili." if language == "sw" else "Respond in simple English."

    prompt = f"""Business: {business_label}
Risk: {risk_level}

Obligations:
{obl_text}

{lang_instruction}
Rewrite these in simple language a small business owner can understand and act on."""

    api_key = os.environ.get("CLAUDE_API_KEY", "")
    if not api_key:
        return _fallback_text(obligations, risk_level)

    url = f"{_API_URL}?key={api_key}"

    payload = json.dumps({
        "contents": [{
            "parts": [{"text": _SYSTEM_PROMPT + "\n\n" + prompt}]
        }]
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]

            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk_level, "")
            header = f"=== ComplyKE Report ===\nBusiness: {business_label}\nRisk: {risk_emoji} {risk_level.upper()}\n\n"
            footer = "\n\nDial *384*29319# to check again."

            return (header + text.strip() + footer).replace('%', 'percent')

    except Exception as e:
        print(f"[AI ERROR] {e}")
        return _fallback_text(obligations, risk_level)


def _fallback_text(obligations: list, risk_level: str) -> str:
    lines = ["YOUR OBLIGATIONS:"]
    for i, obl in enumerate(obligations, 1):
        lines.append(f"\n{i}. {obl['title']}")
        lines.append(f"   {obl['description']}")
        lines.append(f"   What to do: {obl['action']}")
    lines.append("\nTake action today to protect your business.")
    return "\n".join(lines)