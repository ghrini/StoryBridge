"""Tests for the SmileCard feedback function (smilecard-site/api/feedback.py). No email is really sent."""
import importlib.util
import json
import smtplib
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("feedback", Path(__file__).resolve().parents[1] / "api" / "feedback.py")
feedback = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(feedback)

ENV = {"SMTP_USER": "site-sender@example.com", "SMTP_APP_PASSWORD": "not-a-real-password"}
HEADERS = {"Content-Type": "application/json", "Origin": "https://smilecard.example", "Host": "smilecard.example"}
GOOD = {"first_name": "Ana", "last_name": "Lopez", "email": "ana@example.com", "phone": "(555) 010-2000",
        "message": "Thank you for the cards!\nThe residents loved them.", "website": "", "elapsed_ms": 9000}


@pytest.fixture(autouse=True)
def fresh_rate_limit():
    feedback._recent.clear()


def post(data, headers=HEADERS, env=ENV, client="203.0.113.5"):
    sent = []
    body = data if isinstance(data, bytes) else json.dumps(data).encode()
    status, payload = feedback.handle("POST", headers, body, client, env=env, sender=lambda msg, e: sent.append(msg))
    return status, payload, sent


def test_a_good_message_is_emailed_with_reply_to_the_visitor():
    status, payload, sent = post(GOOD)
    assert (status, payload) == (200, {"ok": True})
    [msg] = sent
    assert msg["To"] == "site-sender@example.com"
    assert msg["Reply-To"] == "Ana Lopez <ana@example.com>"
    assert msg["Subject"] == "SmileCard website message from Ana Lopez"
    body = msg.get_content()
    assert "The residents loved them." in body and "(555) 010-2000" in body


def test_feedback_to_overrides_the_inbox():
    _, _, [msg] = post(GOOD, env={**ENV, "FEEDBACK_TO": "team@example.com"})
    assert msg["To"] == "team@example.com"


def test_without_email_settings_it_says_so_and_sends_nothing():
    status, payload, sent = post(GOOD, env={})
    assert (status, payload["error"], sent) == (503, "not_configured", [])


@pytest.mark.parametrize("change", [{"website": "http://spam.example"}, {"elapsed_ms": 500}, {"elapsed_ms": None}])
def test_bots_get_a_quiet_ok_but_nothing_is_sent(change):
    data = {**GOOD, **change}
    if change.get("elapsed_ms", 1) is None:
        del data["elapsed_ms"]
    status, payload, sent = post(data)
    assert (status, payload, sent) == (200, {"ok": True}, [])


@pytest.mark.parametrize("change, field, problem", [
    ({"first_name": " "}, "first_name", "required"),
    ({"email": ""}, "email", "required"),
    ({"email": "not-an-email"}, "email", "invalid"),
    ({"email": "a@b.com, c@d.com"}, "email", "invalid"),
    ({"message": ""}, "message", "required"),
    ({"message": "x" * 5001}, "message", "too_long"),
    ({"phone": "call me <script>"}, "phone", "invalid"),
])
def test_bad_fields_are_named(change, field, problem):
    status, payload, sent = post({**GOOD, **change})
    assert status == 400 and payload["fields"][field] == problem and sent == []


def test_line_breaks_cannot_add_email_headers():
    _, _, [msg] = post({**GOOD, "first_name": "Ana\r\nBcc: victim@example.com", "last_name": "L\nX-Spam: 1"})
    assert msg["Bcc"] is None and msg["X-Spam"] is None
    assert "\n" not in msg["Subject"]


def test_forms_posted_from_another_website_are_refused():
    status, payload, sent = post(GOOD, headers={**HEADERS, "Origin": "https://evil.example"})
    assert (status, payload["error"], sent) == (403, "wrong_site", [])


def test_only_json_posts_are_accepted():
    assert post(GOOD, headers={**HEADERS, "Content-Type": "text/plain"})[0] == 415
    assert post(b"{not json")[0] == 400
    assert post(b"x" * (feedback.MAX_BODY + 1))[0] == 413
    assert feedback.handle("GET", HEADERS, b"", "203.0.113.5", env=ENV)[0] == 405


def test_one_address_can_send_five_messages_in_ten_minutes():
    results = [post(GOOD)[0] for _ in range(6)]
    assert results == [200] * 5 + [429]
    assert post(GOOD, client="198.51.100.7")[0] == 200


def test_an_email_failure_is_reported_not_hidden():
    def broken(msg, env):
        raise smtplib.SMTPAuthenticationError(535, b"bad password")

    status, payload = feedback.handle("POST", HEADERS, json.dumps(GOOD).encode(), "203.0.113.5", env=ENV, sender=broken)
    assert (status, payload["error"]) == (502, "send_failed")


def test_the_vercel_handler_class_over_real_http(monkeypatch):
    sent = []
    monkeypatch.setattr(feedback, "send_email", lambda msg, env: sent.append(msg))
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    server = HTTPServer(("127.0.0.1", 0), feedback.handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/api/feedback"
    try:
        request = urllib.request.Request(url, data=json.dumps(GOOD).encode(), method="POST",
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:
            assert response.status == 200 and json.load(response) == {"ok": True}
            assert response.headers["Cache-Control"] == "no-store"
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(url)
        assert error.value.code == 405 and error.value.headers["Allow"] == "POST"
    finally:
        server.shutdown()
    assert len(sent) == 1 and sent[0]["Reply-To"] == "Ana Lopez <ana@example.com>"
