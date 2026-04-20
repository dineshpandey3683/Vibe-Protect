"""
Vibe Protect — production updater.

Checks the configured GitHub repo's latest release and tells the user when a
newer version is available. Shared by the CLI and the desktop GUI.

Design choices
--------------
* **Never auto-execute downloaded binaries.** Silently running an installer
  from a release asset would be a footgun for a security tool. Instead, we
  surface the release URL + assets and let the user review/install.
* **Throttled.** We cache the last-check timestamp to `~/.vibeprotect/last_check`
  and skip the network call if we checked within the last 6 hours.
* **Optional.** All network calls live in this module; the rest of the app
  works offline. A `VP_DISABLE_UPDATE_CHECK=1` env var fully opts out.
* **No hard dependency on `packaging`.** We implement a lenient
  semver-ish comparator so the updater works on minimal installs.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
_CACHE_DIR = Path(os.environ.get("VP_CACHE_DIR") or Path.home() / ".vibeprotect")
_CACHE_FILE = _CACHE_DIR / "last_check.json"

DEFAULT_REPO_API = os.environ.get(
    "VP_UPDATE_URL",
    "https://api.github.com/repos/vibeprotect/vibe-protect/releases/latest",
)
THROTTLE_SECONDS = 6 * 60 * 60  # 6 hours
REQUEST_TIMEOUT = 6.0


def current_version() -> str:
    """Read the repo-level VERSION file (falls back to 0.0.0)."""
    p = _REPO_ROOT / "VERSION"
    if p.exists():
        try:
            return p.read_text().strip() or "0.0.0"
        except OSError:
            pass
    return "0.0.0"


def _tuple(v: str):
    """Lenient semver tuple — drops leading 'v', ignores trailing pre-release."""
    v = v.lstrip("vV").split("-")[0].split("+")[0]
    parts = re.findall(r"\d+", v)
    nums = [int(x) for x in parts[:3]] + [0, 0, 0]
    return tuple(nums[:3])


def is_newer(latest: str, current: str) -> bool:
    return _tuple(latest) > _tuple(current)


@dataclass
class UpdateInfo:
    current: str
    latest: str
    is_update_available: bool
    release_url: str = ""
    release_name: str = ""
    published_at: str = ""
    assets: Optional[List[dict]] = None
    error: str = ""

    def to_dict(self):
        return asdict(self)


def _read_cache() -> Optional[UpdateInfo]:
    try:
        if not _CACHE_FILE.exists():
            return None
        data = json.loads(_CACHE_FILE.read_text())
        if time.time() - data.get("_cached_at", 0) > THROTTLE_SECONDS:
            return None
        data.pop("_cached_at", None)
        return UpdateInfo(**data)
    except Exception:
        return None


def _write_cache(info: UpdateInfo) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = info.to_dict()
        payload["_cached_at"] = time.time()
        _CACHE_FILE.write_text(json.dumps(payload))
    except OSError:
        pass  # cache is best-effort


def check_for_update(force: bool = False, repo_api: str = DEFAULT_REPO_API) -> UpdateInfo:
    """Return update info. Uses throttled cache unless `force=True`.

    Respects `VP_DISABLE_UPDATE_CHECK=1` — returns a no-op UpdateInfo.
    """
    current = current_version()

    if os.environ.get("VP_DISABLE_UPDATE_CHECK") == "1":
        return UpdateInfo(current=current, latest=current, is_update_available=False)

    if not force:
        cached = _read_cache()
        if cached is not None:
            return cached

    try:
        req = urllib.request.Request(
            repo_api,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"vibe-protect/{current}",
            },
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return UpdateInfo(current=current, latest=current, is_update_available=False, error=f"HTTP {e.code}")
    except Exception as e:
        return UpdateInfo(current=current, latest=current, is_update_available=False, error=str(e))

    latest_tag = (data.get("tag_name") or "").lstrip("vV") or current
    info = UpdateInfo(
        current=current,
        latest=latest_tag,
        is_update_available=is_newer(latest_tag, current),
        release_url=data.get("html_url", ""),
        release_name=data.get("name") or data.get("tag_name") or "",
        published_at=data.get("published_at", ""),
        assets=[
            {"name": a.get("name"), "url": a.get("browser_download_url"), "size": a.get("size")}
            for a in (data.get("assets") or [])
        ],
    )
    _write_cache(info)
    return info


def print_update_banner(info: UpdateInfo) -> None:
    """Pretty print an update banner to the terminal (ANSI)."""
    amber = "\033[38;5;220m"
    dim = "\033[2m"
    reset = "\033[0m"
    if info.error:
        print(f"{dim}  (update check skipped: {info.error}){reset}")
        return
    if not info.is_update_available:
        print(f"{dim}  ● v{info.current} · up to date{reset}")
        return
    print(f"{amber}  ▲ update available: {info.current} → {info.latest}{reset}")
    if info.release_name:
        print(f"{dim}    {info.release_name}{reset}")
    if info.release_url:
        print(f"{dim}    release notes: {info.release_url}{reset}")
    print(f"{dim}    upgrade with:  pip install --upgrade vibe-protect{reset}")
    print(f"{dim}    or inspect assets in the release page before installing.{reset}")


if __name__ == "__main__":
    info = check_for_update(force=True)
    print(json.dumps(info.to_dict(), indent=2))
