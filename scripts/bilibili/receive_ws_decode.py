import argparse
import sys
import time
from pathlib import Path

from live_bullet_covert import bilibili_ws
from live_bullet_covert import receiver


for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(description="Decode live bullet covert comments from a raw Bilibili WebSocket listener.")
    parser.add_argument("--room", type=int, default=23087172)
    parser.add_argument("--seconds", type=int, default=240)
    parser.add_argument(
        "--collect-after-sync",
        action="store_true",
        help="After CAL, collect every observed comment until fin so missed payload detection is diagnosable.",
    )
    parser.add_argument(
        "--log-all",
        action="store_true",
        help="Print every observed comment with carrier detection status.",
    )
    args = parser.parse_args()

    decoder = receiver.CovLBCG_Decoder()
    data = []
    decoded = False
    saw_sync = False

    print(f"[ws-listen] room={args.room}, seconds={args.seconds}", flush=True)

    def on_comment(content, timestamp):
        nonlocal decoded, saw_sync
        has_encoding = decoder.has_encoding(content)
        clock = time.strftime("%H:%M:%S", time.localtime(timestamp))
        has_join = receiver.JOIN_COMMAND in content
        has_sync = receiver.SYNC_COMMAND in content
        if has_sync:
            saw_sync = True

        if "fin" in content:
            print(f"[{clock}] FIN content={content}", flush=True)
            print(f"[decode] collected={len(data)}", flush=True)
            if data:
                decoder.decode(data)
                decoded = True
            return True
        if has_join or has_sync or has_encoding or (args.collect_after_sync and saw_sync):
            data.append({"c": content, "t": timestamp})
            carrier = decoder.detect_carrier(content)
            code = decoder.decode_with_carrier(content, carrier)
            print(f"[{clock}] collect carrier={carrier} code={code} content={content}", flush=True)
        elif args.log_all:
            carrier = decoder.detect_carrier(content)
            print(
                f"[{clock}] skip carrier={carrier} has_encoding={has_encoding} content={content}",
                flush=True,
            )
        return False

    bilibili_ws.listen(args.room, args.seconds, on_comment)
    print("[ws-listen] stopped", flush=True)
    if not decoded:
        print(f"[ws-listen] no final decode, collected={len(data)}", flush=True)


if __name__ == "__main__":
    main()


