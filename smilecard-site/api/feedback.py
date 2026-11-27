"""POST /api/feedback: the Testimonials page form.

A Vercel Python function using only the standard library. Each message is saved as a text file in the
PRIVATE Vercel Blob store "smilecard-feedback" (Vercel → Storage → smilecard-feedback), which only people
signed in to the Vercel team can read. Vercel adds BLOB_STORE_ID when the store is connected to the project,
and signs each request with a short-lived OIDC token, so there is no password to keep.

Email is optional, for later: if SMTP_USER and SMTP_APP_PASSWORD (a Gmail app password) are set in Vercel,
each message is also emailed (to FEEDBACK_TO, or SMTP_USER), with the visitor as Reply-To.

Nothing personal is written to the logs.
"""
import json
import os
import re
import secrets
import smtplib
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr
from http.server import BaseHTTPRequestHandler
import urllib.parse
from urllib.parse import urlsplit

MAX_BODY = 20_000  # bytes; a long message is about 5,000 characters
MIN_SECONDS = 2.0  # a person needs longer than this to fill in the form
RATE_LIMIT = 5  # messages per address per window, per running copy of the function
RATE_WINDOW = 600  # seconds
LIMITS = {"first_name": 80, "last_name": 80, "email": 254, "phone": 40, "message": 5000}
EMAIL = re.compile(r"^[^@\s<>,;:\"]+@[^@\s<>,;:\"]+\.[A-Za-z]{2,}$")
PHONE = re.compile(r"^[0-9+()\-.\s]{0,40}$")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

BLOB_API = "https://vercel.com/api/blob/"  # what Vercel's own @vercel/blob library calls (API version 13)

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


def message_text(fields: dict, received: datetime) -> str:
    name = " ".join(part for part in (fields["first_name"], fields["last_name"]) if part)
    return (
        "Message from the feedback form on the SmileCard website.\n\n"
        f"Received: {received.strftime('%Y-%m-%d %H:%M')} UTC\n"
        f"Name:  {name}\n"
        f"Email: {fields['email']}\n"
        f"Phone: {fields['phone'] or '(not given)'}\n\n"
        f"Message:\n{fields['message']}\n"
    )


def blob_token(headers, env) -> str:
    """Vercel puts a short-lived OIDC token on each request to a function; a read-write token also works."""
    return (headers.get("x-vercel-oidc-token") or env.get("VERCEL_OIDC_TOKEN")
            or env.get("BLOB_READ_WRITE_TOKEN") or "").strip()


def save_message(fields: dict, store_id: str, token: str, received: datetime | None = None) -> str:
    """Save one message as a private text file; return its name. Raises on any failure."""
    received = received or datetime.now(timezone.utc)
    pathname = f"feedback/{received.strftime('%Y-%m-%d_%H-%M-%S')}_{secrets.token_hex(3)}.txt"
    request = urllib.request.Request(
        BLOB_API + "?" + urllib.parse.urlencode({"pathname": pathname}),
        data=message_text(fields, received).encode("utf-8"),
        method="PUT",
        headers={
            "authorization": f"Bearer {token}",
            "x-vercel-blob-store-id": store_id,
            "x-api-version": "13",
            "x-api-blob-request-id": f"{store_id}:{int(received.timestamp() * 1000)}:{secrets.token_hex(4)}",
            "x-api-blob-request-attempt": "0",
            "x-vercel-blob-access": "private",
            "x-content-type": "text/plain; charset=utf-8",
            "x-add-random-suffix": "0",
            "x-allow-overwrite": "0",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        saved = json.loads(response.read().decode("utf-8") or "{}")
    return saved.get("pathname", pathname)


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


def handle(method: str, headers, body: bytes, client: str, env=None, sender=None, saver=None):
    """Return (status, response dict). Kept apart from the HTTP plumbing so it can be tested directly."""
    env = os.environ if env is None else env
    sender = sender or send_email
    saver = saver or save_message
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
    store_id, token = env.get("BLOB_STORE_ID", "").strip(), blob_token(headers, env)
    email_ready = bool(env.get("SMTP_USER") and env.get("SMTP_APP_PASSWORD"))
    if not (store_id and token) and not email_ready:
        print("feedback: nowhere to deliver (no Blob store connected, no email set up)")
        return 503, {"ok": False, "error": "not_configured"}
    delivered = False
    if store_id and token:
        try:
            saver(fields, store_id, token)
            delivered = True
            print("feedback: message saved")
        except urllib.error.HTTPError as error:
            print(f"feedback: saving failed (HTTP {error.code})")
        except (urllib.error.URLError, OSError, ValueError) as error:
            print(f"feedback: saving failed ({type(error).__name__})")
    if email_ready:
        try:
            sender(build_email(fields, env["SMTP_USER"], env.get("FEEDBACK_TO") or env["SMTP_USER"]), env)
            delivered = True
            print("feedback: message emailed")
        except (smtplib.SMTPException, OSError) as error:
            print(f"feedback: emailing failed ({type(error).__name__})")
    if not delivered:
        return 502, {"ok": False, "error": "send_failed"}
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
