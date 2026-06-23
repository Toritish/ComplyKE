"""
app.py
Flask entry point for the Micro-GRC USSD + SMS compliance assistant.

Endpoints:
  POST /ussd   — Africa's Talking USSD callback
  GET  /health — Health check
"""
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, Response
from ussd.handler import handle_ussd

app = Flask(__name__)


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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
