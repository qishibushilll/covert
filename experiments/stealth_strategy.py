import contextlib
import io
import random

from live_bullet_covert import sender
import detectability_baseline as detect


def normal_comment():
    return detect.normal_comment()


def carrier_code(code, carrier):
    if carrier == "symbol":
        return "".join(sender.SYMBOL_MAP[digit] for digit in code)
    if carrier == "punctuation":
        return "".join(sender.PUNCTUATION_MAP[digit] for digit in code)
    if carrier == "space":
        return "".join(sender.SPACE_MAP[digit] for digit in code)
    raise ValueError(carrier)


def insert_at_random_boundary(text, payload):
    if len(text) <= 2:
        return text + payload
    # Avoid a deterministic suffix while keeping the comment readable.
    point = random.randint(1, len(text) - 1)
    return text[:point] + payload + text[point:]


def get_codes(message, seed):
    random.seed(seed)
    core = sender.CovLBCG_Core()
    with contextlib.redirect_stdout(io.StringIO()):
        payloads = core.gen_payloads(message)
    return [payload["code"] for payload in payloads if payload.get("code")]


def generate_strategy(strategy, message, seed):
    random.seed(seed)
    codes = get_codes(message, seed)
    comments = []

    for code in codes:
        template = random.choice(sender.CARRIER_TEMPLATES)
        suffix = random.choice(sender.RANDOM_SUFFIXES)
        base = template.format(suffix)

        if strategy == "symbol_suffix":
            carrier = "symbol"
            comments.append(base + carrier_code(code, carrier))
        elif strategy == "mixed_suffix":
            carrier = random.choice(["symbol", "punctuation", "space"])
            comments.append(base + carrier_code(code, carrier))
        elif strategy == "mixed_insert":
            carrier = random.choice(["symbol", "punctuation", "space"])
            comments.append(insert_at_random_boundary(base, carrier_code(code, carrier)))
        elif strategy == "low_density_mixed_insert":
            carrier = random.choice(["symbol", "punctuation", "space"])
            comments.append(insert_at_random_boundary(base, carrier_code(code, carrier)))
            for _ in range(2):
                comments.append(normal_comment())
        elif strategy == "low_density_mixed_suffix":
            carrier = random.choice(["symbol", "punctuation", "space"])
            comments.append(base + carrier_code(code, carrier))
            for _ in range(2):
                comments.append(normal_comment())
        elif strategy == "low_density_symbol_punctuation_suffix":
            carrier = random.choice(["symbol", "punctuation"])
            comments.append(base + carrier_code(code, carrier))
            for _ in range(2):
                comments.append(normal_comment())
        else:
            raise ValueError(strategy)

    return comments


def evaluate_strategy(strategy):
    random.seed(20260511)
    benign_texts = [normal_comment() for _ in range(500)]
    covert_texts = []
    for index in range(40):
        covert_texts.extend(
            generate_strategy(strategy, f"CovLBCG_test_{index:02d}#", 20260511 + index)
        )
    covert_texts = covert_texts[:500]

    benign_rows = [detect.features(text) for text in benign_texts]
    covert_rows = [detect.features(text) for text in covert_texts]
    benign_summary = detect.summarize(benign_rows)
    covert_summary = detect.summarize(covert_rows)

    rule_tp = sum(row["ends_with_four_symbols"] for row in covert_rows)
    rule_fp = sum(row["ends_with_four_symbols"] for row in benign_rows)
    rule_precision = rule_tp / (rule_tp + rule_fp) if rule_tp + rule_fp else 0.0
    rule_recall = rule_tp / len(covert_rows)
    rule_f1 = (
        2 * rule_precision * rule_recall / (rule_precision + rule_recall)
        if rule_precision + rule_recall
        else 0.0
    )

    benign_scores = [detect.zscore_detector(row, benign_summary) for row in benign_rows]
    covert_scores = [detect.zscore_detector(row, benign_summary) for row in covert_rows]
    stat = detect.evaluate_threshold(benign_scores, covert_scores)

    return {
        "strategy": strategy,
        "length_mean": covert_summary["length"]["mean"],
        "symbol_mean": covert_summary["carrier_symbol_count"]["mean"],
        "punctuation_mean": covert_summary["carrier_punctuation_count"]["mean"],
        "space_run_mean": covert_summary["max_space_run"]["mean"],
        "rule_f1": rule_f1,
        "stat_accuracy": stat["accuracy"],
        "stat_f1": stat["f1"],
    }


def main():
    strategies = [
        "symbol_suffix",
        "mixed_suffix",
        "mixed_insert",
        "low_density_mixed_insert",
        "low_density_mixed_suffix",
        "low_density_symbol_punctuation_suffix",
    ]
    print(
        "strategy,length_mean,symbol_mean,punctuation_mean,"
        "space_run_mean,rule_f1,stat_accuracy,stat_f1"
    )
    for strategy in strategies:
        result = evaluate_strategy(strategy)
        print(
            f"{result['strategy']},"
            f"{result['length_mean']:.4f},"
            f"{result['symbol_mean']:.4f},"
            f"{result['punctuation_mean']:.4f},"
            f"{result['space_run_mean']:.4f},"
            f"{result['rule_f1']:.4f},"
            f"{result['stat_accuracy']:.4f},"
            f"{result['stat_f1']:.4f}"
        )


if __name__ == "__main__":
    main()

