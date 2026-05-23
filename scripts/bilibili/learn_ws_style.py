import argparse
import sys
import time
from pathlib import Path

from live_bullet_covert import bilibili_ws
from live_bullet_covert import room_style


def main():
    parser = argparse.ArgumentParser(description="Learn room style from Bilibili live WebSocket comments.")
    parser.add_argument("--room", type=int, default=23087172)
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--target-count", type=int, default=80)
    parser.add_argument("--max-len", type=int, default=40)
    parser.add_argument("--out-dir", default="data/profiles/room_profiles")
    parser.add_argument("--no-activate", action="store_true")
    args = parser.parse_args()

    comments = []
    seen = set()

    def on_comment(text, timestamp):
        cleaned = room_style.clean_comment(text, max_len=args.max_len)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            comments.append(cleaned)
            clock = time.strftime("%H:%M:%S", time.localtime(timestamp))
            print(f"[{clock}] learn {len(comments):03d}: {cleaned}", flush=True)
        return len(comments) >= args.target_count

    room_id = room_style.room_init(args.room)
    print(
        f"[ws-style] room_display_id={args.room}, room_id={room_id}, seconds={args.seconds}",
        flush=True,
    )
    bilibili_ws.listen(args.room, args.seconds, on_comment)

    result = room_style.save_room_style(
        room_display_id=args.room,
        room_id=room_id,
        comments=comments,
        out_dir=Path(args.out_dir),
        activate=not args.no_activate,
    )
    print(f"[ws-style] sample_count={len(comments)}", flush=True)
    print(f"[ws-style] templates={result['paths']['templates'].resolve()}", flush=True)
    print(f"[ws-style] profile={result['paths']['profile'].resolve()}", flush=True)
    if result["active_path"]:
        print(f"[ws-style] active_templates={result['active_path'].resolve()}", flush=True)


if __name__ == "__main__":
    main()


