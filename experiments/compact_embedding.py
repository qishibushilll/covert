import contextlib
import io
import random
import statistics

from live_bullet_covert import sender
import detectability_baseline as detect


TRIAL_MESSAGES = [f"CovLBCG_compact_{index:02d}#" for index in range(40)]


def payload_sets(compact_enabled, semantic_enabled, humanized_enabled=False):
    original_compact = sender.COMPACT_EMBEDDING_ENABLED
    original_semantic = sender.SEMANTIC_EMBEDDING_ENABLED
    original_humanized = sender.HUMANIZED_CARRIER_ENABLED
    sender.COMPACT_EMBEDDING_ENABLED = compact_enabled
    sender.SEMANTIC_EMBEDDING_ENABLED = semantic_enabled
    sender.HUMANIZED_CARRIER_ENABLED = humanized_enabled
    try:
        sets = []
        for index, message in enumerate(TRIAL_MESSAGES):
            random.seed(20260519 + index)
            core = sender.CovLBCG_Core()
            core.room_comments = []
            with contextlib.redirect_stdout(io.StringIO()):
                sets.append(core.gen_payloads(message))
        return sets
    finally:
        sender.COMPACT_EMBEDDING_ENABLED = original_compact
        sender.SEMANTIC_EMBEDDING_ENABLED = original_semantic
        sender.HUMANIZED_CARRIER_ENABLED = original_humanized


def features_for_texts(texts):
    return [detect.features(text) for text in texts]


def zscore_f1(benign_rows, covert_rows):
    benign_summary = detect.summarize(benign_rows)
    benign_scores = [detect.zscore_detector(row, benign_summary) for row in benign_rows]
    covert_scores = [detect.zscore_detector(row, benign_summary) for row in covert_rows]
    return detect.evaluate_threshold(benign_scores, covert_scores)["f1"]


def js_for_feature(benign_rows, covert_rows, feature):
    return detect.js_divergence(
        [row[feature] for row in benign_rows],
        [row[feature] for row in covert_rows],
    )


def evaluate(label, sets, benign_texts):
    loaded_texts = [
        payload["c"]
        for payloads in sets
        for payload in payloads
        if payload.get("code")
    ][:500]
    stream_texts = [payload["c"] for payloads in sets for payload in payloads][:500]

    benign_rows = features_for_texts(benign_texts)
    loaded_rows = features_for_texts(loaded_texts)
    stream_rows = features_for_texts(stream_texts)
    return {
        "mode": label,
        "loaded_len_mean": statistics.mean(row["length"] for row in loaded_rows),
        "stream_len_mean": statistics.mean(row["length"] for row in stream_rows),
        "loaded_symbol_mean": statistics.mean(row["carrier_symbol_count"] for row in loaded_rows),
        "loaded_punctuation_mean": statistics.mean(row["carrier_punctuation_count"] for row in loaded_rows),
        "loaded_z_f1": zscore_f1(benign_rows, loaded_rows),
        "stream_z_f1": zscore_f1(benign_rows, stream_rows),
        "stream_length_js": js_for_feature(benign_rows, stream_rows, "length"),
        "symbol_count_js": js_for_feature(benign_rows, stream_rows, "carrier_symbol_count"),
    }


def main():
    random.seed(20260519)
    benign_texts = [detect.normal_comment() for _ in range(500)]
    rows = [
        evaluate("legacy_mixed_suffix", payload_sets(False, False, False), benign_texts),
        evaluate("compact_position_in_text", payload_sets(True, False, False), benign_texts),
        evaluate("compact_semantic_in_text", payload_sets(True, True, False), benign_texts),
        evaluate("humanized_phrase_carrier", payload_sets(True, True, True), benign_texts),
    ]

    print(
        "mode,loaded_len_mean,stream_len_mean,loaded_symbol_mean,"
        "loaded_punctuation_mean,loaded_z_f1,stream_z_f1,"
        "stream_length_js,symbol_count_js"
    )
    for row in rows:
        print(
            f"{row['mode']},"
            f"{row['loaded_len_mean']:.4f},"
            f"{row['stream_len_mean']:.4f},"
            f"{row['loaded_symbol_mean']:.4f},"
            f"{row['loaded_punctuation_mean']:.4f},"
            f"{row['loaded_z_f1']:.4f},"
            f"{row['stream_z_f1']:.4f},"
            f"{row['stream_length_js']:.4f},"
            f"{row['symbol_count_js']:.4f}"
        )


if __name__ == "__main__":
    main()

