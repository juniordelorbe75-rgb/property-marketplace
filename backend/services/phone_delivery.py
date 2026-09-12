import base64
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from fastapi import HTTPException


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sms_configured():
    return bool(
        re.fullmatch(r"AC[0-9a-fA-F]{32}", os.getenv("TWILIO_ACCOUNT_SID", ""))
        and re.fullmatch(r"VA[0-9a-fA-F]{32}", os.getenv("TWILIO_VERIFY_SERVICE_SID", ""))
        and os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    )


def _request(resource, data):
    if not sms_configured():
        raise HTTPException(503, "La verificación por SMS todavía no está configurada.")
    account = os.environ["TWILIO_ACCOUNT_SID"]
    service = os.environ["TWILIO_VERIFY_SERVICE_SID"]
    credentials = base64.b64encode(f"{account}:{os.environ['TWILIO_AUTH_TOKEN']}".encode()).decode()
    request = Request(
        f"https://verify.twilio.com/v2/Services/{service}/{resource}",
        data=urlencode(data).encode(), method="POST",
        headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with build_opener(NoRedirects()).open(request, timeout=10) as response:
            result = json.loads(response.read(65537))
        if not isinstance(result, dict):
            raise ValueError("Invalid response")
        return result
    except HTTPError as error:
        if resource == "VerificationCheck" and error.code == 404:
            return {"status": "expired"}
        raise HTTPException(503, "No pudimos confirmar la operación por SMS. Intente más tarde.") from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise HTTPException(503, "No pudimos confirmar la operación por SMS. Intente más tarde.") from None


def send_phone_code(phone):
    prefixes = [item.strip() for item in os.getenv("SMS_ALLOWED_PREFIXES", "+1809,+1829,+1849").split(",") if item.strip()]
    if not prefixes or not any(phone.startswith(prefix) for prefix in prefixes):
        raise HTTPException(400, "La verificación por SMS no está disponible para ese número.")
    data = _request("Verifications", {"To": phone, "Channel": "sms", "Locale": "es"})
    if data.get("status") != "pending" or data.get("to") != phone or not re.fullmatch(r"VE[0-9a-fA-F]{32}", data.get("sid", "")):
        raise HTTPException(503, "No pudimos confirmar el envío del código.")
    return data["sid"]


def check_phone_code(sid, phone, code):
    data = _request("VerificationCheck", {"VerificationSid": sid, "Code": code})
    return data.get("status") == "approved" and data.get("sid") == sid and data.get("to") == phone
