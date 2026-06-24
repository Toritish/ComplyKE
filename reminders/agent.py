"""
reminders/agent.py
Daily reminder agent. Finds due subscribers, re-runs their compliance
check, and sends an SMS update via Africa's Talking.

reminders/scheduler.py wires this into APScheduler.
"""

from datetime import datetime
from db.models import get_due_subscribers, update_next_reminder


def run_reminders():
    """
    Entry point called by the scheduler once per day.
    Processes all subscribers whose next_reminder_at is today or overdue.
    """
    subscribers = get_due_subscribers()

    # 💡 FOR LOCAL TESTING: If no subscribers are returned due to 'next_reminder_at' gates,
    # we pull all active users so you can test your reminders immediately.
    if not subscribers:
        import sqlite3
        conn = sqlite3.connect('micro_grc.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscribers WHERE is_active = 1")
        subscribers = [dict(row) for row in cursor.fetchall()]
        conn.close()

    if not subscribers:
        print(f"[REMINDERS] {datetime.utcnow().date()} — no active subscribers found to remind.")
        return

    print(f"[REMINDERS] Processing {len(subscribers)} subscriber(s)...")

    sent, failed = 0, 0
    for sub in subscribers:
        try:
            _process_subscriber(sub)
            update_next_reminder(sub["phone_number"], days=30)
            sent += 1
        except Exception as e:
            print(f"[REMINDERS] Failed for {sub['phone_number']}: {e}")
            failed += 1

    print(f"[REMINDERS] Done — sent: {sent}, failed: {failed}")


def _process_subscriber(sub: dict):
    """Re-run the compliance check for one subscriber and send their SMS."""
    from engine.mapper import get_obligations   # local import avoids circular deps
    from ai.explainer import simplify_for_sms
    from sms.sender import send_sms

    # Rebuild the flags dict to pass as user_flags
    flags = {
        "has_employees":   bool(sub["has_employees"]),
        "collects_data":   bool(sub["collects_data"]),
        "has_premises":    bool(sub["has_premises"]),
        "above_threshold": bool(sub["above_threshold"]),
    }

    # Initialize a structurally sound baseline profile framework with a default risk key
    report = {
        "business_label": sub["business_type"].replace("_", " ").title(),
        "risk": {"level": sub.get("risk_level", "high")},
        "obligations": []
    }

    try:
        # 💡 FIX: Pass the dictionary to the required 'user_flags' positional argument
        report_data = get_obligations(user_flags=flags)
        if report_data and isinstance(report_data, dict):
            # Ensure critical keys exist in returned data, otherwise merge them
            report.update(report_data)
            if "risk" not in report:
                report["risk"] = {"level": sub.get("risk_level", "high")}
    except Exception as e:
        print(f"[AGENT WARNING] Static mapper failed, using baseline profile framework: {e}")

    # 💡 SMART BUSINESS ASSUMPTION FOR KENYA:
    # If it's June, everyone MUST file their KRA Income Tax Return by June 30th.
    current_month = datetime.now().month
    has_kra_in_report = any("KRA" in obl.get("title", "").upper() or "TAX" in obl.get("title", "").upper() for obl in report.get("obligations", []))
    
    if current_month == 6 and not has_kra_in_report:
        print(f"[AGENT] Injecting mandatory June KRA deadline for {sub['phone_number']}")
        if "obligations" not in report:
            report["obligations"] = []
        
        report["obligations"].append({
            "title": "KRA Annual Income Tax Return",
            "description": "Annual filing obligation for individuals and corporate entities for the previous year of income.",
            "action": "Log into your KRA iTax portal before June 30th to submit your return. If you had no source of income, remember to submit a NIL return to avoid a KES 2,000 late penalty fee."
        })

    # Build the reminder SMS via Gemini/Claude
    language = sub.get("language", "en")
    sms_body = simplify_for_sms(report, language=language)

    # Prepend a reminder header so users know why they got the message
    header = (
        "📋 Your monthly ComplyKE compliance check:\n\n"
        if language == "en"
        else "📋 Ukaguzi wako wa kila mwezi wa ComplyKE:\n\n"
    )
    footer = (
        "\n\nReply STOP to unsubscribe."
        if language == "en"
        else "\n\nJibu STOP kujiondoa."
    )

    # Strip the existing footer variations from explainer.py to avoid duplication
    sms_body = sms_body.replace("\n\nDial *384*29319# to check again.", "")
    sms_body = sms_body.replace("\n\nPiga *384*29319# kukagua tena.", "")

    message = header + sms_body + footer

    send_sms(sub["phone_number"], message)
    print(f"[REMINDERS] Sent to {sub['phone_number']} ({sub['business_type']}, {sub['risk_level']})")