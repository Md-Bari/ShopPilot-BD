"""Phone number normalization. Everything is stored in E.164 (+8801XXXXXXXXX)."""

import phonenumbers

from app.domain.errors import ValidationError

DEFAULT_REGION = "BD"


def normalize_phone(raw: str, region: str = DEFAULT_REGION) -> str:
    """Normalize local or international input ("01712-345678", "+880 1712 345678") to E.164."""
    if raw is None or not str(raw).strip():
        raise ValidationError("Phone number is required.")
    cleaned = str(raw).strip()
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    digits_only = cleaned.replace(" ", "").replace("-", "")
    if digits_only.isdigit() and digits_only.startswith("880"):
        cleaned = "+" + digits_only
    try:
        number = phonenumbers.parse(cleaned, region)
    except phonenumbers.NumberParseException as exc:
        raise ValidationError("Invalid phone number.", details={"phone": raw}) from exc
    if not phonenumbers.is_valid_number(number):
        raise ValidationError("Invalid phone number.", details={"phone": raw})
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def normalize_wa_id(wa_id: str) -> str:
    """WhatsApp ids are international numbers without '+'. Fall back to '+digits' if unparseable."""
    digits = "".join(ch for ch in str(wa_id) if ch.isdigit())
    if not digits:
        raise ValidationError("Invalid WhatsApp id.")
    try:
        return normalize_phone("+" + digits)
    except ValidationError:
        return "+" + digits


def to_wa_id(e164: str) -> str:
    """Format used in the Cloud API `to` field."""
    return e164.lstrip("+")
