"""
Tests for the optional SQLite backend on ``cli/audit_logger.AuditLogger``.

Coverage:
1.  Construct with ``backend="sqlite"`` creates an ``audit.sqlite3`` file
    with the ``audit_events`` table and both indexes.
2.  ``log()`` stores AES-GCM-encrypted rows; plaintext is NEVER visible in
    the DB file.
3.  ``query()`` round-trips encrypted entries and HMAC-verifies them.
4.  ``verify_integrity()`` catches a tampered row (bit-flip on the
    ``encrypted_blob`` column).
5.  SQL-side date-range / event-type filters work.
6.  Flat-file and SQLite backends never interfere with each other.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

CLI_DIR = Path(__file__).resolve().parents[2] / "cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from audit_logger import (   # noqa: E402
    Action,
    AuditLogger,
    BACKEND_FLATFILE,
    BACKEND_SQLITE,
    EventType,
)


@pytest.fixture
def sqlite_logger(tmp_path) -> AuditLogger:
    return AuditLogger(log_dir=tmp_path / "audit", backend=BACKEND_SQLITE)


@pytest.fixture
def flat_logger(tmp_path) -> AuditLogger:
    return AuditLogger(log_dir=tmp_path / "audit-flat", backend=BACKEND_FLATFILE)


# --------------------------------------------------------- setup / schema
class TestSchema:
    def test_backend_rejects_unknown(self, tmp_path):
        with pytest.raises(ValueError):
            AuditLogger(log_dir=tmp_path / "bad", backend="fancyfile")

    def test_sqlite_file_and_table_created(self, sqlite_logger):
        assert sqlite_logger.sqlite_file.exists()
        with sqlite3.connect(str(sqlite_logger.sqlite_file)) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            names = {r[0] for r in rows}
            assert "audit_events" in names
            idx = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            idx_names = {r[0] for r in idx}
            assert "idx_audit_timestamp" in idx_names
            assert "idx_audit_event_type" in idx_names


# ----------------------------------------------------------- encryption
class TestEncryptionAtRest:
    def test_plaintext_never_on_disk(self, sqlite_logger):
        sqlite_logger.log(
            EventType.REDACTION,
            secret_type="openai_api_key",
            action=Action.SCRUBBED,
            metadata={"count": 3, "tag": "super-distinctive-sentinel-xyz"},
        )
        # Checkpoint WAL so all writes are flushed to the main DB file.
        with sqlite3.connect(str(sqlite_logger.sqlite_file)) as conn:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
        # Scan every DB-related artifact — main file, WAL journal, shm file.
        on_disk = b""
        for suffix in ("", "-wal", "-shm", "-journal"):
            p = Path(str(sqlite_logger.sqlite_file) + suffix)
            if p.exists():
                on_disk += p.read_bytes()
        assert b"super-distinctive-sentinel-xyz" not in on_disk, \
            "plaintext metadata leaked into SQLite storage"


# -------------------------------------------------------- round trip
class TestRoundTrip:
    def test_log_then_query_roundtrips(self, sqlite_logger):
        sqlite_logger.log(
            EventType.REDACTION, secret_type="openai_api_key", action=Action.SCRUBBED
        )
        sqlite_logger.log(
            EventType.PAUSE, action=Action.INFO
        )
        results = sqlite_logger.query()
        assert len(results) == 2
        kinds = [e["event_type"] for e in results]
        assert set(kinds) == {"REDACTION", "PAUSE"}

    def test_query_filters_by_event_type(self, sqlite_logger):
        sqlite_logger.log(EventType.REDACTION, action=Action.SCRUBBED)
        sqlite_logger.log(EventType.PAUSE, action=Action.INFO)
        sqlite_logger.log(EventType.RESUME, action=Action.INFO)

        red = sqlite_logger.query(event_type=EventType.REDACTION)
        assert len(red) == 1
        assert red[0]["event_type"] == "REDACTION"

    def test_query_filters_by_date_range(self, sqlite_logger):
        sqlite_logger.log(EventType.STARTUP, action=Action.INFO)
        # Far future window — nothing should be returned
        far = datetime.now(timezone.utc) + timedelta(days=365)
        empty = sqlite_logger.query(start_date=far)
        assert empty == []

        # Wide window — our entry should come back
        wide = datetime.now(timezone.utc) - timedelta(days=1)
        full = sqlite_logger.query(start_date=wide)
        assert any(e["event_type"] == "STARTUP" for e in full)


# --------------------------------------------------------- tamper detect
class TestTamperDetection:
    def test_tampered_row_is_flagged(self, sqlite_logger):
        sqlite_logger.log(EventType.REDACTION, action=Action.SCRUBBED)
        # Corrupt the ciphertext on disk
        with sqlite3.connect(str(sqlite_logger.sqlite_file)) as conn:
            conn.execute(
                "UPDATE audit_events SET encrypted_blob = ? WHERE id = 1",
                ("AAAA" + "B" * 40,),
            )
            conn.commit()
        rep = sqlite_logger.verify_integrity()
        # Either decrypt fails or HMAC fails — either way, tampered.
        assert rep.tampered, "expected tamper detection on corrupted row"


# --------------------------------------------------------- cross-backend
class TestBackendIsolation:
    def test_flatfile_ignored_by_sqlite(self, tmp_path):
        flat = AuditLogger(log_dir=tmp_path / "a", backend=BACKEND_FLATFILE)
        flat.log(EventType.STARTUP, action=Action.INFO)
        # Same dir, different backend → independent storage
        sq = AuditLogger(log_dir=tmp_path / "a", backend=BACKEND_SQLITE)
        # sqlite backend only sees its own table, which is empty
        assert sq.query() == []
        # but flat-file backend still sees its own entry
        assert len(flat.query()) == 1
