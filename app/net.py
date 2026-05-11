"""Network client helpers for TLS settings."""
from __future__ import annotations

import os


def tls_verify_enabled() -> bool:
    raw = os.getenv("PAPERWEB_TLS_VERIFY", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}
