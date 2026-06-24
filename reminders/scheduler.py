"""
reminders/scheduler.py
Wires the reminder agent into APScheduler.
Call init_scheduler(app) once from app.py after the app is created.
Runs daily at 08:00 Nairobi time (Africa/Nairobi = UTC+3).
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

_scheduler = BackgroundScheduler(timezone=pytz.utc)


def init_scheduler(app):
    """
    Start the background scheduler bound to the Flask app context.
    Safe to call multiple times — won't start if already running.
    """
    if _scheduler.running:
        return

    nairobi_tz = pytz.timezone("Africa/Nairobi")

    # 08:00 Nairobi = 05:00 UTC
    _scheduler.add_job(
        func=_run_with_context(app),
        trigger=CronTrigger(hour=5, minute=0, timezone=pytz.utc),
        id="daily_reminders",
        name="Daily compliance reminders",
        replace_existing=True,
        misfire_grace_time=3600,  # run even if server was down, up to 1hr late
    )

    _scheduler.start()
    print(f"[SCHEDULER] Started — daily reminders at 08:00 Nairobi time.")


def _run_with_context(app):
    """
    Returns a callable that runs the reminder agent inside the Flask app context.
    Required so agent.py can access current_app, db connections, etc.
    """
    def job():
        with app.app_context():
            from reminders.agent import run_reminders
            run_reminders()
    return job


def shutdown_scheduler():
    """Call on app teardown to avoid orphaned threads."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)