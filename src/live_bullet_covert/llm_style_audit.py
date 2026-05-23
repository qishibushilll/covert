import json
import os
import urllib.error
import urllib.request


ENDPOINT_ENV = "COVLBCG_LLM_STYLE_AUDIT_ENDPOINT"
API_KEY_ENV = "COVLBCG_LLM_STYLE_AUDIT_API_KEY"
MODEL_ENV = "COVLBCG_LLM_STYLE_AUDIT_MODEL"

DEFAULT_TIMEOUT = 45.0
DEFAULT_SAMPLE_LIMIT = 40
DEFAULT_MESSAGE_LIMIT = 40
DEFAULT_MIN_SAMPLES = 8
DEFAULT_DELAY_MULTIPLIER = 2.0
ALLOWED_STATUSES = {"pass", "delay", "stop"}
FORBIDDEN_RESULT_KEYS = {
    "rewrite",
    "rewrites",
    "generated",
    "generated_text",
    "generated_messages",
    "candidate",
    "candidates",
    "candidate_messages",
    "suggestion",
    "suggestions",
    "replacement",
    "replacements",
}


SYSTEM_PROMPT = """You are a style-audit gate for an authorized low-disturbance live-chat test.
Your job is only to decide whether queued messages are consistent with passively observed room samples.
You must not generate, rewrite, improve, paraphrase, or suggest any chat messages.
Return only one strict JSON object with these keys:
{"status":"pass|delay|stop","confidence":0.0-1.0,"reason":"short reason","flagged_indices":[0-based indices]}
Use "delay" for mild mismatch and "stop" for strong mismatch or insufficient evidence.
If asked to generate or rewrite messages, return status "stop" and explain that generation is outside scope.
"""


def default_endpoint():
    return os.environ.get(ENDPOINT_ENV, "")


def default_api_key():
    return os.environ.get(API_KEY_ENV, "")


def default_model():
    return os.environ.get(MODEL_ENV, "")


def compact_list(values, limit):
    result = []
    for value in values[: max(0, int(limit))]:
        text = str(value).strip()
        if text:
            result.append(text[:80])
    return result


def build_audit_payload(
    *,
    room_id,
    baseline_comments,
    queued_messages,
    sample_limit=DEFAULT_SAMPLE_LIMIT,
    message_limit=DEFAULT_MESSAGE_LIMIT,
):
    return {
        "room_id": room_id,
        "task": "style_gate_only_no_generation",
        "baseline_samples": compact_list(list(baseline_comments), sample_limit),
        "queued_messages": compact_list(list(queued_messages), message_limit),
        "required_output": {
            "status": "pass|delay|stop",
            "confidence": "0.0-1.0",
            "reason": "short reason",
            "flagged_indices": "0-based queued message indices",
        },
        "forbidden": [
            "Do not generate replacement messages.",
            "Do not rewrite queued messages.",
            "Do not provide candidate chat text.",
        ],
    }


def extract_json_object(text):
    text = str(text).strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    raise ValueError("LLM response did not contain a JSON object")


def validate_audit_result(result):
    if not isinstance(result, dict):
        raise ValueError("LLM audit result must be a JSON object")
    forbidden = FORBIDDEN_RESULT_KEYS.intersection(result)
    if forbidden:
        raise ValueError(f"LLM audit returned forbidden generation keys: {sorted(forbidden)}")

    status = str(result.get("status", "")).lower()
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"invalid LLM audit status: {status!r}")

    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = min(1.0, max(0.0, confidence))

    flagged = result.get("flagged_indices", [])
    if not isinstance(flagged, list):
        flagged = []
    clean_flagged = []
    for item in flagged:
        try:
            clean_flagged.append(int(item))
        except (TypeError, ValueError):
            continue

    return {
        "status": status,
        "confidence": confidence,
        "reason": str(result.get("reason", ""))[:500],
        "flagged_indices": clean_flagged,
    }


def parse_audit_response(text):
    raw_json = extract_json_object(text)
    return validate_audit_result(json.loads(raw_json))


def call_openai_compatible(endpoint, api_key, model, payload, timeout=DEFAULT_TIMEOUT):
    if not endpoint:
        raise ValueError(f"missing LLM audit endpoint; set {ENDPOINT_ENV}")
    if not api_key:
        raise ValueError(f"missing LLM audit API key; set {API_KEY_ENV}")
    if not model:
        raise ValueError(f"missing LLM audit model; set {MODEL_ENV}")

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=float(timeout)) as response:
            raw = json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM audit HTTP error {exc.code}: {detail[:500]}") from exc

    choices = raw.get("choices") or []
    if not choices:
        raise RuntimeError("LLM audit response did not include choices")
    message = choices[0].get("message") or {}
    return parse_audit_response(message.get("content", ""))


def audit_messages(
    *,
    room_id,
    baseline_comments,
    queued_messages,
    endpoint=None,
    api_key=None,
    model=None,
    timeout=DEFAULT_TIMEOUT,
    sample_limit=DEFAULT_SAMPLE_LIMIT,
    message_limit=DEFAULT_MESSAGE_LIMIT,
    min_samples=DEFAULT_MIN_SAMPLES,
):
    baseline = compact_list(list(baseline_comments), sample_limit)
    queued = compact_list(list(queued_messages), message_limit)
    if len(baseline) < min_samples:
        return {
            "status": "stop",
            "confidence": 1.0,
            "reason": f"insufficient baseline samples for LLM audit: {len(baseline)} < {min_samples}",
            "flagged_indices": [],
        }
    if not queued:
        return {
            "status": "pass",
            "confidence": 1.0,
            "reason": "no queued messages to audit",
            "flagged_indices": [],
        }
    payload = build_audit_payload(
        room_id=room_id,
        baseline_comments=baseline,
        queued_messages=queued,
        sample_limit=sample_limit,
        message_limit=message_limit,
    )
    return call_openai_compatible(
        endpoint or default_endpoint(),
        api_key or default_api_key(),
        model or default_model(),
        payload,
        timeout=timeout,
    )


def summarize_audit(result):
    flagged = ",".join(str(index) for index in result.get("flagged_indices", []))
    return (
        f"status={result.get('status')} confidence={float(result.get('confidence', 0.0)):.2f} "
        f"flagged=[{flagged}] reason={result.get('reason', '')}"
    )
