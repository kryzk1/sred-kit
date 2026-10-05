import csv
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

BASE_TOML = """
[company]
name = "Acme Robotics Inc."

[fiscal_year]
start = 2026-08-01
end = 2027-07-31
"""


class FakeHttp:
    """Answers requests from canned routes: (method, url_prefix, payload, headers).

    The first route whose method matches and whose prefix starts the URL wins, so list
    more specific prefixes first. A callable payload receives the request body.
    """

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def request(self, method, url, headers=None, body=None):
        self.calls.append((method, url, body))
        for m, prefix, payload, hdrs in self.routes:
            if m == method and url.startswith(prefix):
                data = payload(body) if callable(payload) else payload
                return data, {k.lower(): v for k, v in (hdrs or {}).items()}
        raise AssertionError(f"unexpected request {method} {url}")

    def get(self, url, headers=None):
        return self.request("GET", url, headers)

    def post(self, url, body, headers=None):
        return self.request("POST", url, headers, body)


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def fake_http():
    return FakeHttp


@pytest.fixture
def make_claim(tmp_path):
    def _make(extra_toml: str = "", roster=None) -> Path:
        (tmp_path / "sred.toml").write_text(BASE_TOML + extra_toml, encoding="utf-8")
        if roster is not None:
            from sredlib.roster import ROSTER_COLUMNS

            with (tmp_path / "roster.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=ROSTER_COLUMNS, lineterminator="\n")
                writer.writeheader()
                for row in roster:
                    writer.writerow({c: row.get(c, "") for c in ROSTER_COLUMNS})
        return tmp_path

    return _make
