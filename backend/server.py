"""
Vibe Protect — backend API.

- POST /api/redact         run redaction server-side, returns matches + cleaned
- GET  /api/patterns       list all available patterns with examples
- POST /api/track          record an anonymous redaction event (used by CLI/ext)
- GET  /api/stats          aggregate counts used by the dashboard
- GET  /api/feed           last N anonymized events for the live ticker
"""

from __future__ import annotations

import os
import re
import sys
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict
from dotenv import load_dotenv

# --- load shared pattern library from ../cli/patterns.py ---------------------
ROOT_DIR = Path(__file__).parent
REPO_ROOT = ROOT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "cli"))

from patterns import PATTERNS as _PATTERNS_DEF, redact as _redact, UNION  # noqa: E402
from updater import check_for_update, current_version  # noqa: E402

load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Vibe Protect API")
api = APIRouter(prefix="/api")


# ---- models ----------------------------------------------------------------
class RedactRequest(BaseModel):
    text: str


class Match(BaseModel):
    pattern: str
    original_len: int
    start: int
    end: int
    mask: str


class RedactResponse(BaseModel):
    cleaned: str
    matches: List[Match]
    chars_before: int
    chars_after: int


class Pattern(BaseModel):
    name: str
    regex: str
    description: str
    example: str


class TrackEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source: str = Field(default="web")  # web / cli / desktop / extension
    patterns: List[str] = Field(default_factory=list)
    chars_before: int = 0
    chars_after: int = 0


class FeedItem(BaseModel):
    id: str
    ts: datetime
    source: str
    patterns: List[str]
    chars_saved: int


class Stats(BaseModel):
    total_events: int
    total_secrets: int
    total_chars_scrubbed: int
    patterns_active: int
    events_last_24h: int


# ---- endpoints -------------------------------------------------------------
@api.get("/")
async def root():
    return {"service": "vibe-protect", "status": "armed", "patterns": len(_PATTERNS_DEF), "version": current_version()}


@api.get("/version")
async def version_endpoint():
    info = check_for_update(force=False)
    return info.to_dict()


@api.get("/patterns", response_model=List[Pattern])
async def list_patterns():
    return [
        Pattern(name=n, regex=p, description=d, example=ex)
        for n, p, d, ex in _PATTERNS_DEF
    ]


@api.post("/redact", response_model=RedactResponse)
async def redact_endpoint(body: RedactRequest):
    if body.text is None:
        raise HTTPException(400, "text is required")
    cleaned, matches = _redact(body.text)
    evt_patterns = [m["pattern"] for m in matches]
    chars_saved = max(0, len(body.text) - len(cleaned))

    # auto-track non-trivial redactions to power the live feed & stats
    if matches:
        doc = {
            "id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": "web",
            "patterns": evt_patterns,
            "chars_before": len(body.text),
            "chars_after": len(cleaned),
            "chars_saved": chars_saved,
        }
        try:
            await db.vp_events.insert_one(doc)
        except Exception:
            pass  # never fail the redaction because of a storage hiccup

    return RedactResponse(
        cleaned=cleaned,
        matches=[Match(**m) for m in matches],
        chars_before=len(body.text),
        chars_after=len(cleaned),
    )


@api.post("/track")
async def track(evt: TrackEvent):
    source = evt.source if evt.source in {"web", "cli", "desktop", "extension"} else "other"
    chars_saved = max(0, evt.chars_before - evt.chars_after)
    doc = {
        "id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "patterns": evt.patterns[:20],
        "chars_before": evt.chars_before,
        "chars_after": evt.chars_after,
        "chars_saved": chars_saved,
    }
    await db.vp_events.insert_one(doc)
    return {"ok": True, "id": doc["id"]}


@api.get("/feed", response_model=List[FeedItem])
async def feed(limit: int = 30):
    limit = max(1, min(limit, 100))
    cursor = db.vp_events.find({}, {"_id": 0}).sort("ts", -1).limit(limit)
    out: List[FeedItem] = []
    async for doc in cursor:
        ts = doc.get("ts")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        out.append(
            FeedItem(
                id=doc.get("id", str(uuid.uuid4())),
                ts=ts,
                source=doc.get("source", "web"),
                patterns=doc.get("patterns", []),
                chars_saved=doc.get("chars_saved", 0),
            )
        )
    return out


@api.get("/stats", response_model=Stats)
async def stats():
    # aggregate counts
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_events": {"$sum": 1},
                "total_secrets": {"$sum": {"$size": "$patterns"}},
                "total_chars": {"$sum": "$chars_saved"},
            }
        }
    ]
    agg = await db.vp_events.aggregate(pipeline).to_list(1)
    if agg:
        a = agg[0]
        total_events = int(a.get("total_events", 0))
        total_secrets = int(a.get("total_secrets", 0))
        total_chars = int(a.get("total_chars", 0))
    else:
        total_events = total_secrets = total_chars = 0

    from datetime import timedelta

    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    last_24h = await db.vp_events.count_documents({"ts": {"$gte": since}})

    return Stats(
        total_events=total_events,
        total_secrets=total_secrets,
        total_chars_scrubbed=total_chars,
        patterns_active=len(_PATTERNS_DEF),
        events_last_24h=last_24h,
    )


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("vibe-protect")


@app.on_event("shutdown")
async def _shutdown():
    client.close()
