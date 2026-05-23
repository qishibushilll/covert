import math
import statistics

from live_bullet_covert import room_style


DEFAULT_STYLE_GATE_MAX_Z = 3.0
DEFAULT_STYLE_GATE_MAX_REJECT_RATIO = 0.35
DEFAULT_STYLE_GATE_MIN_SAMPLES = 12
DEFAULT_STYLE_GATE_DELAY_MULTIPLIER = 2.0

FEATURES = (
    "length",
    "punctuation_count",
    "ascii_ratio",
    "digit_ratio",
    "space_count",
)


def text_features(text):
    text = str(text)
    length = len(text)
    ascii_count = sum(1 for char in text if ord(char) < 128)
    digit_count = sum(1 for char in text if char.isdigit())
    return {
        "length": float(length),
        "punctuation_count": float(room_style.punctuation_count(text)),
        "ascii_ratio": ascii_count / max(1, length),
        "digit_ratio": digit_count / max(1, length),
        "space_count": float(text.count(" ")),
    }


def build_style_profile(comments):
    rows = [text_features(comment) for comment in comments if str(comment).strip()]
    summary = {}
    for feature in FEATURES:
        values = [row[feature] for row in rows]
        if not values:
            summary[feature] = {"mean": 0.0, "stdev": 0.0}
            continue
        summary[feature] = {
            "mean": float(statistics.mean(values)),
            "stdev": float(statistics.pstdev(values)),
        }
    return {
        "sample_count": len(rows),
        "features": summary,
    }


def feature_z(value, mean, stdev):
    scale = max(float(stdev), 1.0)
    return abs(float(value) - float(mean)) / scale


def score_text(text, profile):
    row = text_features(text)
    z_by_feature = {}
    for feature in FEATURES:
        stats = profile["features"][feature]
        z_by_feature[feature] = feature_z(row[feature], stats["mean"], stats["stdev"])
    max_feature = max(z_by_feature, key=z_by_feature.get)
    return {
        "text": str(text),
        "features": row,
        "z_by_feature": z_by_feature,
        "max_z": z_by_feature[max_feature],
        "max_feature": max_feature,
    }


def evaluate_messages(
    messages,
    baseline_comments,
    *,
    max_z=DEFAULT_STYLE_GATE_MAX_Z,
    max_reject_ratio=DEFAULT_STYLE_GATE_MAX_REJECT_RATIO,
    min_samples=DEFAULT_STYLE_GATE_MIN_SAMPLES,
    skip_messages=None,
):
    skip_messages = set(skip_messages or [])
    profile = build_style_profile(baseline_comments)
    if profile["sample_count"] < min_samples:
        return {
            "status": "insufficient_samples",
            "profile": profile,
            "scored_count": 0,
            "rejected_count": 0,
            "reject_ratio": 1.0,
            "max_z": math.inf,
            "details": [],
            "reason": f"style sample count {profile['sample_count']} is below {min_samples}",
        }

    details = []
    for message in messages:
        if message in skip_messages:
            continue
        score = score_text(message, profile)
        score["rejected"] = score["max_z"] > max_z
        details.append(score)

    rejected_count = sum(1 for item in details if item["rejected"])
    scored_count = len(details)
    reject_ratio = rejected_count / max(1, scored_count)
    max_observed_z = max((item["max_z"] for item in details), default=0.0)
    status = "pass"
    if rejected_count and reject_ratio <= max_reject_ratio:
        status = "delay"
    elif rejected_count:
        status = "stop"

    return {
        "status": status,
        "profile": profile,
        "scored_count": scored_count,
        "rejected_count": rejected_count,
        "reject_ratio": reject_ratio,
        "max_z": max_observed_z,
        "details": details,
        "reason": "",
    }


def summarize_report(report, detail_limit=5):
    lines = [
        (
            f"status={report['status']} samples={report['profile']['sample_count']} "
            f"scored={report['scored_count']} rejected={report['rejected_count']} "
            f"reject_ratio={report['reject_ratio']:.3f} max_z={report['max_z']:.3f}"
        )
    ]
    if report.get("reason"):
        lines.append(f"reason={report['reason']}")
    rejected = [item for item in report.get("details", []) if item.get("rejected")]
    for item in rejected[:detail_limit]:
        text = item["text"]
        if len(text) > 40:
            text = text[:37] + "..."
        lines.append(
            f"reject feature={item['max_feature']} z={item['max_z']:.3f} text={text}"
        )
    return "\n".join(lines)
