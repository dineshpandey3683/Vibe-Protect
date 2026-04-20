# syntax=docker/dockerfile:1.6
# ---------------------------------------------------------------------------
# Vibe Protect — CLI image
#
# Designed to be tiny (only the CLI + core detection modules ship inside the
# container — no frontend, no desktop, no browser extension) so it's quick
# to pull in CI pipelines and doesn't leak irrelevant attack surface.
#
# Build:
#     docker build -t vibeprotect/vibe-protect:1.0.0 -t vibeprotect/vibe-protect:latest .
#
# Scan a single file (mount your workspace at /scan):
#     docker run --rm -v $(pwd):/scan vibeprotect/vibe-protect \
#         --file /scan/.env --json
#
# Scan from stdin:
#     cat config.py | docker run --rm -i vibeprotect/vibe-protect \
#         --file - --json
#
# GitHub Actions (see .github/workflows/example-scan.yml):
#     - uses: docker://vibeprotect/vibe-protect:latest
#       with:
#         args: --file .env --json
# ---------------------------------------------------------------------------

# ---------- stage 1: builder ------------------------------------------------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Copy only what the wheel actually needs. Everything else (frontend/,
# desktop/, extension/, vscode-extension/, docs/, etc.) is excluded via
# .dockerignore so the build context stays small.
COPY pyproject.toml README.md LICENSE ./
COPY cli/ ./cli/

RUN pip install --upgrade pip build && \
    python -m build --wheel --outdir /wheels

# ---------- stage 2: runtime ------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Run as a non-root user so a compromised scan can't escalate inside the
# container. /scan is left owned by root:root because the host mount
# controls permissions — we just need the process to be able to read it.
RUN useradd --create-home --shell /bin/sh --uid 1001 vibe

COPY --from=builder /wheels/*.whl /tmp/

RUN pip install /tmp/*.whl && rm -f /tmp/*.whl

USER vibe
WORKDIR /scan

ENTRYPOINT ["vibe-protect"]
# Sensible default: emit JSON against stdin if no args are supplied (great
# for `cat file | docker run -i vibeprotect/vibe-protect`).
CMD ["--file", "-", "--json"]

LABEL org.opencontainers.image.title="Vibe Protect" \
      org.opencontainers.image.description="Clipboard guardian — auto-redacts API keys, tokens, and PII before they leak into AI chats, logs, or git." \
      org.opencontainers.image.url="https://github.com/vibeprotect/vibe-protect" \
      org.opencontainers.image.source="https://github.com/vibeprotect/vibe-protect" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="1.0.0"
