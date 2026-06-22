"""
ussd/handler.py
State machine for the USSD session flow.

Africa's Talking sends POST requests with:
  - sessionId   : unique session identifier
  - phoneNumber : user's MSISDN
  - networkCode : carrier code
  - serviceCode : USSD shortcode
  - text        : accumulated user input, e.g. "1*2*1"

We respond with plain text:
  - "CON <text>"  → continue session (show menu)
  - "END <text>"  → end session (final message)

Language selection is the FIRST step (before business type).
  text="" → language menu
  text="1" → English selected → show business type menu
  text="2" → Swahili selected → show business type menu (Swahili)
  text="1*3" → English + business type 3 (retail), etc.
"""

import ussd.menus as menus_en
import ussd.menus_sw as menus_sw
from engine.mapper import build_compliance_report
from sms.sender import send_sms_report

BUSINESS_TYPE_MAP = {
    "1": "online_shop",
    "2": "freelancer",
    "3": "retail_store",
    "4": "food_vendor",
    "5": "agent_service",
}

LANG_MAP = {"1": "en", "2": "sw"}

MENU_LANG = "Micro-GRC\nChagua lugha / Select language:\n1. English\n2. Kiswahili"

INVALID_EN = "CON Invalid option. Please try again.\n"
INVALID_SW = "CON Chaguo batili. Tafadhali jaribu tena.\n"
ERROR_EN = "END Something went wrong. Please try again."
ERROR_SW = "END Hitilafu imetokea. Tafadhali jaribu tena."


def _menus(lang: str):
    return menus_sw if lang == "sw" else menus_en


def handle_ussd(session_id: str, phone_number: str, text: str) -> str:
    """
    Main dispatcher. Parses accumulated `text` to determine session state.
    Returns a CON or END string.

    Step layout (text = "L*B*E*D*P*T"):
      L = language choice (1=EN, 2=SW)
      B = business type (1-5)
      E = has employees (1/2)
      D = collects data (1/2)
      P = has premises (1/2)
      T = turnover above 5M (1/2)
    """
    steps = text.strip().split("*") if text.strip() else []
    depth = len(steps)

    # ── Step 0: Language selection ──
    if depth == 0 or steps[0] == "":
        return f"CON {MENU_LANG}"

    lang = LANG_MAP.get(steps[0])
    if not lang:
        return INVALID_EN

    m = _menus(lang)
    invalid = INVALID_SW if lang == "sw" else INVALID_EN
    error   = ERROR_SW   if lang == "sw" else ERROR_EN

    # ── Step 1: Language chosen → show business type menu ──
    if depth == 1:
        return f"CON {m.MENU_MAIN}"

    # ── Step 2: Business type selected ──
    if depth == 2:
        if steps[1] not in BUSINESS_TYPE_MAP:
            return invalid
        return f"CON {m.MENU_EMPLOYEES}"

    # ── Step 3: Employees question ──
    if depth == 3:
        if steps[2] not in ("1", "2"):
            return invalid
        return f"CON {m.MENU_CUSTOMER_DATA}"

    # ── Step 4: Customer data question ──
    if depth == 4:
        if steps[3] not in ("1", "2"):
            return invalid
        return f"CON {m.MENU_PREMISES}"

    # ── Step 5: Premises question ──
    if depth == 5:
        if steps[4] not in ("1", "2"):
            return invalid
        return f"CON {m.MENU_TURNOVER}"

    # ── Step 6: Turnover answered → generate report ──
    if depth >= 6:
        if steps[5] not in ("1", "2"):
            return invalid

        business_type = BUSINESS_TYPE_MAP.get(steps[1])
        if not business_type:
            return error

        user_flags = _build_flags(steps, offset=1)
        report = build_compliance_report(business_type, user_flags)

        send_sms_report(phone_number, report, language=lang)

        risk_level = report["risk"]["level"].upper()
        risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(risk_level, "")
        obl_count  = len(report["obligations"])

        return f"END {m.text_end(risk_level, risk_emoji, obl_count)}"

    return error


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_flags(steps: list[str], offset: int = 0) -> dict:
    """
    Translate USSD answers into the flag dict expected by the rules engine.
    offset=1 because steps[0] is now the language choice.

    steps[offset+0] = business type  (handled separately)
    steps[offset+1] = has employees  (1=yes, 2=no)
    steps[offset+2] = collects data  (1=yes, 2=no)
    steps[offset+3] = has premises   (1=yes, 2=no)
    steps[offset+4] = turnover >5M   (1=yes, 2=no)
    """
    def yes(rel_index: int) -> bool:
        idx = offset + rel_index
        return len(steps) > idx and steps[idx] == "1"

    has_employees  = yes(2)
    collects_data  = yes(3)
    has_premises   = yes(4)
    high_turnover  = yes(5)

    return {
        "has_employees":                has_employees,
        "collects_customer_data":       collects_data,
        "has_physical_premises":        has_premises,
        "turnover_above_vat_threshold": high_turnover,
        "unregistered_business":        True,
        "no_kra_pin":                   True,
        "no_county_permit":             has_premises,
        "has_employees_no_nssf":        has_employees,
        "has_employees_no_paye":        has_employees,
        "no_health_certificate":        False,
        "no_agent_authorization":       False,
        "no_kyc_process":               False,
        "never_filed_returns":          True,
    }
