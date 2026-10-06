import io
import urllib.error

import pytest

from sredlib.http import Http, HttpError


class Resp:
    def __init__(self, body, headers=None):
        self.body, self.headers = body, headers or {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_retries_rate_limit_then_succeeds(monkeypatch):
    calls, slept = [], []

    def fake_urlopen(req, timeout):
        calls.append(req.full_url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 403, "rate limited", {"X-RateLimit-Remaining": "0", "Retry-After": "3"}, io.BytesIO(b""))
        return Resp(b'{"ok": true}', {"Link": "x"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    data, headers = Http(sleep=slept.append).get("https://api.example/x")
    assert data == {"ok": True} and headers == {"link": "x"} and slept == [3.0] and len(calls) == 2


def test_http_error_carries_status_and_body(monkeypatch):
    def fake_urlopen(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "no", {}, io.BytesIO(b"bad token"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(HttpError, match="HTTP 401: bad token"):
        Http(sleep=lambda s: None).get("https://api.example/x")


@pytest.mark.parametrize("error", [ConnectionResetError(54, "Connection reset by peer"), TimeoutError("read timed out")])
def test_transient_network_errors_are_retried(monkeypatch, error):
    calls, slept = [], []

    def fake_urlopen(req, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise error
        return Resp(b"[]")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert Http(sleep=slept.append).get("https://api.github.com/x")[0] == [] and len(calls) == 2 and slept
