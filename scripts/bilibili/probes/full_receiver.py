import argparse
import asyncio
import time

from bilibili_api import Credential, live

from live_bullet_covert import receiver


async def main_async():
    parser = argparse.ArgumentParser(description="Full CovLBCG receiver for Bilibili live-room tests.")
    parser.add_argument("--room", type=int, default=6963590)
    parser.add_argument("--seconds", type=int, default=300)
    args = parser.parse_args()

    decoder = receiver.CovLBCG_Decoder()
    data = []
    credential = Credential(sessdata=receiver.MY_SESSDATA)
    monitor = live.LiveDanmaku(room_display_id=args.room, credential=credential)

    @monitor.on("DANMU_MSG")
    async def on_danmaku(event):
        info = event["data"]["info"]
        content = info[1]
        timestamp = info[0][4] / 1000.0
        has_encoding = len(decoder.trailing_mixed_carrier_digits(content)) >= receiver.PROTOCOL_FRAGMENT_RECORD_SIZE

        if receiver.JOIN_COMMAND in content or receiver.SYNC_COMMAND in content or has_encoding:
            data.append({"c": content, "t": timestamp})
            carrier = decoder.detect_carrier(content)
            code = decoder.decode_with_carrier(content, carrier)
            clock = time.strftime("%H:%M:%S", time.localtime(timestamp))
            print(f"[{clock}] collect carrier={carrier} code={code} content={content}")
        elif "fin" in content:
            clock = time.strftime("%H:%M:%S", time.localtime(timestamp))
            print(f"[{clock}] FIN content={content}")
            print(f"[decode] collected={len(data)}")
            if data:
                decoder.decode(data)

    print(f"[full-listen] room={args.room}, seconds={args.seconds}")
    task = asyncio.create_task(monitor.connect())
    try:
        await asyncio.sleep(args.seconds)
    finally:
        await monitor.disconnect()
        task.cancel()
        print("[full-listen] stopped")


if __name__ == "__main__":
    asyncio.run(main_async())

