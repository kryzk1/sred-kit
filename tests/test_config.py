from datetime import date, datetime, timezone

import pytest

from sredlib import config


def test_fiscal_year_reads_toml_dates(make_claim):
    cfg = config.load_config(make_claim() / "sred.toml")
    assert config.fiscal_year(cfg) == (date(2026, 8, 1), date(2027, 7, 31))


def test_fiscal_year_rejects_quoted_dates(tmp_path):
    (tmp_path / "sred.toml").write_text('[fiscal_year]\nstart = "2026-08-01"\nend = "2027-07-31"\n')
    cfg = config.load_config(tmp_path / "sred.toml")
    with pytest.raises(config.ConfigError, match="TOML dates"):
        config.fiscal_year(cfg)


def test_limits_default_to_form_word_maximums(make_claim):
    lim = config.limits(config.load_config(make_claim() / "sred.toml"))
    assert lim["mode"] == "words"
    assert lim["words"] == {"242": 350, "244": 700, "246": 350}
    assert lim["lines"] == {"242": 50, "244": 100, "246": 50}
    assert lim["line_width"] == 78


def test_limits_override_mode_and_values(make_claim):
    claim = make_claim('[limits]\nmode = "lines"\n[limits.lines]\n244 = 90\n')
    lim = config.limits(config.load_config(claim / "sred.toml"))
    assert lim["mode"] == "lines" and lim["lines"]["244"] == 90 and lim["lines"]["242"] == 50


def test_source_lookup_and_issue_regexes(make_claim):
    claim = make_claim("""
[[sources]]
name = "jira"
kind = "tracker"
tool = "jira"
method = "export"
issue_key_regex = '[A-Z]+-\\d+'
""")
    cfg = config.load_config(claim / "sred.toml")
    assert config.source(cfg, "jira")["tool"] == "jira"
    assert config.issue_key_regexes(cfg) == [r"[A-Z]+-\d+"]
    with pytest.raises(config.ConfigError):
        config.source(cfg, "nope")


def test_timezone_defaults_to_utc_and_rejects_unknown(make_claim, tmp_path):
    cfg = config.load_config(make_claim() / "sred.toml")
    assert config.timezone_of(cfg) == timezone.utc
    cfg["company"]["timezone"] = "America/Vancouver"
    late = datetime(2027, 8, 1, 5, tzinfo=timezone.utc)
    assert late.astimezone(config.timezone_of(cfg)).date() == date(2027, 7, 31)
    cfg["company"]["timezone"] = "Mars/Olympus"
    with pytest.raises(config.ConfigError, match="time zone"):
        config.timezone_of(cfg)


def test_classification_rates_and_kind_weights(make_claim):
    claim = make_claim("""
[classification]
review_threshold = 0.8
[[classification.rules]]
id = "r1"
project = "P1"
level = "direct"
[rates]
itc_rate = 0.35
[time_basis.kind_weights]
chat_message = 0.5
""")
    cfg = config.load_config(claim / "sred.toml")
    assert config.classification(cfg) == {"review_threshold": 0.8, "rules": [{"id": "r1", "project": "P1", "level": "direct"}]}
    assert config.rates(cfg) == {"itc_rate": 0.35}
    assert config.kind_weights(cfg) == {"chat_message": 0.5}
    assert config.resolve_path(cfg, "prior/a.pdf") == claim / "prior/a.pdf"


def test_blank_limits_mode_falls_back_to_words(make_claim):
    lim = config.limits(config.load_config(make_claim('[limits]\nmode = ""\n') / "sred.toml"))
    assert lim["mode"] == "words"
