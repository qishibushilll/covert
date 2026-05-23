import argparse
import asyncio
import time

from bilibili_api import Credential, live

from live_bullet_covert import receiver


async def main_async():
    parser = argparse.ArgumentParser(description="Listen for one-code CovLBCG probe records in a Bilibili live room.")
    parser.add_argument("--room", type=int, default=6963590, help="Bilibili live room display id.")
    parser.add_argument("--seconds", type=int, default=120, help="Listening duration.")
    args = parser.parse_args()

    decoder = receiver.CovLBCG_Decoder()
    credential = Credential(sessdata=receiver.MY_SESSDATA)
    monitor = live.LiveDanmaku(room_display_id=args.room, credential=credential)

    @monitor.on("DANMU_MSG")
    async def on_danmaku(event):
        info = event["data"]["info"]
        content = info[1]
        timestamp = info[0][4] / 1000.0
        carrier_type = decoder.detect_carrier(content)
        code = decoder.decode_with_carrier(content, carrier_type)
        marker = ""
        if receiver.SYNC_COMMAND in content:
            marker = " CAL"
        elif "fin" in content:
            marker = " FIN"

        if marker or code:
            clock = time.strftime("%H:%M:%S", time.localtime(timestamp))
            print(f"[{clock}]{marker} carrier={carrier_type} code={code} content={content}")

    print(f"[probe-listen] room={args.room}, seconds={args.seconds}")
    task = asyncio.create_task(monitor.connect())
    try:
        await asyncio.sleep(args.seconds)
    finally:
        await monitor.disconnect()
        task.cancel()
        print("[probe-listen] stopped")


if __name__ == "__main__":
    asyncio.run(main_async())

