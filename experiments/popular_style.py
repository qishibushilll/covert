import argparse
import contextlib
import io
import json
import random
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from live_bullet_covert import bilibili_ws
from live_bullet_covert import sender
import detectability_baseline as detect
from live_bullet_covert import room_style


DEFAULT_OUT_DIR = Path("popular_style_profiles")
TRIAL_MESSAGES = [f"CovLBCG_popular_style_{index:02d}#" for index in range(40)]


def parse_rooms(values):
    rooms = []
    for value in values:
        for part in str(value).replace(",", " ").split():
            part = part.strip()
            if part.isdigit():
                rooms.append(int(part))
    return list(dict.fromkeys(rooms))


def clean_comment(text, max_len):
    return room_style.clean_comment(text, max_len=max_len)


def collect_from_history(room_display_id, target_count, rounds, sleep_sec, max_len):
    room_id, comments = room_style.collect_room_comments(
        room_display_id=room_display_id,
        target_count=target_count,
        rounds=rounds,
        sleep_sec=sleep_sec,
        max_len=max_len,
    )
    return room_id, comments


def collect_from_ws(room_display_id, target_count, seconds, max_len):
    room_id = room_style.room_init(room_display_id)
    comments = []
    seen = set()

    def on_comment(text, timestamp):
        cleaned = clean_comment(text, max_len)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            comments.append(cleaned)
            clock = time.strftime("%H:%M:%S", time.localtime(timestamp))
            print(f"[ws {room_display_id}] {clock} {len(comments):03d}: {cleaned}", flush=True)
        return len(comments) >= target_count

    bilibili_ws.listen(room_display_id, seconds, on_comment)
    return room_id, comments


def save_comments(path, comments):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(comments) + ("\n" if comments else ""), encoding="utf-8")


def unique_comments(comments):
    seen = set()
    result = []
    for comment in comments:
        if comment not in seen:
            seen.add(comment)
            result.append(comment)
    return result


def build_profile(label, rooms, comments):
    lengths = [len(comment) for comment in comments]
    punct_counts = [room_style.punctuation_count(comment) for comment in comments]
    suffix_counts = Counter(
        room_style.suffix_token(comment)
        for comment in comments
        if room_style.suffix_token(comment)
    )
    char_counts = Counter(ch for comment in comments for ch in comment)
    return {
        "label": label,
        "rooms": rooms,
        "sample_count": len(comments),
        "length": {
            "mean": round(statistics.mean(lengths), 4) if lengths else 0,
            "median": statistics.median(lengths) if lengths else 0,
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
        },
        "punctuation": {
            "mean_count": round(statistics.mean(punct_counts), 4) if punct_counts else 0,
            "top_suffixes": suffix_counts.most_common(20),
        },
        "top_chars": char_counts.most_common(40),
    }


def set_sender_style_file(path):
    sender.ROOM_COMMENTS_FILE = str(path)
    sender._ROOM_COMMENT_CACHE = None
    sender._ROOM_COMMENT_CACHE_PATH = None


def fixed_payloads(message, seed):
    random.seed(seed)
    sender.ROOM_COMMENTS_FILE = "__covlbcg_no_room_comments__.txt"
    sender._ROOM_COMMENT_CACHE = None
    sender._ROOM_COMMENT_CACHE_PATH = None
    core = sender.CovLBCG_Core()
    core.room_comments = []
    with contextlib.redirect_stdout(io.StringIO()):
        return core.gen_payloads(message)


def styled_payloads(message, seed, style_file):
    random.seed(seed)
    set_sender_style_file(style_file)
    core = sender.CovLBCG_Core()
    with contextlib.redirect_stdout(io.StringIO()):
        return core.gen_payloads(message)


def features_for_texts(texts):
    return [detect.features(text) for text in texts]


def js_for_feature(benign_rows, covert_rows, feature):
    return detect.js_divergence(
        [row[feature] for row in benign_rows],
        [row[feature] for row in covert_rows],
    )


def zscore_f1(benign_rows, covert_rows):
    benign_summary = detect.summarize(benign_rows)
    benign_scores = [detect.zscore_detector(row, benign_summary) for row in benign_rows]
    covert_scores = [detect.zscore_detector(row, benign_summary) for row in covert_rows]
    return detect.evaluate_threshold(benign_scores, covert_scores)["f1"]


def duplicate_rate(texts):
    counts = Counter(texts)
    duplicates = sum(count - 1 for count in counts.values() if count > 1)
    return duplicates / len(texts) if texts else 0.0


