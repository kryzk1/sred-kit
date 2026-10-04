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
                body = exc.read() or b""
                remaining, retry_after = exc.headers.get("X-RateLimit-Remaining"), exc.headers.get("Retry-After")
                secondary = exc.code == 403 and (bool(retry_after) or b"secondary rate limit" in body.lower())
                limited = exc.code == 429 or (exc.code == 403 and remaining == "0") or secondary
                if (limited or exc.code in (502, 503, 504)) and attempt < 5:
                    reset = exc.headers.get("X-RateLimit-Reset")
                    if retry_after:
                        wait = float(retry_after)
                    elif remaining == "0" and reset:
                        wait = max(float(reset) - time.time(), 1.0)
                    else:
                        wait = 60.0 if secondary else 2.0 ** attempt  # GitHub asks for at least a minute on secondary limits
                    self.sleep(min(wait, 900.0))
                    continue
                raise HttpError(f"{method} {url} -> HTTP {exc.code}: {body.decode(errors='replace')[:500]}") from exc
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
