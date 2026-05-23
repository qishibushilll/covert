import contextlib
import io
import random
import statistics
import time

from live_bullet_covert import receiver
from live_bullet_covert import sender
import detectability_baseline as detect


MESSAGE = "CovLBCG_test_123#"
TRIALS = 50
REPETITION = 3
CONDITIONS = [
    ("clean", 0.00, 0.00),
    ("reorder_only", 0.00, 0.10),
    ("light_loss", 0.02, 0.10),
    ("default_loss", 0.10, 0.10),
]

NLG_CODEBOOK = {
    "00": "主播好厉害！",
    "01": "这个游戏好玩吗？",
    "10": "大家晚上好～",
    "11": "这波操作可以的！",
}
NLG_REVERSE = {value: key for key, value in NLG_CODEBOOK.items()}


def bits_from_text(text):
    return "".join(f"{byte:08b}" for byte in text.encode("utf-8"))


def text_from_bits(bits):
    usable = bits[: len(bits) // 8 * 8]
    data = bytes(int(usable[i:i + 8], 2) for i in range(0, len(usable), 8))
    return data.decode("utf-8", errors="ignore")


def perturb(comments, loss_prob, reorder_jitter, seed):
    random.seed(seed)
    observed = []
    for index, comment in enumerate(comments):
        if random.random() < loss_prob:
            continue
        item = dict(comment)
        item["t"] = item.get("t", index) + random.uniform(-reorder_jitter, reorder_jitter)
        observed.append(item)
    observed.sort(key=lambda item: item["t"])
    return observed


def proposed_comments(message, seed):
    random.seed(seed)
    core = sender.CovLBCG_Core()
    with contextlib.redirect_stdout(io.StringIO()):
        payloads = core.gen_payloads(message)
    now = time.time()
    comments = [{"c": sender.SYNC_COMMAND, "t": now}]
    comments.extend(
        {"c": payload["c"], "t": now + offset + 1}
        for offset, payload in enumerate(payloads)
    )
    return comments


def decode_proposed(comments, expected):
    decoder = receiver.CovLBCG_Decoder()
    output = io.StringIO()
    error_output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error_output):
        decoder.decode(comments)
    return f"成功解码: {expected}" in output.getvalue()


def time_modulation_comments(message):
    bits = bits_from_text(message)
    comments = [{"c": detect.normal_comment(), "t": 0.0}]
    timestamp = 0.0
    for bit in bits:
        for _ in range(REPETITION):
            timestamp += 1.0 if bit == "0" else 2.0
            comments.append({"c": detect.normal_comment(), "t": timestamp})
    return comments


def decode_time_modulation(comments, expected):
    if len(comments) < 2:
        return False
    comments = sorted(comments, key=lambda item: item["t"])
    gaps = [comments[i]["t"] - comments[i - 1]["t"] for i in range(1, len(comments))]
    bits = ["1" if gap >= 1.5 else "0" for gap in gaps]

    decoded_bits = []
    for i in range(0, len(bits) - REPETITION + 1, REPETITION):
        group = bits[i:i + REPETITION]
        decoded_bits.append("1" if group.count("1") > group.count("0") else "0")
    return text_from_bits("".join(decoded_bits)) == expected


def nlg_comments(message):
    bits = bits_from_text(message)
    if len(bits) % 2:
        bits += "0"
    comments = []
    timestamp = 0.0
    for i in range(0, len(bits), 2):
        pair = bits[i:i + 2]
        for _ in range(REPETITION):
            comments.append({"c": NLG_CODEBOOK[pair], "t": timestamp})
            timestamp += 1.0
    return comments


def decode_nlg(comments, expected):
    pairs = []
    for i in range(0, len(comments) - REPETITION + 1, REPETITION):
        group = comments[i:i + REPETITION]
        votes = [NLG_REVERSE[item["c"]] for item in group if item["c"] in NLG_REVERSE]
        if not votes:
            continue
        pairs.append(max(set(votes), key=votes.count))
    return text_from_bits("".join(pairs)) == expected


def detector_metrics(method_name, generated_texts):
    random.seed(20260511)
    benign_texts = [detect.normal_comment() for _ in range(500)]
    covert_texts = generated_texts[:500]
    benign_rows = [detect.features(text) for text in benign_texts]
    covert_rows = [detect.features(text) for text in covert_texts]
    benign_summary = detect.summarize(benign_rows)

    rule_tp = sum(row["ends_with_four_symbols"] for row in covert_rows)
    rule_fp = sum(row["ends_with_four_symbols"] for row in benign_rows)
    precision = rule_tp / (rule_tp + rule_fp) if rule_tp + rule_fp else 0.0
    recall = rule_tp / len(covert_rows) if covert_rows else 0.0
    rule_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    benign_scores = [detect.zscore_detector(row, benign_summary) for row in benign_rows]
    covert_scores = [detect.zscore_detector(row, benign_summary) for row in covert_rows]
    stat = detect.evaluate_threshold(benign_scores, covert_scores)
    return {
        "method": method_name,
        "rule_f1": rule_f1,
        "stat_f1": stat["f1"],
        "length_js": detect.js_divergence(
            [row["length"] for row in benign_rows],
            [row["length"] for row in covert_rows],
        ),
    }


def evaluate_method(name, make_comments, decode, expected, loss_prob, reorder_jitter):
    successes = []
    counts = []
    generated_texts = []
    for trial in range(TRIALS):
        comments = make_comments(MESSAGE, 20260511 + trial) if name == "proposed" else make_comments(MESSAGE)
        generated_texts.extend(item["c"] for item in comments)
        observed = perturb(comments, loss_prob, reorder_jitter, 20260600 + trial)
        successes.append(decode(observed, expected))
        counts.append(len(comments))

    detect_metrics = detector_metrics(name, generated_texts)
    return {
        "method": name,
        "success_rate": sum(successes) / len(successes),
        "avg_comments": statistics.mean(counts),
        "rule_f1": detect_metrics["rule_f1"],
        "stat_f1": detect_metrics["stat_f1"],
        "length_js": detect_metrics["length_js"],
    }


def main():
    expected = sender.CovLBCG_Core().sanitize_input(MESSAGE)
    if expected.endswith("#"):
        expected = expected[:-1]

    print(
        "condition,method,success_rate,avg_comments,rule_f1,stat_f1,length_js,"
        "loss_prob,reorder_jitter,trials"
    )
    for condition, loss_prob, reorder_jitter in CONDITIONS:
        rows = [
            evaluate_method("proposed", proposed_comments, decode_proposed, expected, loss_prob, reorder_jitter),
            evaluate_method(
                "time_modulation",
                lambda message: time_modulation_comments(message),
                decode_time_modulation,
                MESSAGE,
                loss_prob,
                reorder_jitter,
            ),
            evaluate_method(
                "nlg_comment_choice",
                lambda message: nlg_comments(message),
                decode_nlg,
                MESSAGE,
                loss_prob,
                reorder_jitter,
            ),
        ]
        for row in rows:
            print(
                f"{condition},"
                f"{row['method']},"
                f"{row['success_rate']:.4f},"
                f"{row['avg_comments']:.2f},"
                f"{row['rule_f1']:.4f},"
                f"{row['stat_f1']:.4f},"
                f"{row['length_js']:.4f},"
                f"{loss_prob:.2f},"
                f"{reorder_jitter:.2f},"
                f"{TRIALS}"
            )


if __name__ == "__main__":
    main()

