"""
engine/mapper.py
Maps user answers → applicable compliance obligations + risk score.
"""

import json
import os

_RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")

with open(_RULES_PATH) as f:
    RULES = json.load(f)


def get_obligations(business_type: str, user_flags: dict) -> list[dict]:
    """
    Return the list of obligations that apply to this business given user_flags.

    user_flags example:
        {
            "collects_customer_data": True,
            "has_employees": False,
            "has_physical_premises": False,
            "turnover_above_vat_threshold": False,
            "unregistered_business": True,
            "no_kra_pin": True,
        }
    """
    biz = RULES["business_types"].get(business_type)
    if not biz:
        return []

    applicable = []
    for obl in biz["obligations"]:
        if obl.get("applies_always"):
            applicable.append(obl)
        elif obl.get("applies_when") and user_flags.get(obl["applies_when"]):
            applicable.append(obl)

    return applicable


def compute_risk_score(business_type: str, user_flags: dict) -> dict:
    """
    Compute a risk score based on which risk factors are present.

    Returns:
        {
            "score": int,
            "level": "low" | "medium" | "high",
            "triggered_factors": [str]
        }
    """
    biz = RULES["business_types"].get(business_type)
    if not biz:
        return {"score": 0, "level": "low", "triggered_factors": []}

    weight_map = RULES["risk_scoring"]["weight_map"]
    thresholds = RULES["risk_scoring"]["thresholds"]

    total = 0
    triggered = []

    for factor, meta in biz["risk_factors"].items():
        if user_flags.get(factor):
            total += meta["weight"]
            triggered.append(factor)

    # Determine level
    level = "low"
    for lvl, rng in thresholds.items():
        if rng["min"] <= total <= rng["max"]:
            level = lvl
            break

    return {
        "score": total,
        "level": level,
        "triggered_factors": triggered
    }


def build_compliance_report(business_type: str, user_flags: dict) -> dict:
    """
    Full report: obligations + risk score, ready to format into SMS.
    """
    obligations = get_obligations(business_type, user_flags)
    risk = compute_risk_score(business_type, user_flags)
    biz_label = RULES["business_types"].get(business_type, {}).get("label", business_type)

    return {
        "business_type": business_type,
        "business_label": biz_label,
        "risk": risk,
        "obligations": obligations,
    }
