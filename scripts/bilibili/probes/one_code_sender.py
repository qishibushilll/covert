import argparse
import random

from live_bullet_covert import sender


def main():
    parser = argparse.ArgumentParser(description="Send one CovLBCG probe code to a Bilibili live room.")
    parser.add_argument("--room", type=int, default=6963590, help="Bilibili live room display id.")
    parser.add_argument("--code", default="00012", help="Five-digit probe record: seq(2)+frag_idx(1)+fragment(2).")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay before sending the probe payload.")
    args = parser.parse_args()

    if not args.code.isdigit() or len(args.code) != 5:
        raise SystemExit("--code must be exactly five digits, e.g. 00012")

    sender.TARGET_ROOM_ID = args.room
    random.seed(20260513)

    core = sender.CovLBCG_Core()
    payload = core.make_payload_comment(args.code)
    payload["d"] = args.delay

    print(f"[probe] room={args.room}")
    print(f"[probe] code={args.code}")
    print(f"[probe] payload={payload['c']}")
    print("[probe] Browser will send JOIN, CAL, one probe payload, then fin.")

    sender.BrowserSender().run([payload])


if __name__ == "__main__":
    main()

