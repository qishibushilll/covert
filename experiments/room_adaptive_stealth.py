import contextlib
import io
import random
import re
import statistics
from collections import Counter
from pathlib import Path

from live_bullet_covert import sender
import detectability_baseline as detect


ROOM_CORPUS_PATH = Path("room_comments.txt")
TRIAL_MESSAGES = [f"CovLBCG_room_adaptive_{index:02d}#" for index in range(40)]


EXTRA_ROOM_COMMENTS = [
    "这把有点东西",
    "主播稳住",
    "哈哈哈哈哈",
    "这波可以",
    "太细节了",
    "我刚来",
    "什么情况",
    "有点离谱",
    "这装备可以",
    "别急别急",
    "这也能赢",
    "学到了",
    "主播看下弹幕",
    "这局太精彩了",
    "还有这种操作",
    "对面急了",
    "这手速可以",
    "刚才发生啥了",
    "笑死",
    "舒服了",
    "这配合可以",
    "感觉稳了",
    "差一点",
    "这也太秀了",
    "再来一把",
]


def strip_carrier_chars(text):
    carrier_chars = getattr(
        sender,
        "ALL_CARRIER_CHARS",
        set(sender.SYMBOL_MAP.values()) | set(sender.PUNCTUATION_MAP.values()),
    )
    return "".join(ch for ch in text if ch not in carrier_chars)


