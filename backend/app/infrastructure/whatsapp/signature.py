import hashlib
import hmac


def compute_signature(app_secret: str, raw_body: bytes) -> str:
    return "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()


def verify_signature(app_secret: str, raw_body: bytes, header_value: str | None) -> bool:
    """Validate X-Hub-Signature-256 against the exact raw request body."""
    if not app_secret or not header_value or not header_value.startswith("sha256="):
        return False
    return hmac.compare_digest(compute_signature(app_secret, raw_body), header_value.strip())
