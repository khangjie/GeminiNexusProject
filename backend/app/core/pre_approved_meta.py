import json
from typing import Any

_PRE_APPROVED_META_PREFIX = "__NEXUS_PREAPPROVED_META__:"


def encode_pre_approved_meta(note: str | None, custom_variables: dict[str, str] | None) -> str | None:
    cleaned_note = (note or "").strip() or None
    cleaned_vars = {str(k): str(v) for k, v in (custom_variables or {}).items() if str(k).strip()}

    if not cleaned_vars:
        return cleaned_note

    payload = {
        "note": cleaned_note,
        "custom_variables": cleaned_vars,
    }
    return f"{_PRE_APPROVED_META_PREFIX}{json.dumps(payload, ensure_ascii=True)}"


def decode_pre_approved_meta(stored_note: str | None) -> tuple[str | None, dict[str, str]]:
    if not stored_note:
        return None, {}

    if not stored_note.startswith(_PRE_APPROVED_META_PREFIX):
        return stored_note, {}

    raw = stored_note[len(_PRE_APPROVED_META_PREFIX):]
    try:
        payload = json.loads(raw)
    except Exception:
        return stored_note, {}

    note = payload.get("note")
    raw_vars: Any = payload.get("custom_variables")

    if not isinstance(raw_vars, dict):
        return (note if isinstance(note, str) or note is None else str(note)), {}

    parsed_vars: dict[str, str] = {}
    for key, value in raw_vars.items():
        key_str = str(key).strip()
        if not key_str:
            continue
        parsed_vars[key_str] = "" if value is None else str(value)

    normalized_note = note if isinstance(note, str) or note is None else str(note)
    return normalized_note, parsed_vars