def load_room_corpus():
    if ROOM_CORPUS_PATH.exists():
        comments = [
            line.strip()
            for line in ROOM_CORPUS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if comments:
            return comments, "room_comments.txt"

    comments = []
    for template in sender.CARRIER_TEMPLATES:
        for suffix in sender.RANDOM_SUFFIXES + [""]:
            try:
                comments.append(template.format(suffix))
            except Exception:
                comments.append(template)
    comments.extend(sender.DISTRACTION_TEMPLATES)
    comments.extend(EXTRA_ROOM_COMMENTS)
    return comments, "synthetic_room_corpus"


class RoomAdaptiveSampler:
    def __init__(self, corpus):
        self.corpus = [comment.strip() for comment in corpus if comment.strip()]
        self.lengths = [len(comment) for comment in self.corpus]
        self.target_mean_len = statistics.mean(self.lengths)
        self.punctuation_counts = [
            sum(1 for ch in comment if ch in detect.CARRIER_PUNCTUATION)
            for comment in self.corpus
        ]
        self.target_mean_punct = statistics.mean(self.punctuation_counts)

    def choose_wrapper(self, carrier_len):
        target_wrapper_len = max(2, round(self.target_mean_len - carrier_len))
        scored = []
        for comment in self.corpus:
            clean = strip_carrier_chars(comment).strip()
            if not clean:
                continue
            score = abs(len(clean) - target_wrapper_len)
            score += 0.75 * abs(
                sum(1 for ch in comment if ch in detect.CARRIER_PUNCTUATION)
                - self.target_mean_punct
            )
            scored.append((score, random.random(), clean))
        scored.sort()
        top = scored[: min(20, len(scored))]
        return random.choice(top)[2] if top else random.choice(self.corpus)

    def choose_filler(self):
        return random.choice(self.corpus)


class RoomAdaptiveCore(sender.CovLBCG_Core):
    def __init__(self, sampler):
        super().__init__()
        self.sampler = sampler

    def make_payload_comment(self, code):
        if sender.COMPACT_EMBEDDING_ENABLED:
            carrier_code, carrier = self.encode_fragment_compact(code)
            wrapper = self.sampler.choose_wrapper(len(carrier_code))
            return {
                "c": self.embed_compact_carrier(wrapper, carrier_code),
                "d": sender.TIME_OFFSET,
                "code": code,
                "carrier": "adaptive+" + carrier,
            }

        carrier_code, carrier = self.encode_fragment_mixed(code)
        wrapper = self.sampler.choose_wrapper(len(carrier_code))
        return {
            "c": wrapper + carrier_code,
            "d": sender.TIME_OFFSET,
            "code": code,
            "carrier": "adaptive+" + carrier,
        }

    def make_distraction_comment(self):
        return {
            "c": self.sampler.choose_filler(),
            "d": sender.TIME_OFFSET,
            "code": "",
            "carrier": "adaptive_distraction",
        }


def fixed_payloads(message, seed):
    random.seed(seed)
    core = sender.CovLBCG_Core()
    core.room_comments = []
    with contextlib.redirect_stdout(io.StringIO()):
        return core.gen_payloads(message)


def adaptive_payloads(message, seed, sampler):
    random.seed(seed)
    core = RoomAdaptiveCore(sampler)
    with contextlib.redirect_stdout(io.StringIO()):
        return core.gen_payloads(message)


def features_for_texts(texts):
    return [detect.features(text) for text in texts]


def js_for_feature(benign_rows, covert_rows, feature):
    return detect.js_divergence(
        [row[feature] for row in benign_rows],
        [row[feature] for row in covert_rows],
    )


def duplicate_rate(texts):
    counts = Counter(texts)
    duplicates = sum(count - 1 for count in counts.values() if count > 1)
    return duplicates / len(texts) if texts else 0.0


def zscore_f1(benign_rows, covert_rows):
    benign_summary = detect.summarize(benign_rows)
    benign_scores = [detect.zscore_detector(row, benign_summary) for row in benign_rows]
    covert_scores = [detect.zscore_detector(row, benign_summary) for row in covert_rows]
    return detect.evaluate_threshold(benign_scores, covert_scores)["f1"]


def evaluate_payloads(label, payload_sets, benign_texts):
    loaded_texts = [
        payload["c"]
        for payloads in payload_sets
        for payload in payloads
        if payload.get("code")
    ][:500]
    stream_texts = [payload["c"] for payloads in payload_sets for payload in payloads][:500]

    benign_rows = features_for_texts(benign_texts[:500])
    loaded_rows = features_for_texts(loaded_texts)
    stream_rows = features_for_texts(stream_texts)

    return {
        "label": label,
        "loaded_len_mean": statistics.mean(row["length"] for row in loaded_rows),
        "stream_len_mean": statistics.mean(row["length"] for row in stream_rows),
        "loaded_z_f1": zscore_f1(benign_rows, loaded_rows),
        "stream_z_f1": zscore_f1(benign_rows, stream_rows),
        "stream_length_js": js_for_feature(benign_rows, stream_rows, "length"),
        "stream_punctuation_js": js_for_feature(
            benign_rows,
            stream_rows,
            "carrier_punctuation_count",
        ),
        "duplicate_rate": duplicate_rate(stream_texts),
    }


def main():
    corpus, source = load_room_corpus()
    sampler = RoomAdaptiveSampler(corpus)
    benign_texts = corpus * (500 // len(corpus) + 1)
    random.seed(20260511)
    random.shuffle(benign_texts)

    fixed_sets = [
        fixed_payloads(message, 20260511 + index)
        for index, message in enumerate(TRIAL_MESSAGES)
    ]
    adaptive_sets = [
        adaptive_payloads(message, 20260511 + index, sampler)
        for index, message in enumerate(TRIAL_MESSAGES)
    ]

    print(f"corpus_source={source}")
    print(f"corpus_size={len(corpus)}")
    print(
        "method,loaded_len_mean,stream_len_mean,loaded_z_f1,stream_z_f1,"
        "stream_length_js,stream_punctuation_js,duplicate_rate"
    )
    for row in [
        evaluate_payloads("fixed_templates", fixed_sets, benign_texts),
        evaluate_payloads("room_adaptive", adaptive_sets, benign_texts),
    ]:
        print(
            f"{row['label']},"
            f"{row['loaded_len_mean']:.4f},"
            f"{row['stream_len_mean']:.4f},"
            f"{row['loaded_z_f1']:.4f},"
            f"{row['stream_z_f1']:.4f},"
            f"{row['stream_length_js']:.4f},"
            f"{row['stream_punctuation_js']:.4f},"
            f"{row['duplicate_rate']:.4f}"
        )


if __name__ == "__main__":
    main()

