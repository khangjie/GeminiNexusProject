import json

_APPROVAL_RULE_META_PREFIX = "__NEXUS_APPROVAL_RULE_META__:"


def encode_approval_rule_prompt(prompt: str, applies_to_preapproved: bool) -> str:
    visible_prompt = prompt.strip()
    payload = {
        "prompt": visible_prompt,
        "applies_to_preapproved": applies_to_preapproved,
    }
    return f"{_APPROVAL_RULE_META_PREFIX}{json.dumps(payload, ensure_ascii=True)}"


def decode_approval_rule_prompt(stored_prompt: str) -> tuple[str, bool]:
    if not stored_prompt.startswith(_APPROVAL_RULE_META_PREFIX):
        return stored_prompt, True

    raw = stored_prompt[len(_APPROVAL_RULE_META_PREFIX):]
    try:
        payload = json.loads(raw)
    except Exception:
        return stored_prompt, True

    prompt = payload.get("prompt")
    applies_to_preapproved = payload.get("applies_to_preapproved")

    normalized_prompt = prompt if isinstance(prompt, str) else stored_prompt
    normalized_applies = applies_to_preapproved if isinstance(applies_to_preapproved, bool) else True
    return normalized_prompt, normalized_applies
