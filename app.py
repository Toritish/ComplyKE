"""
app.py
Flask entry point for the Micro-GRC USSD + SMS compliance assistant.

Endpoints:
  POST /ussd               — Africa's Talking USSD callback
  GET  /health             — Health check
  POST /sms/inbound        — (Via Blueprint) Handles incoming SMS
  POST /admin/run-reminders — Manual trigger for testing reminders
"""
import os
import atexit
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

from flask import Flask, request, Response
from ussd.handler import handle_ussd

# New feature imports
from db.models import init_db
from sms.inbound import inbound_bp
from reminders.scheduler import init_scheduler, shutdown_scheduler

# Initialize Flask app
app = Flask(__name__)

# --- Database & Scheduler Initialization ---
# Initialize DB tables on startup
init_db()

# Start the daily reminder scheduler
init_scheduler(app)

# Graceful shutdown for the scheduler
atexit.register(shutdown_scheduler)


# --- Blueprints ---
app.register_blueprint(inbound_bp)   # handles POST /sms/inbound


# --- Route Handlers ---

@app.route("/ussd", methods=["POST"])
def ussd_callback():
    """
    Africa's Talking USSD gateway callback.
    Expected form fields: sessionId, phoneNumber, networkCode, serviceCode, text
    Must respond within 5 seconds.
    """
    session_id   = request.form.get("sessionId", "")
    phone_number = request.form.get("phoneNumber", "")
    network_code = request.form.get("networkCode", "")
    service_code = request.form.get("serviceCode", "")
    text         = request.form.get("text", "")

    app.logger.info(
        f"USSD | session={session_id} phone={phone_number} "
        f"network={network_code} text={repr(text)}"
    )

    response_text = handle_ussd(session_id, phone_number, text)

    # Africa's Talking expects plain text, Content-Type: text/plain
    return Response(response_text, content_type="text/plain")


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "micro-grc"}, 200


# --- Admin / Testing Endpoints ---

@app.route("/admin/run-reminders", methods=["POST"])
def trigger_reminders():
    """
    Manual trigger endpoint for testing reminders without waiting.
    Remove or protect with a secret key before going to production.
    """
    from reminders.agent import run_reminders
    run_reminders()
    return {"status": "done"}, 200


if __name__ == "__main__":
    # Kept port=5000 from your original setup explicitly
    app.run(debug=True, port=5000)