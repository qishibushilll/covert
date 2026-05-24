import contextlib
import io
import random
import tempfile
import time
from pathlib import Path

from live_bullet_covert import receiver
from live_bullet_covert import sender


ROOM_COMMENTS = [
    "兰博没人限制了老黑还不盯住兰博这波真难处理",
    "涅槃前四的队伍积分给我偷一下这局节奏太乱了",
    "不会玩发条阵容你选什么这把对线已经很难受了",
]
REALTIME_ROOM_COMMENTS = [
    "兰博没人限制了老黑还不盯住兰博这波真难处理",
    "涅槃前四的队伍积分给我偷一下这局节奏太乱了",
    "不会玩发条阵容你选什么这把对线已经很难受了",
    "搞得像jien涅槃在wbg打得很好一样",
]
SHORT_ROOM_COMMENTS = [
    "666",
    "刀妹入场",
    "?",
    "逆天",
    "杰出",
    "6666666666666666666666666",
    "牢外！",
    "对的对的",
    "一波！",
    "nice",
    "好好好",
    "来了来了，",
    "刀妹准备进场",
    "下一把",
    "？",
    "牛逼牛逼",
    "又没人开团",
    "难道说",
    "赢了",
    "不是吧",
    "我们WBG完蛋啦",
    "为啥不让",
    "g",
    "刀妹正在连接",
    "刀妹来了",
    "翻了",
    "正义必胜",
    "刀斧手何在",
    "拿下！！！！！！",
    "加油LGD",
    "🚀🚀wbg.wei正在连接💃🏻💃🏻",
    "涅槃",
    "刀妹要啟動了",
    "刀妹要来了",
    "有点s了",
    "刀斧手",
    "帅",
    "完了",
    "刀妹",
    "段",
]


class SenderConfig:
    def __enter__(self):
        self.original = {
            "ROOM_COMMENTS_FILE": sender.ROOM_COMMENTS_FILE,
            "HUMANIZED_CARRIER_ENABLED": sender.HUMANIZED_CARRIER_ENABLED,
            "COMPACT_EMBEDDING_ENABLED": sender.COMPACT_EMBEDDING_ENABLED,
            "SEMANTIC_EMBEDDING_ENABLED": sender.SEMANTIC_EMBEDDING_ENABLED,
            "FRAGMENT_REPLICAS": sender.FRAGMENT_REPLICAS,
            "FILLERS_PER_PAYLOAD": sender.FILLERS_PER_PAYLOAD,
            "_ROOM_COMMENT_CACHE": sender._ROOM_COMMENT_CACHE,
            "_ROOM_COMMENT_CACHE_PATH": sender._ROOM_COMMENT_CACHE_PATH,
        }
        return self

    def __exit__(self, exc_type, exc, tb):
        for name, value in self.original.items():
            setattr(sender, name, value)


def configure_sender(comments_path, *, template_payloads):
    sender.ROOM_COMMENTS_FILE = str(comments_path)
    sender.HUMANIZED_CARRIER_ENABLED = not template_payloads
    sender.COMPACT_EMBEDDING_ENABLED = True
    sender.SEMANTIC_EMBEDDING_ENABLED = True
    sender._ROOM_COMMENT_CACHE = None
    sender._ROOM_COMMENT_CACHE_PATH = None


def write_comments(directory):
    path = Path(directory) / "room_23087172_templates.txt"
    path.write_text("\n".join(ROOM_COMMENTS), encoding="utf-8")
    return path


def test_default_payload_mode_uses_humanized_codebook():
    decoder = receiver.CovLBCG_Decoder()
    with tempfile.TemporaryDirectory() as temp_dir, SenderConfig():
        configure_sender(write_comments(temp_dir), template_payloads=False)
        random.seed(20260523)
        core = sender.CovLBCG_Core()
        payload = core.make_payload_comment("00006")

    assert payload["carrier"] == "humanized"
    assert decoder.detect_carrier(payload["c"]) == "humanized"
    assert decoder.decode_with_carrier(payload["c"], "humanized") == "00006"


