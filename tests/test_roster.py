from sredlib.roster import Resolver, load_roster, parse_aliases

ROSTER = [
    {"id": "alice", "name": "Alice Chen", "aliases": "github:achen;slack:U01;email:alice@acme.test"},
    {"id": "bob", "name": "Bob Roy", "aliases": "jira:5b10ac;email:bob@acme.test"},
]


def test_parse_aliases_lowercases_and_skips_junk():
    assert parse_aliases("GitHub:AChen; nonsense ;email:A@x.io") == [("github", "achen"), ("email", "a@x.io")]


def test_resolve_by_tool_alias_email_name_and_angle_form():
    r = Resolver(ROSTER)
    assert r.resolve("github", "AChen") == "alice"
    assert r.resolve("git", "whoever", email="ALICE@acme.test") == "alice"
    assert r.resolve("linear", "u-123", name="Bob Roy") == "bob"
    assert r.resolve("azure-devops", "Bob Roy <bob@acme.test>") == "bob"


def test_bots_and_unmatched():
    r = Resolver(ROSTER, extra_bots=["build-robot"])
    assert r.resolve("github", "dependabot[bot]") == "bot"
    assert r.resolve("github", "build-robot") == "bot"
    assert r.resolve("github", "stranger") == "unmatched:stranger"
    assert r.resolve("github", "") == "unmatched:"


def test_load_roster_fills_missing_columns(tmp_path):
    (tmp_path / "roster.csv").write_text("id,name\nalice, Alice Chen \n")
    rows = load_roster(tmp_path / "roster.csv")
    assert rows[0]["name"] == "Alice Chen" and rows[0]["wages_earned"] == ""
