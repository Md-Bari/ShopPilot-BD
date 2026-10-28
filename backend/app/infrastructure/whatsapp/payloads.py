"""Builders for WhatsApp Cloud API `/messages` request bodies."""


def build_text_payload(to_wa_id: str, body: str, *, preview_url: bool = False) -> dict:
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_wa_id,
        "type": "text",
        "text": {"preview_url": preview_url, "body": body},
    }


def build_template_payload(to_wa_id: str, name: str, language: str, body_parameters: list[str] | None = None) -> dict:
    template: dict = {"name": name, "language": {"code": language}}
    if body_parameters:
        template["components"] = [
            {"type": "body", "parameters": [{"type": "text", "text": str(p)} for p in body_parameters]}
        ]
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_wa_id,
        "type": "template",
        "template": template,
    }