def test_template_payload_mode_wraps_compact_records_in_room_comments():
    decoder = receiver.CovLBCG_Decoder()
    with tempfile.TemporaryDirectory() as temp_dir, SenderConfig():
        configure_sender(write_comments(temp_dir), template_payloads=True)
        random.seed(20260523)
        core = sender.CovLBCG_Core()
        payload = core.make_payload_comment("00006")

    assert payload["carrier"] == "compact"
    assert decoder.detect_carrier(payload["c"]) == "compact"
    assert decoder.decode_with_carrier(payload["c"], "compact") == "00006"
    stripped = sender.strip_carrier_chars(payload["c"])
    assert any(sender.strip_carrier_chars(comment).startswith(stripped) for comment in ROOM_COMMENTS)


def test_template_payload_mode_round_trips_message():
    with tempfile.TemporaryDirectory() as temp_dir, SenderConfig():
        configure_sender(write_comments(temp_dir), template_payloads=True)
        random.seed(20260523)
        core = sender.CovLBCG_Core()
        generation_log = io.StringIO()
        with contextlib.redirect_stdout(generation_log):
            payloads = core.gen_payloads("a#")

    raw_bullets = [{"c": sender.SYNC_COMMAND, "t": time.time()}]
    raw_bullets.extend(
        {"c": payload["c"], "t": time.time() + offset + 1}
        for offset, payload in enumerate(payloads)
    )

    decoder = receiver.CovLBCG_Decoder()
    decode_log = io.StringIO()
    with contextlib.redirect_stdout(decode_log):
        decoder.decode(raw_bullets)

    assert "成功解码: a" in decode_log.getvalue()


def test_core_can_use_realtime_room_comments_without_file():
    decoder = receiver.CovLBCG_Decoder()
    with SenderConfig():
        sender.HUMANIZED_CARRIER_ENABLED = False
        sender.COMPACT_EMBEDDING_ENABLED = True
        sender.SEMANTIC_EMBEDDING_ENABLED = True
        random.seed(20260523)
        core = sender.CovLBCG_Core(room_comments=ROOM_COMMENTS)
        payload = core.make_payload_comment("00006")

    assert core.room_comments == ROOM_COMMENTS
    assert payload["carrier"] == "compact"
    assert decoder.detect_carrier(payload["c"]) == "compact"
    assert decoder.decode_with_carrier(payload["c"], "compact") == "00006"
    stripped = sender.strip_carrier_chars(payload["c"])
    assert any(sender.strip_carrier_chars(comment).startswith(stripped) for comment in ROOM_COMMENTS)


def test_room_wrapper_filter_rejects_short_or_emoji_only_comments():
    assert not sender.is_room_wrapper_candidate("😧")
    assert not sender.is_room_wrapper_candidate("宫中")
    assert sender.is_room_wrapper_candidate("兰博没人限制了老黑还不盯住兰博这波真难处理")
    filtered = sender.filter_room_wrapper_candidates(
        ["😧", "宫中", "兰博没人限制了老黑还不盯住兰博这波真难处理"]
    )
    assert filtered == ["兰博没人限制了老黑还不盯住兰博这波真难处理"]


def test_payload_wrapper_filter_rejects_tags_emoji_and_long_ascii_runs():
    comments = [
        "[Ave Mujica_愉快]",
        "LNG:合着我只有才是涅槃🤡🤡🤡",
        "xiaohao前面4把完美节奏不给大场mvp 哈哈哈",
        "今天这阿萨姆打回原形了有点夸张",
        "涅槃要去打强队了有感觉吗",
    ]
    filtered = sender.filter_payload_wrapper_candidates(comments)
    assert "今天这阿萨姆打回原形了有点夸张" in filtered
    assert "涅槃要去打强队了有感觉吗" in filtered
    assert all("[Ave" not in item for item in filtered)
    assert all("🤡" not in item for item in filtered)
    assert all("xiaohao" not in item for item in filtered)


def test_payload_wrapper_filter_composes_short_room_comments():
    filtered = sender.filter_payload_wrapper_candidates(SHORT_ROOM_COMMENTS)
    assert len(filtered) >= 4
    assert all(sender.visible_text_len(item) >= sender.MIN_ROOM_WRAPPER_LEN for item in filtered)
    assert all("666" not in item for item in filtered)
    assert all("nice" not in item for item in filtered)
    assert all("🚀" not in item for item in filtered)


