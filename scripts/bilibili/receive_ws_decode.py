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
    args = parser.parse_args()

    decoder = receiver.CovLBCG_Decoder()
    data = []
    decoded = False

    print(f"[ws-listen] room={args.room}, seconds={args.seconds}", flush=True)

    def on_comment(content, timestamp):
        nonlocal decoded
        has_encoding = decoder.has_encoding(content)
        clock = time.strftime("%H:%M:%S", time.localtime(timestamp))

        if receiver.JOIN_COMMAND in content or receiver.SYNC_COMMAND in content or has_encoding:
            data.append({"c": content, "t": timestamp})
            carrier = decoder.detect_carrier(content)
            code = decoder.decode_with_carrier(content, carrier)
            print(f"[{clock}] collect carrier={carrier} code={code} content={content}", flush=True)
        elif "fin" in content:
            print(f"[{clock}] FIN content={content}", flush=True)
            print(f"[decode] collected={len(data)}", flush=True)
            if data:
                decoder.decode(data)
                decoded = True
            return True
        return False

    bilibili_ws.listen(args.room, args.seconds, on_comment)
    print("[ws-listen] stopped", flush=True)
    if not decoded:
        print(f"[ws-listen] no final decode, collected={len(data)}", flush=True)


if __name__ == "__main__":
    main()


