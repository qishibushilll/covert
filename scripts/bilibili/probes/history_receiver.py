import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from live_bullet_covert import receiver


def headers(room_display_id):
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
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
    return data.get("data", {}).get("room", [])


def item_text(item):
    return str(item.get("text", "")).strip()


def item_key(item):
    text = item_text(item)
    timeline = item.get("timeline") or item.get("check_info", {}).get("ts")
    uid = item.get("uid") or item.get("nickname")
    return (timeline, uid, text) if timeline else (text,)


def main():
    parser = argparse.ArgumentParser(description="Poll Bilibili history API and decode a CovLBCG real-room test.")
    parser.add_argument("--room", type=int, default=23087172)
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--poll", type=float, default=1.5)
    args = parser.parse_args()

    decoder = receiver.CovLBCG_Decoder()
    room_id = room_init(args.room)
    data = []
    seen = set()
    started = time.time()
    decoded = False

    print(f"[history-listen] room_display_id={args.room}, room_id={room_id}, seconds={args.seconds}", flush=True)

    while time.time() - started < args.seconds:
        try:
            items = get_history(args.room, room_id)
        except Exception as exc:
            print(f"[history-listen] poll error: {exc}", flush=True)
            time.sleep(args.poll)
            continue

        for item in items:
            key = item_key(item)
            if key in seen:
                continue
            seen.add(key)

            content = item_text(item)
            if not content:
                continue

            timestamp = time.time()
            has_encoding = (
                len(decoder.trailing_mixed_carrier_digits(content))
                >= receiver.PROTOCOL_FRAGMENT_RECORD_SIZE
            )

            if receiver.JOIN_COMMAND in content or receiver.SYNC_COMMAND in content or has_encoding:
                data.append({"c": content, "t": timestamp})
                carrier = decoder.detect_carrier(content)
                code = decoder.decode_with_carrier(content, carrier)
                clock = time.strftime("%H:%M:%S", time.localtime(timestamp))
                print(f"[{clock}] collect carrier={carrier} code={code} content={content}", flush=True)
            elif "fin" in content:
                clock = time.strftime("%H:%M:%S", time.localtime(timestamp))
                print(f"[{clock}] FIN content={content}", flush=True)
                print(f"[decode] collected={len(data)}", flush=True)
                if data:
                    decoder.decode(data)
                    decoded = True
                break

        if decoded:
            break
        time.sleep(args.poll)

    print("[history-listen] stopped", flush=True)


if __name__ == "__main__":
    main()

