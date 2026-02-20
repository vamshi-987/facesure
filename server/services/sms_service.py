"""
SMS service for sending notifications.
Configure via environment variables:
- SMS_ENABLED: "true" to enable
- SMS_PROVIDER: "msg91" | "fast2sms" | "twilio"
- Fast2SMS (recommended for India, no DLT): FAST2SMS_API_KEY, uses Quick SMS route (no sender ID)
- MSG91 (India, requires DLT + 6-char sender): MSG91_AUTH_KEY, MSG91_SENDER_ID
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
    """Quick SMS route (q): no DLT registration or 6-char sender ID needed."""
    api_key = os.environ.get("FAST2SMS_API_KEY") or os.environ.get("SMS_API_KEY")
    if not api_key or api_key.startswith("REPLACE_"):
        print(f"[SMS] Fast2SMS: API key missing or placeholder (key starts with: {api_key[:10] if api_key else 'None'}...)")
        logger.warning("Fast2SMS: API key missing or placeholder")
        return False
    
    # Remove country code "91" prefix only (not all leading 9s and 1s)
    if phone.startswith("91") and len(phone) >= 12:
        num = phone[2:]  # Remove first 2 chars ("91")
    else:
        num = phone
    print(f"[SMS] Fast2SMS: Sending to {num[:3]}**** (len={len(num)}), message length: {len(message)}")
    
    try:
        import urllib.request
        import urllib.error
        import urllib.parse
        import json
        
        # Try POST method first (more reliable for Fast2SMS)
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {
            "route": "q",
            "message": message[:1600],
            "numbers": num,
        }
        data = json.dumps(payload).encode('utf-8')
        
        print(f"[SMS] Fast2SMS POST: route=q, numbers={num}, message_len={len(message)}")
        
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", api_key)
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            print(f"[SMS] Fast2SMS response body: {body[:500]}")
            result = json.loads(body) if body.strip() else {}
            ok = result.get("return") is True
            if not ok:
                print(f"[SMS] Fast2SMS response not OK: {result}")
                logger.warning("Fast2SMS response not OK: %s", result)
            else:
                print(f"[SMS] Fast2SMS SUCCESS: {result.get('message', 'OK')}")
            return ok
    except urllib.error.HTTPError as e:
        try:
            err_body = e.fp.read().decode() if e.fp else ""
        except Exception:
            err_body = str(e)
        print(f"[SMS] Fast2SMS HTTP ERROR {e.code}: {err_body[:500]}")
        logger.warning("Fast2SMS HTTP %s: %s", e.code, err_body[:200])
        return False
    except Exception as e:
        print(f"[SMS] Fast2SMS EXCEPTION: {type(e).__name__}: {str(e)}")
        logger.warning("Fast2SMS failed: %s", e)
        import traceback
        traceback.print_exc()
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
    print(f"[SMS] send_sms called with phone: {phone[:3] + '****' if phone else 'None'}")
    
    if not phone or not message:
        print("[SMS] Skipped: empty phone or message")
        logger.warning("[SMS] Skipped: empty phone or message")
        return False
    
    normalized = _normalize_phone(phone)
    print(f"[SMS] Normalized phone: {normalized[:3] + '****' if normalized else 'INVALID'}")
    
    if not normalized or len(normalized) < 10:
        print(f"[SMS] Invalid phone format: {phone} -> {normalized}")
        logger.warning("[SMS] Invalid phone: %s", phone)
        return False

    sms_enabled = os.environ.get("SMS_ENABLED", "").lower() in ("true", "1", "yes")
    provider = os.environ.get("SMS_PROVIDER", "msg91").lower()
    
    print(f"[SMS] Config: SMS_ENABLED={sms_enabled}, SMS_PROVIDER={provider}")
    
    if not sms_enabled:
        print(f"[SMS disabled] Would send to {normalized[:6]}****: {message[:80]}...")
        logger.info("[SMS disabled] Would send to %s: %s", normalized[:6] + "****", message[:80] + "...")
        return True  # Don't fail the caller

    if provider == "msg91":
        return _send_msg91(normalized, message)
    if provider == "fast2sms":
        return _send_fast2sms(normalized, message)
    if provider == "twilio":
        return _send_twilio(normalized, message)
    
    print(f"[SMS] Unknown SMS_PROVIDER: {provider}")
    logger.warning("Unknown SMS_PROVIDER: %s", provider)
    return False


def send_left_campus_notification(
    student_roll: str,
    student_name: str,
    reason: str,
    father_mobile: str,
    mother_mobile: str,
    hod_name: str,
    hod_phone: str,
) -> None:
    """Send SMS to both parents when student leaves campus."""
    print(f"[SMS] send_left_campus_notification called: roll={student_roll}, name={student_name}")
    print(f"[SMS] Father mobile: {father_mobile[:3] + '****' if father_mobile else 'MISSING'}")
    print(f"[SMS] Mother mobile: {mother_mobile[:3] + '****' if mother_mobile else 'MISSING'}")
    
    reason_text = reason.strip() if reason else "not specified"
    hod_parts = [p for p in [hod_name, hod_phone] if p]
    hod_contact = "contact HOD - " + " ".join(hod_parts) if hod_parts else "contact HOD"
    message = (
        f"Your ward with roll no {student_roll}, name {student_name} has left clg with reason: {reason_text}. "
        f"If not given permission {hod_contact}."
    )
    
    father_sent = False
    mother_sent = False
    
    if father_mobile:
        print(f"[SMS] Attempting to send to father: {father_mobile[:3]}****")
        father_sent = send_sms(father_mobile, message)
        print(f"[SMS] Father SMS result: {'SUCCESS' if father_sent else 'FAILED'}")
    else:
        print("[SMS] Father mobile missing - skipping")
        
    if mother_mobile:
        print(f"[SMS] Attempting to send to mother: {mother_mobile[:3]}****")
        mother_sent = send_sms(mother_mobile, message)
        print(f"[SMS] Mother SMS result: {'SUCCESS' if mother_sent else 'FAILED'}")
    else:
        print("[SMS] Mother mobile missing - skipping")
    
    if not father_sent and not mother_sent:
        print("[SMS] WARNING: No SMS sent to either parent!")
