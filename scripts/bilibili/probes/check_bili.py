import asyncio
from bilibili_api import live, Credential

# 1. 配置信息
MY_SESSDATA = "30ef271a%2C1782380324%2C6e7b6%2Ac1CjDz1ecJefCBlhq221xgXDe7jrQYy5nRddTVXz781WFOUysXgXyDrLeq_4mADpxKZQYSVmY3b2JxdThWYVJXY1hNTFBFNTIyTjJteTNWdG9jVFRpVzkzZzBFWFZXaVZNTTNhNWlhN19FQmtVZDA4TzVTQ25HN08xdXdDWFotMkNCYzlMZ25HX3RRIIEC"
TARGET_ROOM_ID = 7734200
JOIN_COMMAND = "主播加油"


async def main():
    # 2. 创建凭证和监听器
    credential = Credential(sessdata=MY_SESSDATA)
    room = live.LiveDanmaku(
        room_display_id=TARGET_ROOM_ID,
        credential=credential
    )

    # 3. 定义事件处理函数 (确保使用 async def)
    @room.on('DANMU_MSG')
    async def on_danmaku(event):
        info = event['data']['info']
        content = info[1]
        user = info[2][1] if len(info[2]) > 1 else 'Unknown'
        print(f'[弹幕] {user}: {content}')
        if JOIN_COMMAND in content or "坐标" in content:
            print(f'   -> ✅ 已捕获目标弹幕!')

    @room.on('INTERACT_WORD')
    async def on_enter(event):
        data = event['data']
        print(f'[进入] 用户 {data.get("uname")} 进入直播间')

    @room.on('LIVE')
    async def on_live_start(event):
        print('[状态] 直播开始!')

    @room.on('PREPARING')
    async def on_live_end(event):
        print('[状态] 直播结束!')

    # 4. 连接并保持运行
    print(f"正在连接房间 {TARGET_ROOM_ID}... (按 Ctrl+C 停止)")
    await room.connect()

    # 主循环，保持连接
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n用户中断。")
    finally:
        await room.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
