import argparse
import html
import json
import re
import shutil
import statistics
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


DEFAULT_ROOM_DISPLAY_ID = 6963590
DEFAULT_OUT_DIR = Path("room_profiles")
ACTIVE_COMMENTS_PATH = Path("room_comments.txt")
TARGET_COUNT = 80

PUNCTUATION_CHARS = "，。！？；：、～…—,.!?;:~"
URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
SPACE_RE = re.compile(r"\s+")


def headers(room_display_id):
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Referer": f"https://live.bilibili.com/{room_display_id}",
    }


def get_json(url, room_display_id):
    request = urllib.request.Request(url, headers=headers(room_display_id))
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def room_init(room_display_id):
    query = urllib.parse.urlencode({"id": room_display_id})
    data = get_json(
        f"https://api.live.bilibili.com/room/v1/Room/room_init?{query}",
        room_display_id,
    )
    if data.get("code") != 0:
        raise RuntimeError(f"room_init failed: {data}")
    return data["data"].get("room_id", room_display_id)


def get_history(room_display_id, room_id):
    query = urllib.parse.urlencode({"roomid": room_id, "room_type": 0})
    data = get_json(
        f"https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory?{query}",
        room_display_id,
    )
    if data.get("code") != 0:
        raise RuntimeError(f"gethistory failed: {data}")
    room_items = data.get("data", {}).get("room", [])
    return [item.get("text", "") for item in room_items]


def clean_comment(text, max_len=40):
    text = html.unescape(str(text))
    text = CONTROL_RE.sub("", text)
    text = SPACE_RE.sub(" ", text).strip()
    if not text:
        return ""
    if URL_RE.search(text):
        return ""
    if len(text) > max_len:
        return ""
    return text


def collect_room_comments(
    room_display_id,
    target_count=TARGET_COUNT,
    rounds=12,
    sleep_sec=5.0,
    max_len=40,
):
    room_id = room_init(room_display_id)
    comments = []
    seen = set()
    for round_index in range(max(1, rounds)):
        for text in get_history(room_display_id, room_id):
            text = clean_comment(text, max_len=max_len)
            if not text or text in seen:
                continue
            seen.add(text)
            comments.append(text)
            if len(comments) >= target_count:
                break
        if len(comments) >= target_count:
            break
        if round_index + 1 < rounds:
            time.sleep(sleep_sec)
    return room_id, comments


def punctuation_count(text):
    return sum(1 for ch in text if ch in PUNCTUATION_CHARS)


def suffix_token(text):
    if not text:
        return ""
    tail = []
    for ch in reversed(text):
        if ch in PUNCTUATION_CHARS:
            tail.append(ch)
        else:
            break
    return "".join(reversed(tail))


def build_style_profile(room_display_id, room_id, comments):
    lengths = [len(comment) for comment in comments]
    punct_counts = [punctuation_count(comment) for comment in comments]
    suffix_counts = Counter(suffix_token(comment) for comment in comments if suffix_token(comment))
    char_counts = Counter(ch for comment in comments for ch in comment)

    if lengths:
        mean_len = statistics.mean(lengths)
        median_len = statistics.median(lengths)
    else:
        mean_len = 0
        median_len = 0

    if punct_counts:
        mean_punct = statistics.mean(punct_counts)
    else:
        mean_punct = 0

    buckets = {
        "short": [comment for comment in comments if len(comment) <= 6],
        "medium": [comment for comment in comments if 7 <= len(comment) <= 14],
        "long": [comment for comment in comments if len(comment) >= 15],
    }

    return {
        "room_display_id": room_display_id,
        "room_id": room_id,
        "sample_count": len(comments),
        "length": {
            "mean": round(mean_len, 4),
            "median": median_len,
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
        },
        "punctuation": {
            "mean_count": round(mean_punct, 4),
            "top_suffixes": suffix_counts.most_common(12),
        },
        "top_chars": char_counts.most_common(30),
        "bucket_sizes": {name: len(values) for name, values in buckets.items()},
    }


def room_paths(out_dir, room_display_id):
    out_dir = Path(out_dir)
    stem = f"room_{room_display_id}"
    return {
        "comments": out_dir / f"{stem}_comments.txt",
        "templates": out_dir / f"{stem}_templates.txt",
        "profile": out_dir / f"{stem}_profile.json",
    }


def save_room_style(room_display_id, room_id, comments, out_dir=DEFAULT_OUT_DIR, activate=True):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = room_paths(out_dir, room_display_id)
    profile = build_style_profile(room_display_id, room_id, comments)

    text = "\n".join(comments) + ("\n" if comments else "")
    paths["comments"].write_text(text, encoding="utf-8")
    paths["templates"].write_text(text, encoding="utf-8")
    paths["profile"].write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if activate and comments:
        shutil.copyfile(paths["templates"], ACTIVE_COMMENTS_PATH)

    return {
        "room_display_id": room_display_id,
        "room_id": room_id,
        "comments": comments,
        "profile": profile,
        "paths": paths,
        "active_path": ACTIVE_COMMENTS_PATH if activate and comments else None,
    }


def learn_room_style(
    room_display_id,
    target_count=TARGET_COUNT,
    rounds=12,
    sleep_sec=5.0,
    out_dir=DEFAULT_OUT_DIR,
    activate=True,
    max_len=40,
):
    room_id, comments = collect_room_comments(
        room_display_id=room_display_id,
        target_count=target_count,
        rounds=rounds,
        sleep_sec=sleep_sec,
        max_len=max_len,
    )
    return save_room_style(
        room_display_id=room_display_id,
        room_id=room_id,
        comments=comments,
        out_dir=out_dir,
        activate=activate,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Learn per-room bullet-comment style before CovLBCG transmission."
    )
    parser.add_argument("--room", type=int, default=DEFAULT_ROOM_DISPLAY_ID)
    parser.add_argument("--target-count", type=int, default=TARGET_COUNT)
    parser.add_argument("--rounds", type=int, default=12)
    parser.add_argument("--sleep", type=float, default=5.0)
    parser.add_argument("--max-len", type=int, default=40)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument(
        "--no-activate",
        action="store_true",
        help="Do not copy the learned templates to room_comments.txt.",
    )
    args = parser.parse_args()

    result = learn_room_style(
        room_display_id=args.room,
        target_count=args.target_count,
        rounds=args.rounds,
        sleep_sec=args.sleep,
        out_dir=Path(args.out_dir),
        activate=not args.no_activate,
        max_len=args.max_len,
    )

    paths = result["paths"]
    print(f"room_display_id={args.room}")
    print(f"room_id={result['room_id']}")
    print(f"sample_count={len(result['comments'])}")
    print(f"comments_path={paths['comments'].resolve()}")
    print(f"templates_path={paths['templates'].resolve()}")
    print(f"profile_path={paths['profile'].resolve()}")
    if result["active_path"]:
        print(f"active_templates={result['active_path'].resolve()}")
    print("preview:")
    for text in result["comments"][:20]:
        print(text)


if __name__ == "__main__":
    main()
