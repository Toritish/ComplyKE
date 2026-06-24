"""
ussd/menus_sw.py
Swahili translations of all USSD menu strings.
Keep each menu under 182 characters (AT USSD page limit).
"""

MENU_MAIN = """Micro-GRC: Jua Wajibu Wako
Chagua aina ya biashara:
1. Duka la Mtandaoni
2. Kazi Huru / Freelancer
3. Duka la Rejareja
4. Muuza Chakula
5. Wakala wa Pesa (M-Pesa)"""

MENU_EMPLOYEES = """Je, una wafanyakazi?
1. Ndiyo
2. Hapana"""

MENU_CUSTOMER_DATA = """Je, unakusanya taarifa za wateja?
(majina, barua pepe, nambari za simu)
1. Ndiyo
2. Hapana"""

MENU_PREMISES = """Je, una mahali pa biashara?
(duka, ofisi, kibanda)
1. Ndiyo
2. Hapana"""

MENU_TURNOVER = """Je, mapato yako ya mwaka yanazidi KES 5 milioni?
1. Ndiyo
2. Hapana / Sijui"""


def text_end(risk_level: str, emoji: str, obl_count: int) -> str:
    level_sw = {"LOW": "CHINI", "MEDIUM": "WASTANI", "HIGH": "JUU"}.get(risk_level, risk_level)
    return (
        f"Hatari: {emoji} {level_sw}\n"
        f"Wajibu {obl_count} wamepatikana.\n"
        f"Ripoti imetumwa kwa SMS.\n"
        f"Jibu NDIYO kupata vikumbusho."
    )
