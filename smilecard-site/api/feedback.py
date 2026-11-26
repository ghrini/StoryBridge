"""POST /api/feedback: the Testimonials page form. Each message is emailed to SmileCard's inbox.

A Vercel Python function using only the standard library. It needs these environment variables
(set them in Vercel: Project → Settings → Environment Variables; never put them in the code):
    SMTP_USER          the Gmail address that sends the email (e.g. SmileCard's own Gmail)
    SMTP_APP_PASSWORD  a Gmail "app password" for that address (needs 2-Step Verification on the account)
    FEEDBACK_TO        optional: where messages go (defaults to SMTP_USER)
    SMTP_HOST / SMTP_PORT  optional: default smtp.gmail.com / 465 (SSL)

Nothing is stored here: the message goes straight into the email. The visitor's address is set as
Reply-To, so pressing Reply in Gmail answers them. Nothing personal is written to the logs.
"""
import json
import os
import re
import smtplib
import threading
import time
from email.message import EmailMessage
from email.utils import formataddr
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

MAX_BODY = 20_000  # bytes; a long message is about 5,000 characters
MIN_SECONDS = 2.0  # a person needs longer than this to fill in the form
RATE_LIMIT = 5  # messages per address per window, per running copy of the function
RATE_WINDOW = 600  # seconds
LIMITS = {"first_name": 80, "last_name": 80, "email": 254, "phone": 40, "message": 5000}
EMAIL = re.compile(r"^[^@\s<>,;:\"]+@[^@\s<>,;:\"]+\.[A-Za-z]{2,}$")
PHONE = re.compile(r"^[0-9+()\-.\s]{0,40}$")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_recent: dict[str, list[float]] = {}
_lock = threading.Lock()


def _clean_line(value) -> str:
    """One line of plain text: no line breaks (they could add email headers) and no control characters."""
    return CONTROL.sub("", str(value or "")).replace("\r", " ").replace("\n", " ").strip()


def _clean_text(value) -> str:
    return CONTROL.sub("", str(value or "")).replace("\r\n", "\n").replace("\r", "\n").strip()


def validate(data) -> tuple[dict | None, dict]:
    """Return (clean fields, {}) or (None, {field: problem})."""
    if not isinstance(data, dict):
        return None, {"form": "missing"}
    fields = {
        "first_name": _clean_line(data.get("first_name")),
        "last_name": _clean_line(data.get("last_name")),
        "email": _clean_line(data.get("email")),
        "phone": _clean_line(data.get("phone")),
        "message": _clean_text(data.get("message")),
    }
    problems = {}
    for name, limit in LIMITS.items():
        if len(fields[name]) > limit:
            problems[name] = "too_long"
    for name in ("first_name", "email", "message"):
        if not fields[name]:
            problems[name] = "required"
    if fields["email"] and "email" not in problems and not EMAIL.match(fields["email"]):
        problems["email"] = "invalid"
    if fields["phone"] and "phone" not in problems and not PHONE.match(fields["phone"]):
        problems["phone"] = "invalid"
    return (None, problems) if problems else (fields, {})


def looks_automated(data) -> bool:
    """Spam checks: a hidden field people never see, and a form sent too fast for a person to have typed it."""
    if not isinstance(data, dict):
        return False
    if _clean_line(data.get("website")):
        return True
    try:
        return float(data.get("elapsed_ms", 0)) / 1000 < MIN_SECONDS
    except (TypeError, ValueError):
        return True


def too_many(client: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    with _lock:
        times = [t for t in _recent.get(client, []) if now - t < RATE_WINDOW]
        blocked = len(times) >= RATE_LIMIT
        if not blocked:
            times.append(now)
        _recent[client] = times
        return blocked


def build_email(fields: dict, sender: str, to: str) -> EmailMessage:
    name = " ".join(part for part in (fields["first_name"], fields["last_name"]) if part)
    msg = EmailMessage()
    msg["Subject"] = f"SmileCard website message from {name}"
    msg["From"] = formataddr(("SmileCard website", sender))
    msg["To"] = to
    msg["Reply-To"] = formataddr((name, fields["email"]))
    msg.set_content(
        "New message from the feedback form on the SmileCard website.\n\n"
        f"Name:  {name}\n"
        f"Email: {fields['email']}\n"
        f"Phone: {fields['phone'] or '(not given)'}\n\n"
        f"Message:\n{fields['message']}\n\n"
        "Press Reply to answer them.\n"
    )
    return msg


def send_email(msg: EmailMessage, env) -> None:
    host = env.get("SMTP_HOST", "smtp.gmail.com")
    port = int(env.get("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(host, port, timeout=20) as server:
        server.login(env["SMTP_USER"], env["SMTP_APP_PASSWORD"])
        server.send_message(msg)


def same_site(headers) -> bool:
    """Browsers send Origin with a POST. Refuse forms posted from other websites."""
    origin = headers.get("Origin")
    if not origin:
        return True
    host = (headers.get("X-Forwarded-Host") or headers.get("Host") or "").split(",")[0].strip().lower()
    return bool(host) and urlsplit(origin).netloc.lower() == host


def handle(method: str, headers, body: bytes, client: str, env=None, sender=None):
    """Return (status, response dict). Kept apart from the HTTP plumbing so it can be tested directly."""
    env = os.environ if env is None else env
    sender = sender or send_email
    if method != "POST":
        return 405, {"ok": False, "error": "method_not_allowed"}
    if not same_site(headers):
        return 403, {"ok": False, "error": "wrong_site"}
    if "application/json" not in (headers.get("Content-Type") or ""):
        return 415, {"ok": False, "error": "json_only"}
    if len(body) > MAX_BODY:
        return 413, {"ok": False, "error": "too_large"}
    try:
        data = json.loads(body.decode("utf-8") or "null")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 400, {"ok": False, "error": "bad_json"}
    if looks_automated(data):
        return 200, {"ok": True}  # say nothing useful to a bot
    fields, problems = validate(data)
    if problems:
        return 400, {"ok": False, "error": "invalid", "fields": problems}
    if too_many(client):
        return 429, {"ok": False, "error": "too_many"}
    if not env.get("SMTP_USER") or not env.get("SMTP_APP_PASSWORD"):
        print("feedback: email is not set up (SMTP_USER / SMTP_APP_PASSWORD missing)")
        return 503, {"ok": False, "error": "not_configured"}
    to = env.get("FEEDBACK_TO") or env["SMTP_USER"]
    try:
        sender(build_email(fields, env["SMTP_USER"], to), env)
    except (smtplib.SMTPException, OSError) as error:
        print(f"feedback: sending failed ({type(error).__name__})")
        return 502, {"ok": False, "error": "send_failed"}
    print("feedback: message sent")
    return 200, {"ok": True}


class handler(BaseHTTPRequestHandler):
    """Vercel calls this class for requests to /api/feedback."""

    def _respond(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        if status == 405:
            self.send_header("Allow", "POST")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _run(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        body = self.rfile.read(min(length, MAX_BODY + 1)) if length > 0 else b""
        forwarded = (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        client = forwarded or self.client_address[0]
        status, payload = handle(self.command, self.headers, body, client)
        self._respond(status, payload)

    do_POST = _run
    do_GET = _run
    do_PUT = _run
    do_DELETE = _run

    def log_message(self, *args):  # the default log line includes the visitor's IP address
        pass
