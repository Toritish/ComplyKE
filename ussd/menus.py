"""
ussd/menus.py
All USSD menu text strings.
Keep each menu under 182 characters (AT USSD page limit).
"""

MENU_MAIN = """Micro-GRC: Know Your Obligations
Select business type:
1. Online Shop
2. Freelancer
3. Retail Store
4. Food Vendor
5. Mobile Money Agent"""

MENU_EMPLOYEES = """Do you have any employees?
1. Yes
2. No"""

MENU_CUSTOMER_DATA = """Do you collect customer data?
(names, emails, phone numbers)
1. Yes
2. No"""

MENU_PREMISES = """Do you operate from a physical location?
(shop, office, kiosk)
1. Yes
2. No"""

MENU_TURNOVER = """Is your annual revenue above KES 5 million?
1. Yes
2. No / Not sure"""


def text_end(risk_level: str, emoji: str, obl_count: int) -> str:
    return (
        f"Risk Level: {emoji} {risk_level}\n"
        f"You have {obl_count} compliance obligation(s).\n"
        f"Full details sent via SMS.\n"
        f"Dial again anytime to re-check."
    )


def text_processing() -> str:
    return "Processing your compliance profile...\nYou will receive an SMS shortly."
