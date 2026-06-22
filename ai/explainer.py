"""
ai/explainer.py
Optional LLM layer that rewrites compliance obligations into plain,
accessible language for low-literacy SME owners.

Uses the Anthropic Claude API. Falls back to raw rule text if the
API call fails, so the system always returns something useful.
"""

import os
import json
import urllib.request
import urllib.error

_API_URL = "https://api.anthropic.com/v1/messages"
_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 1000

_SYSTEM_PROMPT = """You are a compliance advisor helping small business owners in Africa understand their legal obligations.

Your job is to rewrite compliance obligations in simple, clear language that someone with basic education can understand. 

Rules:
- Use short sentences. Max 15 words per sentence.
- Avoid legal jargon. Replace it with everyday words.
- Be direct and practical. Tell them exactly what to do.
- Use a warm, encouraging tone. Not scary or threatening.
- If given multiple obligations, number them clearly.
- Keep the total response under 300 words.
- Do not add new obligations not in the input.
- End with one encouraging sentence.

Respond in plain text only. No markdown, no bullet symbols, no asterisks."""


def simplify_obligations(obligations: list[dict], business_label: str, risk_level: str, language: str = "en") -> str:
    """
    Takes a list of obligation dicts from the rules engine and returns
    a simplified, human-friendly explanation.

    Args:
        obligations: list of obligation dicts from rules.json
        business_label: e.g. "Online Shop / E-Commerce"
        risk_level: "low" | "medium" | "high"
        language: "en" (English) | "sw" (Swahili) — extensible

    Returns:
        Simplified plain-text string, or fallback text on error.
    """
    if not obligations:
        return "Good news! No immediate compliance issues found for your business type."

    # Build a structured prompt from the obligations
    obl_text = "\n".join(
        f"{i}. {o['title']}: {o['description']} ACTION: {o['action']}"
        for i, o in enumerate(obligations, 1)
    )

    lang_instruction = (
        "Respond in simple Swahili." if language == "sw"
        else "Respond in simple English."
    )

    risk_context = {
        "low":    "This business has minor compliance gaps.",
        "medium": "This business has some important compliance gaps that need attention.",
        "high":   "This business has serious compliance gaps that need urgent action.",
    }.get(risk_level, "")

    user_prompt = f"""Business type: {business_label}
Risk situation: {risk_context}

Here are the compliance obligations for this business:
{obl_text}

{lang_instruction}
Rewrite these obligations in simple language a small business owner can easily understand and act on."""

    payload = json.dumps({
        "model": _MODEL,
        "max_tokens": _MAX_TOKENS,
        "system": _SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }).encode("utf-8")

    api_key = os.environ.get("CLAUDE_API_KEY", "")
    if not api_key:
        return _fallback_text(obligations, risk_level)

    req = urllib.request.Request(
        _API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
            return "\n".join(text_blocks).strip() or _fallback_text(obligations, risk_level)

    except urllib.error.HTTPError as e:
        print(f"[AI ERROR] HTTP {e.code}: {e.read().decode()}")
        return _fallback_text(obligations, risk_level)
    except Exception as e:
        print(f"[AI ERROR] {e}")
        return _fallback_text(obligations, risk_level)


def simplify_for_sms(report: dict, language: str = "en") -> str:
    """
    Entry point for the SMS sender. Takes a full compliance report dict
    and returns AI-simplified text ready to send as an SMS.

    Falls back to structured plain text if AI is unavailable.
    """
    simplified = simplify_obligations(
        obligations=report["obligations"],
        business_label=report["business_label"],
        risk_level=report["risk"]["level"],
        language=language,
    )

    risk_level = report["risk"]["level"].upper()
    risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(risk_level, "")

    header = (
        f"=== Micro-GRC Report ===\n"
        f"Business: {report['business_label']}\n"
        f"Risk: {risk_emoji} {risk_level}\n\n"
    )
    footer = "\n\nDial *384*GRC# to check again."

    return header + simplified + footer


# ── Fallback ──────────────────────────────────────────────────────────────────

def _fallback_text(obligations: list[dict], risk_level: str) -> str:
    """
    Plain structured text used when Claude API is unavailable.
    Always safe to call.
    """
    lines = ["YOUR OBLIGATIONS:"]
    for i, obl in enumerate(obligations, 1):
        lines.append(f"\n{i}. {obl['title']}")
        lines.append(f"   {obl['description']}")
        lines.append(f"   What to do: {obl['action']}")
        if obl.get("penalty"):
            lines.append(f"   Risk: {obl['penalty']}")
    lines.append("\nTake action today to protect your business.")
    return "\n".join(lines)
