import contextlib
import io
import time

from live_bullet_covert import receiver


REALTIME_COMPACT_PAYLOADS = [
    "圆神神，了，刀，妹出三项破败了～",
    "IG质，疑涅槃，理解涅—槃成为涅槃啊！",
    "赵二三，顾涅槃吧！怎么，不ban露露了，",
    "EZ怎，么！打塞恩了。拿轮子妈吧.",
    "该上盲僧，打野了？LGD加；油涅槃冲冲冲了,",
    "为啥，没？露露谁解释一下了,蜘蛛会玩吗—",
    "为啥，没；露露谁解释一下了！蜘蛛会玩吗，",
    "赵二三，顾涅槃吧；怎么,不ban露露了；",
    "圆神神，了：刀、妹出三项破败了…",
    "我说ig本质，涅槃呢、什么？动静吧，",
    "怎么，不～ban露露了。涅槃王朝了！",
    "什么，动静吧～为啥～没露露谁解释一下了…",
    "这镜头，不切过…去吗；女警拉克丝吧，",
    "我说ig本质，涅槃呢—什么？动静吧…",
]


def test_realtime_compact_payloads_decode_without_fin():
    decoder = receiver.CovLBCG_Decoder()
    bullets = [{"c": receiver.SYNC_COMMAND, "t": time.time()}]
    bullets.extend(
        {"c": content, "t": time.time() + index + 1}
        for index, content in enumerate(REALTIME_COMPACT_PAYLOADS)
    )
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        decoder.decode(bullets)
    output = capture.getvalue()
    assert "成功解码: a" in output


def test_false_positive_high_sequence_records_are_ignored():
    decoder = receiver.CovLBCG_Decoder()
    bullets = [{"c": receiver.SYNC_COMMAND, "t": time.time()}]
    bullets.append({"c": "反你的野!!!!!", "t": time.time() + 0.5})
    bullets.extend(
        {"c": content, "t": time.time() + index + 1}
        for index, content in enumerate(REALTIME_COMPACT_PAYLOADS)
    )
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        decoder.decode(bullets)
    output = capture.getvalue()
    assert "成功解码: a" in output


def main():
    test_realtime_compact_payloads_decode_without_fin()
    test_false_positive_high_sequence_records_are_ignored()
    print("[PASS] receiver_realtime_compact")


if __name__ == "__main__":
    main()
