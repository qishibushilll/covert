import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_bullet_covert import online_style


class Args:
    def __init__(
        self,
        realtime_online_style=True,
        realtime_template_payloads=False,
        room=6,
        online_style_source_room=None,
    ):
        self.realtime_online_style = realtime_online_style
        self.realtime_template_payloads = realtime_template_payloads
        self.room = room
        self.online_style_source_room = online_style_source_room


def test_resolve_source_room_defaults_to_send_room():
    assert online_style.resolve_source_room(23087172, None) == 23087172


def test_source_room_can_differ_from_send_room():
    assert online_style.resolve_source_room(23087172, 7243837) == 7243837


def test_cross_room_learning_does_not_apply_templates():
    assert not online_style.should_apply_learned_templates(
        send_room_display_id=23087172,
        source_room_display_id=7243837,
        templates_path="data/profiles/online_style_profiles/room_7243837_templates.txt",
    )


def test_same_room_learning_can_apply_templates():
    assert online_style.should_apply_learned_templates(
        send_room_display_id=23087172,
        source_room_display_id=23087172,
        templates_path="data/profiles/online_style_profiles/room_23087172_templates.txt",
    )


def test_style_file_room_id_detects_room_profile_paths():
    assert (
        online_style.style_file_room_id(
            "data/profiles/online_style_profiles/room_7243837_templates.txt"
        )
        == 7243837
    )
    assert (
        online_style.style_file_room_id(
            r"data\profiles\online_style_profiles\room_23087172_profile.json"
        )
        == 23087172
    )
    assert online_style.style_file_room_id("data/profiles/popular_templates.txt") is None


def test_cross_room_style_file_is_rejected_for_real_send():
    try:
        online_style.validate_style_file_for_send(
            send_room_display_id=23087172,
            style_file="data/profiles/online_style_profiles/room_7243837_templates.txt",
            send=True,
        )
    except ValueError as exc:
        assert "refusing --send" in str(exc)
    else:
        raise AssertionError("expected cross-room style_file to be rejected for real send")


def test_cross_room_style_file_allowed_for_dry_run():
    online_style.validate_style_file_for_send(
        send_room_display_id=23087172,
        style_file="data/profiles/online_style_profiles/room_7243837_templates.txt",
        send=False,
    )


def test_same_room_style_file_allowed_for_real_send():
    online_style.validate_style_file_for_send(
        send_room_display_id=23087172,
        style_file="data/profiles/online_style_profiles/room_23087172_templates.txt",
        send=True,
    )


def test_cross_room_realtime_templates_are_rejected_for_real_send():
    try:
        online_style.validate_realtime_template_source_for_send(
            send_room_display_id=23087172,
            source_room_display_id=6,
            send=True,
        )
    except ValueError as exc:
        assert "refusing --send" in str(exc)
        assert "realtime templates" in str(exc)
    else:
        raise AssertionError("expected cross-room realtime templates to be rejected")


def test_same_room_realtime_templates_allowed_for_real_send():
    online_style.validate_realtime_template_source_for_send(
        send_room_display_id=6,
        source_room_display_id=6,
        send=True,
    )


def test_browser_sender_auto_enables_same_room_realtime_templates():
    from scripts.bilibili import send_browser_cdp

    args = Args(room=6, online_style_source_room=6)
    send_browser_cdp.enable_realtime_template_payloads_by_default(args)
    assert args.realtime_template_payloads


def test_browser_sender_does_not_auto_enable_cross_room_realtime_templates():
    from scripts.bilibili import send_browser_cdp

    args = Args(room=23087172, online_style_source_room=6)
    send_browser_cdp.enable_realtime_template_payloads_by_default(args)
    assert not args.realtime_template_payloads


def test_http_sender_auto_enables_same_room_realtime_templates():
    from scripts.bilibili.probes import full_http_sender

    args = Args(room=6, online_style_source_room=6)
    full_http_sender.enable_realtime_template_payloads_by_default(args)
    assert args.realtime_template_payloads


def test_realtime_monitor_uses_default_cpm_before_samples():
    monitor = online_style.RealtimeStyleMonitor(room_display_id=6, default_cpm=20.0)
    monitor.started_at = 100.0
    snapshot = monitor.snapshot()
    assert snapshot["activity"]["observed_count"] == 0
    assert snapshot["activity"]["pacing_comments_per_minute"] == 20.0


def test_realtime_monitor_records_unique_clean_comments():
    monitor = online_style.RealtimeStyleMonitor(room_display_id=6, max_len=20, target_count=2)
    monitor.started_at = 100.0
    monitor._on_comment("hello", 101.0)
    monitor._on_comment("hello", 102.0)
    monitor._on_comment("world", 103.0)
    monitor._on_comment("third", 104.0)
    snapshot = monitor.snapshot()
    assert snapshot["activity"]["observed_count"] == 4
    assert snapshot["comments"] == ["hello", "world"]
    assert snapshot["activity"]["usable_count"] == 2


def test_realtime_monitor_wait_for_samples_returns_when_ready():
    monitor = online_style.RealtimeStyleMonitor(room_display_id=6, max_len=20, target_count=2)
    monitor.started_at = 100.0
    monitor._on_comment("hello", 101.0)
    snapshot = monitor.wait_for_samples(1, timeout=0.0)
    assert snapshot["comments"] == ["hello"]


def test_realtime_monitor_save_respects_min_samples(tmp_dir=None):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        monitor = online_style.RealtimeStyleMonitor(
            room_display_id=6,
            room_id=7734200,
            out_dir=directory,
            min_samples=2,
        )
        monitor.started_at = 100.0
        monitor._on_comment("hello", 101.0)
        snapshot = monitor.stop_and_save()
        assert snapshot["templates_path"] is None
        assert not (Path(directory) / "room_6_templates.txt").exists()

        monitor = online_style.RealtimeStyleMonitor(
            room_display_id=6,
            room_id=7734200,
            out_dir=directory,
            min_samples=2,
        )
        monitor.started_at = 100.0
        monitor._on_comment("hello", 101.0)
        monitor._on_comment("world", 102.0)
        snapshot = monitor.stop_and_save()
        assert snapshot["templates_path"] == Path(directory) / "room_6_templates.txt"
        assert (Path(directory) / "room_6_templates.txt").exists()


def main():
    test_resolve_source_room_defaults_to_send_room()
    test_source_room_can_differ_from_send_room()
    test_cross_room_learning_does_not_apply_templates()
    test_same_room_learning_can_apply_templates()
    test_style_file_room_id_detects_room_profile_paths()
    test_cross_room_style_file_is_rejected_for_real_send()
    test_cross_room_style_file_allowed_for_dry_run()
    test_same_room_style_file_allowed_for_real_send()
    test_cross_room_realtime_templates_are_rejected_for_real_send()
    test_same_room_realtime_templates_allowed_for_real_send()
    test_browser_sender_auto_enables_same_room_realtime_templates()
    test_browser_sender_does_not_auto_enable_cross_room_realtime_templates()
    test_http_sender_auto_enables_same_room_realtime_templates()
    test_realtime_monitor_uses_default_cpm_before_samples()
    test_realtime_monitor_records_unique_clean_comments()
    test_realtime_monitor_wait_for_samples_returns_when_ready()
    test_realtime_monitor_save_respects_min_samples()
    print("[PASS] online_style")


if __name__ == "__main__":
    main()
