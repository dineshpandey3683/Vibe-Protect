"""Backend API tests for Vibe Protect."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fall back to reading frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                break

API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- basic ----------
class TestBasics:
    def test_root(self, client):
        r = client.get(f"{API}/")
        assert r.status_code == 200
        d = r.json()
        assert d.get("status") == "armed"
        assert d.get("patterns") == 18
        assert d.get("service") == "vibe-protect"

    def test_patterns(self, client):
        r = client.get(f"{API}/patterns")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 18
        for p in data:
            for k in ("name", "regex", "description", "example"):
                assert k in p and isinstance(p[k], str) and p[k]


# ---------- redaction ----------
class TestRedact:
    def test_redact_openai_and_github(self, client):
        text = (
            "my key is sk-proj-abcd1234efgh5678ijkl9012mnop3456 "
            "and token ghp_1234567890abcdefghijklmnopqrstuvwxyz12 end"
        )
        r = client.post(f"{API}/redact", json={"text": text})
        assert r.status_code == 200
        d = r.json()
        assert "[OPENAI_API_KEY]" in d["cleaned"]
        assert "[GITHUB_TOKEN]" in d["cleaned"]
        assert len(d["matches"]) == 2
        kinds = {m["pattern"] for m in d["matches"]}
        assert "openai_api_key" in kinds
        assert "github_token" in kinds
        assert d["chars_before"] == len(text)
        assert d["chars_after"] == len(d["cleaned"])
        assert d["chars_after"] < d["chars_before"]

    def test_redact_plain(self, client):
        r = client.post(f"{API}/redact", json={"text": "hello world"})
        assert r.status_code == 200
        d = r.json()
        assert d["cleaned"] == "hello world"
        assert d["matches"] == []
        assert d["chars_before"] == 11 and d["chars_after"] == 11

    def test_redact_env_blob(self, client):
        env_blob = """
OPENAI_API_KEY=sk-proj-AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH1234
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz0123456789ab
DATABASE_URL=postgresql://admin:s3cr3t@db.example.com:5432/prod
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_KEY=sk_live_51HqABCDEFghijklmnopqrstuvwxyz
JWT=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcXYZdef123
EMAIL=alice@example.com
SERVER=192.168.1.42
"""
        r = client.post(f"{API}/redact", json={"text": env_blob})
        assert r.status_code == 200
        d = r.json()
        cleaned = d["cleaned"]
        # No plaintext secret values
        secrets = [
            "sk-proj-AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH1234",
            "AKIAIOSFODNN7EXAMPLE",
            "ghp_abcdefghijklmnopqrstuvwxyz0123456789ab",
            "admin:s3cr3t",
            "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxx",
            "sk_live_51HqABCDEFghijklmnopqrstuvwxyz",
            "alice@example.com",
            "192.168.1.42",
        ]
        for s in secrets:
            assert s not in cleaned, f"Secret leaked: {s}"
        kinds = {m["pattern"] for m in d["matches"]}
        expected = {
            "openai_api_key", "aws_access_key", "github_token",
            "db_connection_string", "anthropic_api_key", "stripe_key",
            "jwt_token", "email", "ipv4",
        }
        missing = expected - kinds
        assert not missing, f"Missing pattern types: {missing}"


# ---------- track / stats / feed ----------
class TestTrackStatsFeed:
    def test_track_returns_ok(self, client):
        r = client.post(f"{API}/track", json={
            "source": "cli",
            "patterns": ["email"],
            "chars_before": 50,
            "chars_after": 30,
        })
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True
        assert isinstance(d.get("id"), str) and len(d["id"]) > 0

    def test_stats_shape_and_growth(self, client):
        before = client.get(f"{API}/stats").json()
        for k in ("total_events", "total_secrets", "total_chars_scrubbed",
                  "patterns_active", "events_last_24h"):
            assert k in before and isinstance(before[k], int)
        assert before["patterns_active"] == 18

        # trigger an event
        client.post(f"{API}/track", json={
            "source": "cli", "patterns": ["email", "ipv4"],
            "chars_before": 200, "chars_after": 50,
        })
        after = client.get(f"{API}/stats").json()
        assert after["total_events"] >= before["total_events"] + 1
        assert after["total_secrets"] >= before["total_secrets"] + 2
        assert after["total_chars_scrubbed"] >= before["total_chars_scrubbed"] + 150

    def test_feed_shape(self, client):
        r = client.get(f"{API}/feed", params={"limit": 10})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) <= 10
        if data:
            for item in data:
                for k in ("id", "ts", "source", "patterns", "chars_saved"):
                    assert k in item
                assert isinstance(item["patterns"], list)
                assert isinstance(item["chars_saved"], int)
            # most recent first
            ts_list = [item["ts"] for item in data]
            assert ts_list == sorted(ts_list, reverse=True)
