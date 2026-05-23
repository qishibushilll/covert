import argparse
import json
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

from live_bullet_covert import sender


COOKIE_PATH = Path("bilibili_cookies.json")


def load_cookie_header():
    cookies = json.loads(COOKIE_PATH.read_text(encoding="utf-8"))
    pairs = []
    csrf = None
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if not name or value is None:
            continue
        pairs.append(f"{name}={value}")
        if name == "bili_jct":
            csrf = value
    if not csrf:
        raise RuntimeError("bili_jct not found in bilibili_cookies.json; login cookie may be missing.")
    return "; ".join(pairs), csrf


def post_danmaku(room_id, message, cookie_header, csrf):
    url = "https://api.live.bilibili.com/msg/send"
    data = {
        "bubble": "0",
        "msg": message,
        "color": "16777215",
        "mode": "1",
        "fontsize": "25",
        "rnd": str(int(time.time())),
        "roomid": str(room_id),
        "csrf": csrf,
        "csrf_token": csrf,
    }
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Referer": f"https://live.bilibili.com/{room_id}",
            "Origin": "https://live.bilibili.com",
            "Cookie": cookie_header,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8", errors="ignore")
    return json.loads(body)


def main():
    parser = argparse.ArgumentParser(description="Send one CovLBCG probe code through Bilibili HTTP danmaku API.")
    parser.add_argument("--room", type=int, default=6963590)
    parser.add_argument("--code", default="00012")
    parser.add_argument("--sleep", type=float, default=1.2)
    args = parser.parse_args()

    if not COOKIE_PATH.exists():
        raise SystemExit("bilibili_cookies.json not found. Browser login is required first.")
    if not args.code.isdigit() or len(args.code) != 5:
        raise SystemExit("--code must be exactly five digits, e.g. 00012")

    cookie_header, csrf = load_cookie_header()
    random.seed(20260513)
    core = sender.CovLBCG_Core()
    payload = core.make_payload_comment(args.code)["c"]

    messages = [sender.JOIN_COMMAND, sender.SYNC_COMMAND, payload, "fin"]
    print(f"room={args.room}")
    print(f"probe_code={args.code}")
    print(f"probe_payload={payload}")
    for message in messages:
        result = post_danmaku(args.room, message, cookie_header, csrf)
        print(f"send={message!r} result={result}")
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()

