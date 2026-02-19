# SMS Setup (Parent Notification on Student Leave)

When a student is marked as "Left Campus" by the guard, an SMS is sent to **both parents** (father and mother mobile numbers) with:

> Hi, your ward [Roll No] ([Name]), [College], [Section], [Course] has left the college. If not given permission, contact HOD at [HOD Phone].

## Enable SMS

Set these environment variables before starting the server:

```bash
export SMS_ENABLED=true
export SMS_PROVIDER=msg91   # or fast2sms, twilio
```

## Provider Configuration

### MSG91 (India)
```bash
export MSG91_AUTH_KEY=your_auth_key
export MSG91_SENDER_ID=FACES   # optional, 6-char sender ID
```

### Fast2SMS (India)
```bash
export FAST2SMS_API_KEY=your_api_key
```

### Twilio
```bash
export TWILIO_ACCOUNT_SID=...
export TWILIO_AUTH_TOKEN=...
export TWILIO_PHONE=+1234567890   # your Twilio number
```

## When SMS is Disabled

If `SMS_ENABLED` is not set or is `false`, the "mark left" action still succeeds. The message is only logged (for debugging). No SMS is sent.
