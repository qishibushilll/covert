import contextlib
import io
import random
import statistics
import time

from live_bullet_covert import receiver
from live_bullet_covert import sender
import detectability_baseline as detect


MESSAGE = "CovLBCG_test_123#"
TRIALS = 30
LOSS_PROB = 0.10
REORDER_JITTER = 0.10


def perturb(comments, seed):
    random.seed(seed)
    observed = []
    for index, comment in enumerate(comments):
        if random.random() < LOSS_PROB:
            continue
        item = dict(comment)
        item["t"] = item.get("t", index) + random.uniform(-REORDER_JITTER, REORDER_JITTER)
        observed.append(item)
    observed.sort(key=lambda item: item["t"])
    return observed


def generate_payloads(message, seed):
    random.seed(seed)
    core = sender.CovLBCG_Core()
    with contextlib.redirect_stdout(io.StringIO()):
        payloads = core.gen_payloads(message)
    return payloads


def make_comments(payloads):
    now = time.time()
    comments = [{"c": sender.SYNC_COMMAND, "t": now}]
    comments.extend(
        {"c": payload["c"], "t": now + offset + 1}
        for offset, payload in enumerate(payloads)
    )
    return comments


def decode_comments(comments, expected):
    decoder = receiver.CovLBCG_Decoder()
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        decoder.decode(comments)
    return f"成功解码: {expected}" in stdout.getvalue()


def zscore_f1(benign_texts, covert_texts):
    benign_rows = [detect.features(text) for text in benign_texts]
    covert_rows = [detect.features(text) for text in covert_texts]
    benign_summary = detect.summarize(benign_rows)
    benign_scores = [detect.zscore_detector(row, benign_summary) for row in benign_rows]
    covert_scores = [detect.zscore_detector(row, benign_summary) for row in covert_rows]
    return detect.evaluate_threshold(benign_scores, covert_scores)["f1"]


def js_length(benign_texts, covert_texts):
    benign_rows = [detect.features(text) for text in benign_texts]
    covert_rows = [detect.features(text) for text in covert_texts]
    return detect.js_divergence(
        [row["length"] for row in benign_rows],
        [row["length"] for row in covert_rows],
    )


def evaluate_setting(replicas, fillers):
    sender.FRAGMENT_REPLICAS = replicas
    sender.FILLERS_PER_PAYLOAD = fillers

    expected = sender.CovLBCG_Core().sanitize_input(MESSAGE)
    if expected.endswith("#"):
        expected = expected[:-1]

    successes = []
    counts = []
    loaded_texts = []
    stream_texts = []

    for trial in range(TRIALS):
        payloads = generate_payloads(MESSAGE, 20260511 + trial)
        comments = make_comments(payloads)
        observed = perturb(comments, 20260600 + trial)
        successes.append(decode_comments(observed, expected))
        counts.append(len(comments))
        stream_texts.extend(payload["c"] for payload in payloads)
        loaded_texts.extend(payload["c"] for payload in payloads if payload.get("code"))

    random.seed(20260511)
    benign_texts = [detect.normal_comment() for _ in range(500)]
    loaded_sample = loaded_texts[:500]
    stream_sample = stream_texts[:500]

    return {
        "replicas": replicas,
        "fillers": fillers,
        "success": sum(successes) / len(successes),
        "avg_comments": statistics.mean(counts),
        "loaded_ratio": len(loaded_texts) / len(stream_texts),
        "loaded_f1": zscore_f1(benign_texts, loaded_sample),
        "stream_f1": zscore_f1(benign_texts, stream_sample),
        "stream_length_js": js_length(benign_texts, stream_sample),
    }


def main():
    original_replicas = sender.FRAGMENT_REPLICAS
    original_fillers = sender.FILLERS_PER_PAYLOAD
    try:
        print(
            "replicas,fillers,success_10pct,avg_comments,loaded_ratio,"
            "loaded_z_f1,stream_z_f1,stream_length_js"
        )
        for replicas in [1, 2, 3, 4]:
            for fillers in [1, 2, 3]:
                row = evaluate_setting(replicas, fillers)
                print(
                    f"{row['replicas']},"
                    f"{row['fillers']},"
                    f"{row['success']:.4f},"
                    f"{row['avg_comments']:.2f},"
                    f"{row['loaded_ratio']:.4f},"
                    f"{row['loaded_f1']:.4f},"
                    f"{row['stream_f1']:.4f},"
                    f"{row['stream_length_js']:.4f}"
                )
    finally:
        sender.FRAGMENT_REPLICAS = original_replicas
        sender.FILLERS_PER_PAYLOAD = original_fillers


if __name__ == "__main__":
    main()

