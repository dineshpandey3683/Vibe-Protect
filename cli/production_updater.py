"""
Vibe Protect — ProductionUpdater.

A class-based façade around `updater.check_for_update` that matches the
canonical snippet API:

    from production_updater import ProductionUpdater
    updater = ProductionUpdater()
    updater.check_for_update()

Safety notes (see also updater.py):
* We **do not** auto-download or execute release binaries. For a security tool,
  silently running an installer from the internet is a footgun. Instead we
  tell the user about the update, show the release URL, and let them install
  it themselves.
* Calls are throttled (6h) and fully opt-out via `VP_DISABLE_UPDATE_CHECK=1`.
"""

from __future__ import annotations

from typing import Callable, Optional

from updater import (
    check_for_update as _raw_check,
    current_version,
    print_update_banner,
    DEFAULT_REPO_API,
    UpdateInfo,
)


class ProductionUpdater:
    """Check GitHub for a newer release of Vibe Protect.

    Parameters
    ----------
    repo_url : str, optional
        GitHub releases API URL. Defaults to the project's configured repo
        (overridable via `VP_UPDATE_URL` env var).
    on_update : Callable[[UpdateInfo], None], optional
        Called when an update is available. Use this to show a GUI toast,
        open a menu badge, etc. If omitted, prints a terminal banner.
    force : bool
        Bypass the on-disk throttle cache (useful for a manual "check now"
        button). Defaults to False.
    """

    def __init__(
        self,
        repo_url: str = DEFAULT_REPO_API,
        on_update: Optional[Callable[[UpdateInfo], None]] = None,
        force: bool = False,
    ) -> None:
        self.repo_url = repo_url
        self.current_version = current_version()
        self.force = force
        self.on_update = on_update
        self.last_info: Optional[UpdateInfo] = None

    # --- public API ---------------------------------------------------------
    def check_for_update(self) -> UpdateInfo:
        info = _raw_check(force=self.force, repo_api=self.repo_url)
        self.last_info = info
        if self.on_update is not None:
            try:
                self.on_update(info)
            except Exception:
                # never let a user-supplied callback crash the updater
                pass
        else:
            print_update_banner(info)
        return info

    # --- convenience helpers ------------------------------------------------
    @property
    def is_update_available(self) -> bool:
        return bool(self.last_info and self.last_info.is_update_available)

    @property
    def latest_version(self) -> str:
        return (self.last_info.latest if self.last_info else self.current_version)

    @property
    def release_url(self) -> str:
        return (self.last_info.release_url if self.last_info else "")


__all__ = ["ProductionUpdater", "UpdateInfo"]
