import argparse
import random
import sys
import time
from pathlib import Path

from live_bullet_covert import browser_cdp
from live_bullet_covert import llm_style_audit
from live_bullet_covert import online_style
from live_bullet_covert import sender
from live_bullet_covert import room_style
from live_bullet_covert import send_policy
from live_bullet_covert import style_gate


for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


def build_messages(args):
    actual_room_id = room_style.room_init(args.room)
    sender.TARGET_ROOM_ID = args.room
    sender.FRAGMENT_REPLICAS = args.replicas
    sender.FILLERS_PER_PAYLOAD = args.fillers
    sender.HUMANIZED_CARRIER_ENABLED = not args.template_payloads
    sender.COMPACT_EMBEDDING_ENABLED = True
    sender.SEMANTIC_EMBEDDING_ENABLED = True

    if args.fixed_templates:
        sender.ROOM_COMMENTS_FILE = "__covlbcg_no_room_comments__.txt"
        sender._ROOM_COMMENT_CACHE = None
        sender._ROOM_COMMENT_CACHE_PATH = None
    elif args.style_file:
        sender.ROOM_COMMENTS_FILE = args.style_file
        sender._ROOM_COMMENT_CACHE = None
        sender._ROOM_COMMENT_CACHE_PATH = None

    try:
        online_style.validate_style_file_for_send(
            send_room_display_id=args.room,
            style_file=sender.ROOM_COMMENTS_FILE,
            send=args.send,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    random.seed(20260519)
    core = sender.CovLBCG_Core()
    payloads = core.gen_payloads(args.message)
    messages = [sender.JOIN_COMMAND for _ in range(max(1, args.warmup_count))]
    messages.append(sender.SYNC_COMMAND)
    messages.extend(payload["c"] for payload in payloads)
    messages.append("fin")
    return actual_room_id, core, payloads, messages


def validate_explicit_style_file_for_send(args):
    if args.fixed_templates or not args.style_file:
        return
    try:
        online_style.validate_style_file_for_send(
            send_room_display_id=args.room,
            style_file=args.style_file,
            send=args.send,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def apply_online_style_if_requested(args):
    if not args.online_style_learning:
        return None

    if args.fixed_templates:
        raise SystemExit("--online-style-learning cannot be combined with --fixed-templates")

    source_room = online_style.resolve_source_room(args.room, args.online_style_source_room)
    print(
        f"[online-style] passive staged learning: stages={args.online_style_stages} "
        f"seconds={args.online_style_seconds} target={args.online_style_target} "
        f"source_room={source_room} send_room={args.room}",
        flush=True,
    )
    result = online_style.staged_online_style_learning(
        room_display_id=source_room,
        stages=args.online_style_stages,
        seconds=args.online_style_seconds,
        target_count=args.online_style_target,
        max_len=args.online_style_max_len,
        out_dir=args.online_style_out_dir,
        min_samples=args.online_style_min_samples,
        activate=False,
    )
    templates_path = result.get("templates_path")
    if online_style.should_apply_learned_templates(args.room, source_room, templates_path):
        args.style_file = str(templates_path)
        print(f"[online-style] using refreshed templates: {templates_path}", flush=True)
    elif templates_path:
        print(
            "[online-style] learned source-room templates kept for pacing/audit only; "
            "send-room templates unchanged",
            flush=True,
        )
    return result


def start_realtime_online_style_if_requested(args):
    if not args.realtime_online_style:
        return None
    if args.online_style_learning:
        raise SystemExit("--realtime-online-style cannot be combined with --online-style-learning")
    if args.fixed_templates:
        raise SystemExit("--realtime-online-style cannot be combined with --fixed-templates")

    source_room = online_style.resolve_source_room(args.room, args.online_style_source_room)
    print(
        f"[online-style-rt] background learning: source_room={source_room} "
        f"send_room={args.room} max_seconds={args.realtime_online_style_seconds} "
        f"target={args.online_style_target}",
        flush=True,
    )
    monitor = online_style.RealtimeStyleMonitor(
        room_display_id=source_room,
        max_len=args.online_style_max_len,
        out_dir=args.online_style_out_dir,
        min_samples=args.online_style_min_samples,
        target_count=args.online_style_target,
        max_seconds=args.realtime_online_style_seconds,
        activate=False,
        default_cpm=args.activity_normal_cpm,
    ).start()
    return monitor


def realtime_snapshot(monitor):
    if monitor is None:
        return None
    snapshot = monitor.snapshot()
    activity = snapshot.get("activity", {})
    print(
        f"[online-style-rt] snapshot observed={activity.get('observed_count', 0)} "
        f"usable={activity.get('usable_count', 0)} "
        f"cpm={activity.get('comments_per_minute', 0.0):.2f} "
        f"pacing_cpm={activity.get('pacing_comments_per_minute', 0.0):.2f}",
        flush=True,
    )
    return snapshot


def current_send_sleep(args, style_learning, realtime_monitor, base_send_sleep):
    if realtime_monitor is not None and args.adaptive_sleep:
        snapshot = realtime_monitor.snapshot()
        activity = snapshot.get("activity", {})
        return online_style.conservative_sleep_from_activity(
            base_sleep=base_send_sleep,
            min_sleep=args.min_sleep,
            comments_per_minute=activity.get(
                "pacing_comments_per_minute",
                activity.get("comments_per_minute", args.activity_normal_cpm),
            ),
            quiet_cpm=args.activity_quiet_cpm,
            normal_cpm=args.activity_normal_cpm,
        )
    return base_send_sleep


def main():
    parser = argparse.ArgumentParser(description="Browser-simulated live bullet covert sender using Chrome DevTools Protocol.")
    parser.add_argument("--room", type=int, default=23087172)
    parser.add_argument("--message", default="hi#")
    parser.add_argument("--replicas", type=int, default=3)
    parser.add_argument("--fillers", type=int, default=2)
    parser.add_argument("--fixed-templates", action="store_true")
    parser.add_argument("--style-file")
    parser.add_argument(
        "--template-payloads",
        action="store_true",
        help="Use learned room templates as payload wrappers instead of the fixed humanized codebook.",
    )
    parser.add_argument("--sleep", type=float, default=send_policy.DEFAULT_MIN_SEND_SLEEP)
    parser.add_argument("--min-sleep", type=float, default=send_policy.DEFAULT_MIN_SEND_SLEEP)
    parser.add_argument("--page-wait", type=float, default=25.0)
    parser.add_argument("--warmup-count", type=int, default=3)
    parser.add_argument("--max-comments", type=int, default=send_policy.DEFAULT_SEND_MAX_COMMENTS)
    parser.add_argument("--port", type=int, default=9333)
    parser.add_argument("--user-data-dir", default="local_secrets/chrome_profiles/chrome_cdp_profile")
    parser.add_argument("--send", action="store_true")
    parser.add_argument(
        "--confirm-authorized",
        action="store_true",
        help="Required with --send; confirms this is an authorized test room.",
    )
    parser.add_argument(
        "--authorized-rooms",
        help="Comma/space separated room ids authorized for real sending. Defaults to COVLBCG_AUTHORIZED_ROOMS or 23087172.",
    )
    parser.add_argument("--online-style-learning", action="store_true")
    parser.add_argument(
        "--realtime-online-style",
        action="store_true",
        help="Learn source-room style in the background while preparing and sending.",
    )
    parser.add_argument(
        "--realtime-online-style-seconds",
        type=int,
        default=900,
        help="Maximum background realtime learning duration.",
    )
    parser.add_argument(
        "--online-style-source-room",
        type=int,
        help="Optional room id to passively learn for activity pacing and audit baselines. Real sends still target --room.",
    )
    parser.add_argument("--online-style-stages", type=int, default=online_style.DEFAULT_ONLINE_STYLE_STAGES)
    parser.add_argument("--online-style-seconds", type=int, default=online_style.DEFAULT_ONLINE_STYLE_SECONDS)
    parser.add_argument("--online-style-target", type=int, default=online_style.DEFAULT_ONLINE_STYLE_TARGET)
    parser.add_argument("--online-style-min-samples", type=int, default=online_style.DEFAULT_ONLINE_STYLE_MIN_SAMPLES)
    parser.add_argument("--online-style-max-len", type=int, default=40)
    parser.add_argument("--online-style-out-dir", default="data/profiles/online_style_profiles")
    parser.add_argument("--adaptive-sleep", action="store_true")
    parser.add_argument("--activity-quiet-cpm", type=float, default=online_style.DEFAULT_ACTIVITY_QUIET_CPM)
    parser.add_argument("--activity-normal-cpm", type=float, default=online_style.DEFAULT_ACTIVITY_NORMAL_CPM)
    parser.add_argument("--style-gate", action="store_true")
    parser.add_argument("--style-gate-max-z", type=float, default=style_gate.DEFAULT_STYLE_GATE_MAX_Z)
    parser.add_argument("--style-gate-max-reject-ratio", type=float, default=style_gate.DEFAULT_STYLE_GATE_MAX_REJECT_RATIO)
    parser.add_argument("--style-gate-min-samples", type=int, default=style_gate.DEFAULT_STYLE_GATE_MIN_SAMPLES)
    parser.add_argument("--style-gate-delay-multiplier", type=float, default=style_gate.DEFAULT_STYLE_GATE_DELAY_MULTIPLIER)
    parser.add_argument("--llm-style-audit", action="store_true")
    parser.add_argument("--llm-style-audit-endpoint", default=llm_style_audit.default_endpoint())
    parser.add_argument("--llm-style-audit-model", default=llm_style_audit.default_model())
    parser.add_argument("--llm-style-audit-timeout", type=float, default=llm_style_audit.DEFAULT_TIMEOUT)
    parser.add_argument("--llm-style-audit-sample-limit", type=int, default=llm_style_audit.DEFAULT_SAMPLE_LIMIT)
    parser.add_argument("--llm-style-audit-message-limit", type=int, default=llm_style_audit.DEFAULT_MESSAGE_LIMIT)
    parser.add_argument("--llm-style-audit-min-samples", type=int, default=llm_style_audit.DEFAULT_MIN_SAMPLES)
    parser.add_argument("--llm-style-audit-delay-multiplier", type=float, default=llm_style_audit.DEFAULT_DELAY_MULTIPLIER)
    args = parser.parse_args()

    send_policy.validate_authorized_send_context(
        send=args.send,
        room=args.room,
        confirm_authorized=args.confirm_authorized,
        authorized_rooms_text=args.authorized_rooms,
    )
    validate_explicit_style_file_for_send(args)
    realtime_monitor = start_realtime_online_style_if_requested(args)
    style_learning = None
    try:
        style_learning = apply_online_style_if_requested(args)
        actual_room_id, core, payloads, messages = build_messages(args)
    except Exception:
        if realtime_monitor is not None:
            realtime_monitor.stop()
        raise
    activity = (style_learning or {}).get("activity", {})
    if realtime_monitor is not None:
        realtime_snapshot(realtime_monitor)
    learning_source_room = (style_learning or {}).get("room_display_id", args.room)
    if realtime_monitor is not None:
        learning_source_room = realtime_monitor.room_display_id
    adaptive_sleep = online_style.conservative_sleep_from_activity(
        base_sleep=args.sleep,
        min_sleep=args.min_sleep,
        comments_per_minute=activity.get("comments_per_minute", args.activity_normal_cpm),
        quiet_cpm=args.activity_quiet_cpm,
        normal_cpm=args.activity_normal_cpm,
    )
    send_sleep = adaptive_sleep if args.adaptive_sleep and style_learning else max(args.sleep, args.min_sleep)
    gate_report = None
    if args.style_gate:
        realtime = realtime_snapshot(realtime_monitor)
        baseline_comments = (
            (realtime or {}).get("comments")
            or (style_learning or {}).get("comments")
            or core.room_comments
        )
        gate_report = style_gate.evaluate_messages(
            messages,
            baseline_comments,
            max_z=args.style_gate_max_z,
            max_reject_ratio=args.style_gate_max_reject_ratio,
            min_samples=args.style_gate_min_samples,
            skip_messages={sender.JOIN_COMMAND, sender.SYNC_COMMAND, "fin"},
        )
        print("[style-gate]")
        print(style_gate.summarize_report(gate_report))
        if gate_report["status"] == "insufficient_samples" and args.send:
            raise SystemExit("style gate has insufficient samples; stopping real send")
        if gate_report["status"] == "stop" and args.send:
            raise SystemExit("style gate requested stop; not sending")
        if gate_report["status"] == "delay":
            send_sleep *= max(1.0, args.style_gate_delay_multiplier)
    llm_report = None
    if args.llm_style_audit:
        realtime = realtime_snapshot(realtime_monitor)
        baseline_comments = (
            (realtime or {}).get("comments")
            or (style_learning or {}).get("comments")
            or core.room_comments
        )
        queued_for_audit = [
            message
            for message in messages
            if message not in {sender.JOIN_COMMAND, sender.SYNC_COMMAND, "fin"}
        ]
        try:
            llm_report = llm_style_audit.audit_messages(
                room_id=args.room,
                baseline_comments=baseline_comments,
                queued_messages=queued_for_audit,
                endpoint=args.llm_style_audit_endpoint,
                model=args.llm_style_audit_model,
                timeout=args.llm_style_audit_timeout,
                sample_limit=args.llm_style_audit_sample_limit,
                message_limit=args.llm_style_audit_message_limit,
                min_samples=args.llm_style_audit_min_samples,
            )
        except Exception as exc:
            raise SystemExit(f"LLM style audit failed: {exc}") from exc
        print("[llm-style-audit]")
        print(llm_style_audit.summarize_audit(llm_report))
        if llm_report["status"] == "stop" and args.send:
            raise SystemExit("LLM style audit requested stop; not sending")
        if llm_report["status"] == "delay":
            send_sleep *= max(1.0, args.llm_style_audit_delay_multiplier)

    print(f"room_display_id={args.room}")
    print(f"room_id={actual_room_id}")
    print(f"online_style_source_room={learning_source_room}")
    print(f"message={args.message!r}")
    print(f"replicas={args.replicas}")
    print(f"fillers={args.fillers}")
    print(f"fixed_templates={bool(args.fixed_templates)}")
    print(f"template_payloads={bool(args.template_payloads)}")
    print(f"room_comments_enabled={bool(core.room_comments)} count={len(core.room_comments)}")
    print(f"payload_count={len(payloads)}")
    print(f"total_comments_with_markers={len(messages)}")
    print(f"browser_sleep={args.sleep}")
    print(f"min_send_sleep={args.min_sleep}")
    print(f"adaptive_sleep_enabled={bool(args.adaptive_sleep)}")
    print(f"activity_cpm={activity.get('comments_per_minute', 0.0):.2f}")
    if realtime_monitor is not None:
        realtime = realtime_snapshot(realtime_monitor)
        rt_activity = realtime.get("activity", {})
        print(f"realtime_online_style_enabled=True")
        print(f"realtime_observed={rt_activity.get('observed_count', 0)}")
        print(f"realtime_usable={rt_activity.get('usable_count', 0)}")
        print(f"realtime_activity_cpm={rt_activity.get('comments_per_minute', 0.0):.2f}")
        print(f"realtime_pacing_cpm={rt_activity.get('pacing_comments_per_minute', 0.0):.2f}")
    else:
        print("realtime_online_style_enabled=False")
    print(f"style_gate_enabled={bool(args.style_gate)}")
    print(f"llm_style_audit_enabled={bool(args.llm_style_audit)}")
    print(f"effective_send_sleep={send_sleep:.2f}")
    print(f"authorized_rooms={sorted(send_policy.authorized_rooms(args.authorized_rooms))}")
    print("preview:")
    for index, message in enumerate(messages[:20], 1):
        print(f"{index:03d}: {message}")

    send_policy.validate_low_disturbance_send(
        send=args.send,
        room=args.room,
        total_comments=len(messages),
        max_comments=args.max_comments,
        sleep=send_sleep,
        min_sleep=args.min_sleep,
        confirm_authorized=args.confirm_authorized,
        authorized_rooms_text=args.authorized_rooms,
    )

    print("[browser] launching Chrome...")
    chrome = browser_cdp.launch_chrome(args.port, Path(args.user_data_dir).resolve())
    cdp = None
    try:
        browser_cdp.wait_for_cdp(args.port)
        ws_url = browser_cdp.get_page_ws(args.port)
        cdp = browser_cdp.CDPClient(ws_url)
        cdp.call("Runtime.enable")
        cdp.call("Page.enable")
        cdp.call("Network.enable")
        browser_cdp.set_bilibili_cookies(cdp, browser_cdp.load_cookies())
        live_url = f"https://live.bilibili.com/{args.room}"
        print(f"[browser] navigating {live_url}")
        cdp.call("Page.navigate", {"url": live_url})
        print(f"[browser] waiting {args.page_wait:.1f}s for live chat readiness")
        time.sleep(args.page_wait)
        candidates = cdp.eval(browser_cdp.FIND_INPUT_JS)
        print(f"[browser] input_candidates={candidates.get('result', {}).get('value')}")

        if not args.send:
            print("dry_run=1; add --send --confirm-authorized to actually send through Chrome.")
            return

        print("[browser] sending comments through page input...")
        for index, message in enumerate(messages, 1):
            result = browser_cdp.send_comment(cdp, message)
            print(f"[{index}/{len(messages)}] browser_send={message!r} result={result}")
            if not result.get("ok"):
                raise SystemExit(f"browser send failed at {index}: {result}")
            live_sleep = current_send_sleep(args, style_learning, realtime_monitor, send_sleep)
            print(f"[online-style-rt] next_sleep={live_sleep:.2f}", flush=True)
            time.sleep(live_sleep)
        print("[browser] send complete")
    finally:
        if realtime_monitor is not None:
            realtime_final = realtime_monitor.stop_and_save()
            rt_activity = realtime_final.get("activity", {})
            print(
                f"[online-style-rt] final observed={rt_activity.get('observed_count', 0)} "
                f"usable={rt_activity.get('usable_count', 0)} "
                f"cpm={rt_activity.get('comments_per_minute', 0.0):.2f}",
                flush=True,
            )
        if cdp is not None:
            cdp.close()
        print("[browser] Chrome left open for inspection.")


if __name__ == "__main__":
    main()


