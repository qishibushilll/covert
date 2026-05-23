import argparse
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from live_bullet_covert import llm_style_audit
from live_bullet_covert import online_style
from live_bullet_covert import room_style
from live_bullet_covert import send_policy
from live_bullet_covert import style_gate


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
        raise RuntimeError("bili_jct not found in bilibili_cookies.json")
    return "; ".join(pairs), csrf


def post_danmaku(room_id, message, cookie_header, csrf, referer_room_id=None):
    referer_room_id = referer_room_id or room_id
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
    request = urllib.request.Request(
        "https://api.live.bilibili.com/msg/send",
        data=urllib.parse.urlencode(data).encode("utf-8"),
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Referer": f"https://live.bilibili.com/{referer_room_id}",
            "Origin": "https://live.bilibili.com",
            "Cookie": cookie_header,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8", errors="ignore")
    return json.loads(body)


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


def main():
    parser = argparse.ArgumentParser(description="Full CovLBCG HTTP sender for authorized Bilibili live-room tests.")
    parser.add_argument("--room", type=int, default=send_policy.DEFAULT_AUTHORIZED_ROOM_ID)
    parser.add_argument("--message", default="hi#")
    parser.add_argument("--replicas", type=int, default=1, help="Temporary FRAGMENT_REPLICAS for this real-room probe.")
    parser.add_argument("--fillers", type=int, default=0, help="Temporary FILLERS_PER_PAYLOAD for this real-room probe.")
    parser.add_argument("--sleep", type=float, default=send_policy.DEFAULT_MIN_SEND_SLEEP)
    parser.add_argument("--min-sleep", type=float, default=send_policy.DEFAULT_MIN_SEND_SLEEP)
    parser.add_argument("--rate-limit-sleep", type=float, default=30.0)
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--max-comments", type=int, default=send_policy.DEFAULT_SEND_MAX_COMMENTS)
    parser.add_argument("--style-file", help="Use a learned template file instead of the default room_comments.txt.")
    parser.add_argument("--fixed-templates", action="store_true", help="Ignore room_comments.txt and use built-in fixed templates.")
    parser.add_argument(
        "--template-payloads",
        action="store_true",
        help="Use learned room templates as payload wrappers instead of the fixed humanized codebook.",
    )
    parser.add_argument("--learn-style", action="store_true", help="Learn the target room style before generating payloads.")
    parser.add_argument("--learn-target-count", type=int, default=80)
    parser.add_argument("--learn-rounds", type=int, default=12)
    parser.add_argument("--learn-sleep", type=float, default=5.0)
    parser.add_argument("--learn-max-len", type=int, default=20)
    parser.add_argument("--style-out-dir", default="room_profiles")
    parser.add_argument("--send", action="store_true", help="Actually send to Bilibili. Omit for dry run.")
    parser.add_argument(
        "--confirm-authorized",
        action="store_true",
        help="Required with --send; confirms this is an authorized test room.",
    )
    parser.add_argument(
        "--authorized-rooms",
        help="Comma/space separated room ids authorized for real sending. Defaults to COVLBCG_AUTHORIZED_ROOMS or 23087172.",
    )
    parser.add_argument(
        "--retry-on-rate-limit",
        action="store_true",
        help="Retry after code 10031. Default is to stop immediately.",
    )
    parser.add_argument("--online-style-learning", action="store_true")
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

    from live_bullet_covert import sender

    random.seed(20260513)
    send_policy.validate_authorized_send_context(
        send=args.send,
        room=args.room,
        confirm_authorized=args.confirm_authorized,
        authorized_rooms_text=args.authorized_rooms,
    )
    validate_explicit_style_file_for_send(args)
    style_learning = apply_online_style_if_requested(args)
    actual_room_id = room_style.room_init(args.room)
    sender.TARGET_ROOM_ID = args.room
    sender.FRAGMENT_REPLICAS = args.replicas
    sender.FILLERS_PER_PAYLOAD = args.fillers
    sender.HUMANIZED_CARRIER_ENABLED = not args.template_payloads
    sender.COMPACT_EMBEDDING_ENABLED = True
    sender.SEMANTIC_EMBEDDING_ENABLED = True
    learned_style = None

    if args.learn_style:
        learned_style = room_style.learn_room_style(
            room_display_id=args.room,
            target_count=args.learn_target_count,
            rounds=args.learn_rounds,
            sleep_sec=args.learn_sleep,
            out_dir=Path(args.style_out_dir),
            activate=False,
            max_len=args.learn_max_len,
        )
        sender.ROOM_COMMENTS_FILE = str(learned_style["paths"]["templates"])
        sender._ROOM_COMMENT_CACHE = None
        sender._ROOM_COMMENT_CACHE_PATH = None
    elif args.fixed_templates:
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

    core = sender.CovLBCG_Core()
    payloads = core.gen_payloads(args.message)
    messages = [sender.JOIN_COMMAND, sender.SYNC_COMMAND]
    messages.extend(payload["c"] for payload in payloads)
    messages.append("fin")
    activity = (style_learning or {}).get("activity", {})
    learning_source_room = (style_learning or {}).get("room_display_id", args.room)
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
        baseline_comments = (style_learning or {}).get("comments") or core.room_comments
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
        baseline_comments = (style_learning or {}).get("comments") or core.room_comments
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
    if learned_style:
        print(f"learn_style=1 sample_count={len(learned_style['comments'])}")
        print(f"style_templates={learned_style['paths']['templates'].resolve()}")
        print(f"style_profile={learned_style['paths']['profile'].resolve()}")
    elif args.fixed_templates:
        print("fixed_templates=1")
    elif args.style_file:
        print(f"style_file={Path(args.style_file).resolve()}")
    print(f"template_payloads={bool(args.template_payloads)}")
    print(f"room_comments_enabled={bool(core.room_comments)} count={len(core.room_comments)}")
    print(f"payload_count={len(payloads)}")
    print(f"total_comments_with_markers={len(messages)}")
    print(f"send_sleep={args.sleep}")
    print(f"min_send_sleep={args.min_sleep}")
    print(f"adaptive_sleep_enabled={bool(args.adaptive_sleep)}")
    print(f"activity_cpm={activity.get('comments_per_minute', 0.0):.2f}")
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

    if not args.send:
        print("dry_run=1; add --send --confirm-authorized to actually send.")
        return

    if not COOKIE_PATH.exists():
        raise SystemExit("bilibili_cookies.json not found")

    cookie_header, csrf = load_cookie_header()
    for index, message in enumerate(messages, 1):
        attempt = 0
        while True:
            attempt += 1
            result = post_danmaku(actual_room_id, message, cookie_header, csrf, referer_room_id=args.room)
            code = result.get("code")
            msg = result.get("message") or result.get("msg")
            retry_note = f" attempt={attempt}" if attempt > 1 else ""
            print(f"[{index}/{len(messages)}] send={message!r} code={code} msg={msg}{retry_note}")
            if code == 0:
                break
            if code == 10031 and not args.retry_on_rate_limit:
                raise SystemExit(f"rate limited; stopping low-disturbance run: {result}")
            if code == 10031 and attempt <= args.max_retries:
                print(f"[rate-limit] waiting {args.rate_limit_sleep:.1f}s before retrying the same comment")
                time.sleep(args.rate_limit_sleep)
                continue
            raise SystemExit(f"send failed: {result}")
        time.sleep(send_sleep)


if __name__ == "__main__":
    main()

