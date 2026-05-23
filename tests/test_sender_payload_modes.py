import contextlib
import io
import random
import tempfile
import time
from pathlib import Path

from live_bullet_covert import receiver
from live_bullet_covert import sender


ROOM_COMMENTS = [
    "plainroomchatone",
    "plainroomchattwo",
    "plainroomchatthree",
]


class SenderConfig:
    def __enter__(self):
        self.original = {
            "ROOM_COMMENTS_FILE": sender.ROOM_COMMENTS_FILE,
            "HUMANIZED_CARRIER_ENABLED": sender.HUMANIZED_CARRIER_ENABLED,
            "COMPACT_EMBEDDING_ENABLED": sender.COMPACT_EMBEDDING_ENABLED,
            "SEMANTIC_EMBEDDING_ENABLED": sender.SEMANTIC_EMBEDDING_ENABLED,
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
    assert sender.strip_carrier_chars(payload["c"]) in ROOM_COMMENTS


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
    assert sender.strip_carrier_chars(payload["c"]) in ROOM_COMMENTS


def main():
    test_default_payload_mode_uses_humanized_codebook()
    test_template_payload_mode_wraps_compact_records_in_room_comments()
    test_template_payload_mode_round_trips_message()
    test_core_can_use_realtime_room_comments_without_file()
    print("[PASS] sender_payload_modes")


if __name__ == "__main__":
    main()