def test_short_room_realtime_templates_round_trip_message():
    decoder = receiver.CovLBCG_Decoder()
    with SenderConfig():
        sender.HUMANIZED_CARRIER_ENABLED = False
        sender.COMPACT_EMBEDDING_ENABLED = True
        sender.SEMANTIC_EMBEDDING_ENABLED = True
        sender.FRAGMENT_REPLICAS = 1
        sender.FILLERS_PER_PAYLOAD = 0
        random.seed(20260524)
        core = sender.CovLBCG_Core(room_comments=sender.filter_payload_wrapper_candidates(SHORT_ROOM_COMMENTS))
        payloads = core.gen_payloads("a#")

    assert len(payloads) == 14
    raw_bullets = [{"c": sender.SYNC_COMMAND, "t": time.time()}]
    raw_bullets.extend(
        {"c": payload["c"], "t": time.time() + offset + 1}
        for offset, payload in enumerate(payloads)
    )
    for payload in payloads:
        assert payload["carrier"] == "compact"
        assert decoder.decode_with_carrier(payload["c"], "compact")

    decode_log = io.StringIO()
    with contextlib.redirect_stdout(decode_log):
        decoder.decode(raw_bullets)
    assert "成功解码: a" in decode_log.getvalue()


def test_realtime_template_payloads_avoid_trailing_four_symbol_suffix():
    decoder = receiver.CovLBCG_Decoder()
    with SenderConfig():
        sender.HUMANIZED_CARRIER_ENABLED = False
        sender.COMPACT_EMBEDDING_ENABLED = True
        sender.SEMANTIC_EMBEDDING_ENABLED = True
        random.seed(20260523)
        core = sender.CovLBCG_Core(room_comments=REALTIME_ROOM_COMMENTS)
        payload = core.make_payload_comment("00006")

    assert payload["carrier"] == "compact"
    assert decoder.decode_with_carrier(payload["c"], "compact") == "00006"
    trailing_carriers = 0
    for char in reversed(payload["c"]):
        if char in sender.COMPACT_CARRIER_ALPHABET:
            trailing_carriers += 1
        else:
            break
    assert trailing_carriers < sender.COMPACT_RECORD_SIZE
    assert len(sender.strip_carrier_chars(payload["c"])) >= sender.MIN_ROOM_WRAPPER_LEN


def test_compact_payload_does_not_split_ascii_words():
    decoder = receiver.CovLBCG_Decoder()
    comments = [
        "wbg敢去涅槃刀妹就敢来",
        "lng要是不拿涅槃第一不打team还真可能能赢啊",
        "NIP是生怕赢了吗",
        "EDG领先五把还是有感觉的",
    ]
    with SenderConfig():
        sender.HUMANIZED_CARRIER_ENABLED = False
        sender.COMPACT_EMBEDDING_ENABLED = True
        sender.SEMANTIC_EMBEDDING_ENABLED = True
        random.seed(20260524)
        core = sender.CovLBCG_Core(room_comments=comments)
        payloads = [core.make_payload_comment("00006") for _ in range(20)]

    for payload in payloads:
        assert decoder.decode_with_carrier(payload["c"], "compact") == "00006"
        for index, char in enumerate(payload["c"]):
            if char not in sender.COMPACT_CARRIER_ALPHABET:
                continue
            prev_char = payload["c"][index - 1] if index else ""
            next_char = payload["c"][index + 1] if index + 1 < len(payload["c"]) else ""
            assert not (sender.is_ascii_word_char(prev_char) and sender.is_ascii_word_char(next_char))


def main():
    test_default_payload_mode_uses_humanized_codebook()
    test_template_payload_mode_wraps_compact_records_in_room_comments()
    test_template_payload_mode_round_trips_message()
    test_core_can_use_realtime_room_comments_without_file()
    test_room_wrapper_filter_rejects_short_or_emoji_only_comments()
    test_payload_wrapper_filter_rejects_tags_emoji_and_long_ascii_runs()
    test_payload_wrapper_filter_composes_short_room_comments()
    test_short_room_realtime_templates_round_trip_message()
    test_realtime_template_payloads_avoid_trailing_four_symbol_suffix()
    test_compact_payload_does_not_split_ascii_words()
    print("[PASS] sender_payload_modes")


if __name__ == "__main__":
    main()
