import time
from pathlib import Path

from live_bullet_covert import bilibili_ws
from live_bullet_covert import room_style


DEFAULT_ONLINE_STYLE_STAGES = 2
DEFAULT_ONLINE_STYLE_SECONDS = 30
DEFAULT_ONLINE_STYLE_TARGET = 40
DEFAULT_ONLINE_STYLE_MIN_SAMPLES = 12
DEFAULT_ACTIVITY_QUIET_CPM = 5.0
DEFAULT_ACTIVITY_NORMAL_CPM = 20.0
DEFAULT_ACTIVITY_QUIET_MULTIPLIER = 3.0
DEFAULT_ACTIVITY_MODERATE_MULTIPLIER = 1.5


def summarize_activity(stage_summaries):
    observed = sum(stage.get("observed_count", 0) for stage in stage_summaries)
    elapsed = sum(stage.get("elapsed_seconds", 0.0) for stage in stage_summaries)
    usable = sum(stage.get("usable_count", 0) for stage in stage_summaries)
    comments_per_minute = observed / max(1.0, elapsed) * 60.0
    return {
        "observed_count": observed,
        "usable_count": usable,
        "elapsed_seconds": elapsed,
        "comments_per_minute": comments_per_minute,
    }


def conservative_sleep_from_activity(
    *,
    base_sleep,
    min_sleep,
    comments_per_minute,
    quiet_cpm=DEFAULT_ACTIVITY_QUIET_CPM,
    normal_cpm=DEFAULT_ACTIVITY_NORMAL_CPM,
    quiet_multiplier=DEFAULT_ACTIVITY_QUIET_MULTIPLIER,
    moderate_multiplier=DEFAULT_ACTIVITY_MODERATE_MULTIPLIER,
):
    sleep = max(float(base_sleep), float(min_sleep))
    cpm = max(0.0, float(comments_per_minute))
    if cpm < quiet_cpm:
        return sleep * quiet_multiplier
    if cpm < normal_cpm:
        return sleep * moderate_multiplier
    return sleep


def collect_online_stage(room_display_id, room_id, seconds, target_count, max_len, stage_index):
    comments = []
    seen = set()
    observed_count = 0
    started = time.time()

    def on_comment(text, timestamp):
        nonlocal observed_count
        observed_count += 1
        cleaned = room_style.clean_comment(text, max_len=max_len)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            comments.append(cleaned)
            clock = time.strftime("%H:%M:%S", time.localtime(timestamp))
            print(
                f"[online-style] stage={stage_index} learn={len(comments):03d} "
                f"time={clock} text={cleaned}",
                flush=True,
            )
        return len(comments) >= target_count

    bilibili_ws.listen(room_display_id, seconds, on_comment)
    elapsed = max(1.0, time.time() - started)
    return {
        "stage": stage_index,
        "room_display_id": room_display_id,
        "room_id": room_id,
        "comments": comments,
        "observed_count": observed_count,
        "usable_count": len(comments),
        "elapsed_seconds": elapsed,
        "comments_per_minute": observed_count / elapsed * 60.0,
    }


def staged_online_style_learning(
    *,
    room_display_id,
    stages=DEFAULT_ONLINE_STYLE_STAGES,
    seconds=DEFAULT_ONLINE_STYLE_SECONDS,
    target_count=DEFAULT_ONLINE_STYLE_TARGET,
    max_len=40,
    out_dir="data/profiles/online_style_profiles",
    min_samples=DEFAULT_ONLINE_STYLE_MIN_SAMPLES,
    activate=False,
):
    room_id = room_style.room_init(room_display_id)
    all_comments = []
    seen = set()
    stage_summaries = []

    for stage_index in range(1, max(1, int(stages)) + 1):
        stage = collect_online_stage(
            room_display_id=room_display_id,
            room_id=room_id,
            seconds=max(1, int(seconds)),
            target_count=max(1, int(target_count)),
            max_len=max_len,
            stage_index=stage_index,
        )
        for comment in stage["comments"]:
            if comment not in seen:
                seen.add(comment)
                all_comments.append(comment)
        stage_summaries.append({key: value for key, value in stage.items() if key != "comments"})
        print(
            f"[online-style] stage={stage_index} observed={stage['observed_count']} "
            f"usable={stage['usable_count']} cpm={stage['comments_per_minute']:.2f}",
            flush=True,
        )

    activity = summarize_activity(stage_summaries)
    result = None
    if len(all_comments) >= min_samples:
        result = room_style.save_room_style(
            room_display_id=room_display_id,
            room_id=room_id,
            comments=all_comments,
            out_dir=Path(out_dir),
            activate=activate,
        )
        print(
            f"[online-style] saved_templates={result['paths']['templates'].resolve()} "
            f"samples={len(all_comments)}",
            flush=True,
        )
    else:
        print(
            f"[online-style] samples={len(all_comments)} below min_samples={min_samples}; "
            "keeping existing templates",
            flush=True,
        )

    return {
        "room_id": room_id,
        "comments": all_comments,
        "stage_summaries": stage_summaries,
        "activity": activity,
        "style_result": result,
        "templates_path": result["paths"]["templates"] if result else None,
    }
