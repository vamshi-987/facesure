"""
SMS service for sending notifications.
Configure via environment variables:
- SMS_ENABLED: "true" to enable
- SMS_PROVIDER: "msg91" | "fast2sms" | "twilio"
- MSG91: MSG91_AUTH_KEY, MSG91_SENDER_ID (optional)
- Fast2SMS: FAST2SMS_API_KEY
- Twilio: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE
"""
import os
import re
import logging

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    """Ensure Indian mobile number has country code."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) == 10:
        return "91" + digits
    if digits.startswith("91") and len(digits) == 12:
        return digits
    return digits if digits else ""


def _send_msg91(phone: str, message: str) -> bool:
    auth_key = os.environ.get("MSG91_AUTH_KEY") or os.environ.get("SMS_API_KEY")
    if not auth_key:
        return False
    try:
        import urllib.request
        import urllib.parse
        url = "https://api.msg91.com/api/sendhttp.php"
        params = urllib.parse.urlencode({
            "mobiles": phone.lstrip("91") if phone.startswith("91") else phone,
            "authkey": auth_key,
            "sender": os.environ.get("MSG91_SENDER_ID", "FACES"),
            "message": message[:1600],
            "route": "4",
        })
        req = urllib.request.Request(f"{url}?{params}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning("MSG91 SMS failed: %s", e)
        return False


def _send_fast2sms(phone: str, message: str) -> bool:
    api_key = os.environ.get("FAST2SMS_API_KEY") or os.environ.get("SMS_API_KEY")
    if not api_key:
        return False
    try:
        import urllib.request
        import json
        url = "https://www.fast2sms.com/dev/bulkV2"
        data = json.dumps({
            "route": "q",
            "message": message[:1600],
            "numbers": phone.lstrip("91") if phone.startswith("91") else phone,
        }).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", api_key)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            return result.get("return") is True
    except Exception as e:
        logger.warning("Fast2SMS failed: %s", e)
        return False


def _send_twilio(phone: str, message: str) -> bool:
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_phone = os.environ.get("TWILIO_PHONE")
    if not all([sid, token, from_phone]):
        return False
    try:
        from twilio.rest import Client
        client = Client(sid, token)
        to = f"+{phone}" if not phone.startswith("+") else phone
        client.messages.create(body=message[:1600], from_=from_phone, to=to)
        return True
    except Exception as e:
        logger.warning("Twilio SMS failed: %s", e)
        return False


def send_sms(phone: str, message: str) -> bool:
    """Send SMS to the given phone number. Returns True if sent successfully."""
    if not phone or not message:
        return False
    normalized = _normalize_phone(phone)
    if not normalized or len(normalized) < 10:
        logger.warning("Invalid phone for SMS: %s", phone)
        return False

    if os.environ.get("SMS_ENABLED", "").lower() not in ("true", "1", "yes"):
        logger.info("[SMS disabled] Would send to %s: %s", normalized[:6] + "****", message[:80] + "...")
        return True  # Don't fail the caller

    provider = os.environ.get("SMS_PROVIDER", "msg91").lower()
    if provider == "msg91":
        return _send_msg91(normalized, message)
    if provider == "fast2sms":
        return _send_fast2sms(normalized, message)
    if provider == "twilio":
        return _send_twilio(normalized, message)
    logger.warning("Unknown SMS_PROVIDER: %s", provider)
    return False


def send_left_campus_notification(
    student_roll: str,
    student_name: str,
    college: str,
    section: str,
    course: str,
    father_mobile: str,
    mother_mobile: str,
    hod_phone: str,
) -> None:
    """Send SMS to both parents when student leaves campus."""
    hod_contact = f"Contact HOD at {hod_phone}" if hod_phone else "Contact HOD for details"
    message = (
        f"Hi, your ward {student_roll} ({student_name}), {college}, {section}, {course} "
        f"has left the college. If not given permission, {hod_contact}."
    )
    if father_mobile:
        send_sms(father_mobile, message)
    if mother_mobile and mother_mobile != father_mobile:
        send_sms(mother_mobile, message)
