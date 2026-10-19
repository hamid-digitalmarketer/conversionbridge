"""Secret redaction, hashing utilities, and privacy protections."""

import hashlib
import re
from typing import Any

# Match standard SHA-256 hex string (64 lowercase hex digits)
_SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")

# Keys that must be masked or redacted in logs and diagnostic outputs
_SENSITIVE_KEYS = {
    "access_token",
    "api_secret",
    "api_key",
    "password",
    "secret",
    "token",
    "authorization",
    "email",
    "phone",
    "first_name",
    "last_name",
    "client_ip_address",
}


def hash_sha256(val: str) -> str:
    """Normalize and hash string with SHA-256 per Meta & Google measurement standards.

    If the string is already a valid 64-character hex SHA-256 digest, returns it directly
    to avoid double-hashing.
    """
    if not val:
        return ""
    clean = val.strip().lower()
    if _SHA256_HEX_RE.match(clean):
        return clean
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


def mask_secret(val: str, keep_start: int = 3, keep_end: int = 3) -> str:
    """Mask a secret string for safe display in logs or status endpoints."""
    if not val:
        return ""
    length = len(val)
    if length <= (keep_start + keep_end):
        return "***"
    return f"{val[:keep_start]}***{val[-keep_end:]}"


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact sensitive keys from a dictionary for safe logging/inspection."""
    redacted = {}
    for k, v in data.items():
        k_lower = k.lower()
        if any(s in k_lower for s in _SENSITIVE_KEYS):
            if isinstance(v, str):
                redacted[k] = mask_secret(v)
            else:
                redacted[k] = "[REDACTED]"
        elif isinstance(v, dict):
            redacted[k] = redact_dict(v)
        elif isinstance(v, list):
            redacted[k] = [redact_dict(item) if isinstance(item, dict) else item for item in v]
        else:
            redacted[k] = v
    return redacted