def evaluate_payload_sets(label, payload_sets, benign_texts):
    loaded_texts = [
        payload["c"]
        for payloads in payload_sets
        for payload in payloads
        if payload.get("code")
    ][:500]
    stream_texts = [payload["c"] for payloads in payload_sets for payload in payloads][:500]
    benign_rows = features_for_texts((benign_texts * (500 // max(1, len(benign_texts)) + 1))[:500])
    loaded_rows = features_for_texts(loaded_texts)
    stream_rows = features_for_texts(stream_texts)
    return {
        "label": label,
        "loaded_count": len(loaded_texts),
        "stream_count": len(stream_texts),
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


def run_evaluation(comments, templates_path, out_dir):
    benign_texts = comments * (500 // max(1, len(comments)) + 1)
    random.seed(20260519)
    random.shuffle(benign_texts)

    fixed_sets = [
        fixed_payloads(message, 20260519 + index)
        for index, message in enumerate(TRIAL_MESSAGES)
    ]
    styled_sets = [
        styled_payloads(message, 20260519 + index, templates_path)
        for index, message in enumerate(TRIAL_MESSAGES)
    ]

    rows = [
        evaluate_payload_sets("fixed_templates", fixed_sets, benign_texts),
        evaluate_payload_sets("popular_style", styled_sets, benign_texts),
    ]
    csv_path = out_dir / "popular_style_detectability.csv"
    lines = [
        "method,loaded_count,stream_count,loaded_len_mean,stream_len_mean,"
        "loaded_z_f1,stream_z_f1,stream_length_js,stream_punctuation_js,duplicate_rate"
    ]
    for row in rows:
        lines.append(
            f"{row['label']},{row['loaded_count']},{row['stream_count']},"
            f"{row['loaded_len_mean']:.4f},{row['stream_len_mean']:.4f},"
            f"{row['loaded_z_f1']:.4f},{row['stream_z_f1']:.4f},"
            f"{row['stream_length_js']:.4f},{row['stream_punctuation_js']:.4f},"
            f"{row['duplicate_rate']:.4f}"
        )
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows, csv_path


def main():
    parser = argparse.ArgumentParser(
        description="Passive popular-room style learning and offline CovLBCG detectability experiment."
    )
    parser.add_argument("--rooms", nargs="+", required=True, help="Room display ids, e.g. --rooms 6 7777 6963590")
    parser.add_argument("--target-per-room", type=int, default=80)
    parser.add_argument("--history-rounds", type=int, default=3)
    parser.add_argument("--history-sleep", type=float, default=2.0)
    parser.add_argument("--ws-seconds", type=int, default=0, help="Optional realtime passive listening per room.")
    parser.add_argument("--max-len", type=int, default=20)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--no-evaluate", action="store_true")
    args = parser.parse_args()

    rooms = parse_rooms(args.rooms)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_comments = []
    room_summaries = []

    print(f"rooms={rooms}")
    for room in rooms:
        print(f"\n[room {room}] collecting history...")
        room_id, history_comments = collect_from_history(
            room,
            target_count=args.target_per_room,
            rounds=args.history_rounds,
            sleep_sec=args.history_sleep,
            max_len=args.max_len,
        )
        comments = unique_comments(history_comments)
        print(f"[room {room}] room_id={room_id} history_count={len(comments)}")

        if args.ws_seconds > 0 and len(comments) < args.target_per_room:
            print(f"[room {room}] collecting websocket for {args.ws_seconds}s...")
            _, ws_comments = collect_from_ws(
                room,
                target_count=args.target_per_room - len(comments),
                seconds=args.ws_seconds,
                max_len=args.max_len,
            )
            comments = unique_comments(comments + ws_comments)
            print(f"[room {room}] merged_count={len(comments)}")

        room_comments_path = out_dir / f"room_{room}_comments.txt"
        save_comments(room_comments_path, comments)
        profile = build_profile(f"room_{room}", [room], comments)
        (out_dir / f"room_{room}_profile.json").write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        all_comments.extend(comments)
        room_summaries.append(
            {"room_display_id": room, "room_id": room_id, "sample_count": len(comments)}
        )

    merged_comments = unique_comments(all_comments)
    templates_path = out_dir / "popular_templates.txt"
    comments_path = out_dir / "popular_comments.txt"
    profile_path = out_dir / "popular_profile.json"
    save_comments(comments_path, merged_comments)
    save_comments(templates_path, merged_comments)
    profile = build_profile("popular_style", rooms, merged_comments)
    profile["room_summaries"] = room_summaries
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n[popular corpus]")
    print(f"sample_count={len(merged_comments)}")
    print(f"comments_path={comments_path.resolve()}")
    print(f"templates_path={templates_path.resolve()}")
    print(f"profile_path={profile_path.resolve()}")

    if merged_comments and not args.no_evaluate:
        rows, csv_path = run_evaluation(merged_comments, templates_path, out_dir)
        print(f"detectability_csv={csv_path.resolve()}")
        print(
            "method,loaded_count,stream_count,loaded_len_mean,stream_len_mean,"
            "loaded_z_f1,stream_z_f1,stream_length_js,stream_punctuation_js,duplicate_rate"
        )
        for row in rows:
            print(
                f"{row['label']},{row['loaded_count']},{row['stream_count']},"
                f"{row['loaded_len_mean']:.4f},{row['stream_len_mean']:.4f},"
                f"{row['loaded_z_f1']:.4f},{row['stream_z_f1']:.4f},"
                f"{row['stream_length_js']:.4f},{row['stream_punctuation_js']:.4f},"
                f"{row['duplicate_rate']:.4f}"
            )


if __name__ == "__main__":
    main()

