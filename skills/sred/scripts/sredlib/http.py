"""Minimal JSON-over-HTTP client with retries. Tests replace it with a fake."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


class HttpError(RuntimeError):
    pass


class Http:
    def __init__(self, sleep=time.sleep, timeout: int = 60):
        self.sleep = sleep
        self.timeout = timeout

    def request(self, method, url, headers=None, body=None):
        data = json.dumps(body).encode() if body is not None else None
        hdrs = {"Accept": "application/json", "User-Agent": "sred-kit"}
        hdrs.update(headers or {})
        if data is not None:
            hdrs["Content-Type"] = "application/json"
        for attempt in range(6):
            req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    payload = resp.read()
                    return (json.loads(payload) if payload else None), {k.lower(): v for k, v in resp.headers.items()}
            except urllib.error.HTTPError as exc:
                limited = exc.code == 429 or (exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0")
                if (limited or exc.code in (502, 503, 504)) and attempt < 5:
                    reset = exc.headers.get("X-RateLimit-Reset")
                    wait = float(exc.headers.get("Retry-After") or 0) or (max(float(reset) - time.time(), 1.0) if reset else 2.0 ** attempt)
                    self.sleep(min(wait, 900.0))
                    continue
                detail = exc.read().decode(errors="replace")[:500]
                raise HttpError(f"{method} {url} -> HTTP {exc.code}: {detail}") from exc
            except urllib.error.URLError as exc:
                if attempt < 5:
                    self.sleep(2.0 ** attempt)
                    continue
                raise HttpError(f"{method} {url} -> {exc.reason}") from exc
        raise HttpError(f"{method} {url} -> gave up after retries")

    def get(self, url, headers=None):
        return self.request("GET", url, headers)

    def post(self, url, body, headers=None):
        return self.request("POST", url, headers, body)
