import contextlib
import io
import math
import random
import statistics
from collections import Counter

from live_bullet_covert import sender


CARRIER_SYMBOLS = set(sender.SYMBOL_MAP.values())
CARRIER_PUNCTUATION = set(sender.PUNCTUATION_MAP.values()) | set(
    getattr(sender, "COMPACT_CARRIER_ALPHABET", "")
)


def normal_comment():
    templates = sender.CARRIER_TEMPLATES + sender.DISTRACTION_TEMPLATES
    template = random.choice(templates)
    suffix = random.choice(sender.RANDOM_SUFFIXES)
    try:
        return template.format(suffix)
    except Exception:
        return template


def covert_comments(message, seed, loaded_only=False):
    random.seed(seed)
    core = sender.CovLBCG_Core()
    with contextlib.redirect_stdout(io.StringIO()):
        payloads = core.gen_payloads(message)
    if loaded_only:
        return [payload["c"] for payload in payloads if payload.get("code")]
    return [payload["c"] for payload in payloads]


def features(text):
    length = max(len(text), 1)
    carrier_symbol_count = sum(1 for ch in text if ch in CARRIER_SYMBOLS)
    carrier_punctuation_count = sum(1 for ch in text if ch in CARRIER_PUNCTUATION)
    whitespace_count = sum(1 for ch in text if ch.isspace())
    max_space_run = 0
    current_run = 0
    for ch in text:
        if ch.isspace():
            current_run += 1
            max_space_run = max(max_space_run, current_run)
        else:
            current_run = 0

    return {
        "length": length,
        "carrier_symbol_count": carrier_symbol_count,
        "carrier_punctuation_count": carrier_punctuation_count,
        "whitespace_count": whitespace_count,
        "max_space_run": max_space_run,
        "carrier_symbol_ratio": carrier_symbol_count / length,
        "carrier_punctuation_ratio": carrier_punctuation_count / length,
        "whitespace_ratio": whitespace_count / length,
        "ends_with_four_symbols": int(
            len(text) >= 4 and all(ch in CARRIER_SYMBOLS for ch in text[-4:])
        ),
    }


def summarize(rows):
    keys = rows[0].keys()
    summary = {}
    for key in keys:
        values = [row[key] for row in rows]
        summary[key] = {
            "mean": statistics.mean(values),
            "stdev": statistics.pstdev(values),
            "max": max(values),
        }
    return summary


def zscore_detector(row, benign_summary):
    score = 0.0
    for key in [
        "length",
        "carrier_symbol_count",
        "carrier_punctuation_count",
        "whitespace_count",
        "max_space_run",
    ]:
        stdev = benign_summary[key]["stdev"] or 1.0
        score += abs(row[key] - benign_summary[key]["mean"]) / stdev
    return score


def evaluate_threshold(scores_benign, scores_covert):
    candidates = sorted(set(scores_benign + scores_covert))
    best = None
    for threshold in candidates:
        tp = sum(score >= threshold for score in scores_covert)
        fp = sum(score >= threshold for score in scores_benign)
        fn = len(scores_covert) - tp
        tn = len(scores_benign) - fp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        accuracy = (tp + tn) / (len(scores_benign) + len(scores_covert))
        candidate = (f1, accuracy, precision, recall, threshold)
        if best is None or candidate > best:
            best = candidate
    f1, accuracy, precision, recall, threshold = best
    return {
        "threshold": threshold,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def js_divergence(left_values, right_values):
    left = Counter(left_values)
    right = Counter(right_values)
    keys = set(left) | set(right)
    total_left = sum(left.values())
    total_right = sum(right.values())

    def kl(p_counts, q_probs, total):
        value = 0.0
        for key in keys:
            p = p_counts[key] / total if total else 0.0
            q = q_probs[key]
            if p > 0 and q > 0:
                value += p * math.log2(p / q)
        return value

    mid = {
        key: 0.5 * (left[key] / total_left + right[key] / total_right)
        for key in keys
    }
    return 0.5 * kl(left, mid, total_left) + 0.5 * kl(right, mid, total_right)


def run_profile(loaded_only):
    random.seed(20260511)
    benign_texts = [normal_comment() for _ in range(500)]

    covert_texts = []
    loaded_count = 0
    total_count = 0
    for index in range(40):
        all_comments = covert_comments(f"CovLBCG_test_{index:02d}#", 20260511 + index, False)
        loaded_comments = covert_comments(f"CovLBCG_test_{index:02d}#", 20260511 + index, True)
        total_count += len(all_comments)
        loaded_count += len(loaded_comments)
        covert_texts.extend(loaded_comments if loaded_only else all_comments)
    covert_texts = covert_texts[:500]

    benign_rows = [features(text) for text in benign_texts]
    covert_rows = [features(text) for text in covert_texts]
    benign_summary = summarize(benign_rows)
    covert_summary = summarize(covert_rows)

    profile_name = "loaded-only" if loaded_only else "stream-level"
    print(f"\nProfile: {profile_name}")
    print(f"loaded_ratio={loaded_count / total_count:.4f}")
    print("Feature means: benign vs covert")
    for key in [
        "length",
        "carrier_symbol_count",
        "carrier_punctuation_count",
        "whitespace_count",
        "max_space_run",
        "ends_with_four_symbols",
    ]:
        print(
            f"{key}: "
            f"{benign_summary[key]['mean']:.4f} vs {covert_summary[key]['mean']:.4f}"
        )

    rule_tp = sum(row["ends_with_four_symbols"] for row in covert_rows)
    rule_fp = sum(row["ends_with_four_symbols"] for row in benign_rows)
    rule_precision = rule_tp / (rule_tp + rule_fp) if rule_tp + rule_fp else 0.0
    rule_recall = rule_tp / len(covert_rows)
    rule_f1 = (
        2 * rule_precision * rule_recall / (rule_precision + rule_recall)
        if rule_precision + rule_recall
        else 0.0
    )
    print("\nRule detector: ends_with_four_symbols")
    print(
        f"precision={rule_precision:.4f} recall={rule_recall:.4f} "
        f"f1={rule_f1:.4f} false_positive={rule_fp}/{len(benign_rows)}"
    )

    benign_scores = [zscore_detector(row, benign_summary) for row in benign_rows]
    covert_scores = [zscore_detector(row, benign_summary) for row in covert_rows]
    stat_result = evaluate_threshold(benign_scores, covert_scores)
    print("\nZ-score statistical detector")
    print(
        f"threshold={stat_result['threshold']:.4f} "
        f"accuracy={stat_result['accuracy']:.4f} "
        f"precision={stat_result['precision']:.4f} "
        f"recall={stat_result['recall']:.4f} "
        f"f1={stat_result['f1']:.4f}"
    )

    print("\nDistribution distance")
    print(
        "length_js="
        f"{js_divergence([row['length'] for row in benign_rows], [row['length'] for row in covert_rows]):.4f}"
    )
    print(
        "carrier_symbol_count_js="
        f"{js_divergence([row['carrier_symbol_count'] for row in benign_rows], [row['carrier_symbol_count'] for row in covert_rows]):.4f}"
    )


def main():
    run_profile(loaded_only=True)
    run_profile(loaded_only=False)


if __name__ == "__main__":
    main()

