import time
import re
import threading
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
ROOM_STYLE_FILE_RE = re.compile(r"(?:^|[\\/])room_(\d+)_(?:comments|templates|profile)\.")


def resolve_source_room(send_room_display_id, source_room_display_id=None):
    if source_room_display_id is None:
        return int(send_room_display_id)
    return int(source_room_display_id)


def is_same_room(left_room_display_id, right_room_display_id):
    return int(left_room_display_id) == int(right_room_display_id)


def should_apply_learned_templates(send_room_display_id, source_room_display_id, templates_path):
    return bool(templates_path) and is_same_room(send_room_display_id, source_room_display_id)


def style_file_room_id(style_file):
    if not style_file:
        return None
    match = ROOM_STYLE_FILE_RE.search(str(style_file).replace("\\", "/"))
    if not match:
        return None
    return int(match.group(1))


def validate_style_file_for_send(*, send_room_display_id, style_file, send=False):
    source_room = style_file_room_id(style_file)
    if source_room is None:
        return
    if send and not is_same_room(send_room_display_id, source_room):
        raise ValueError(
            f"refusing --send with style_file learned from room {source_room}; "
            f"send room is {send_room_display_id}"
        )


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


class RealtimeStyleMonitor:
    def __init__(
        self,
        *,
        room_display_id,
        room_id=None,
        max_len=40,
        out_dir="data/profiles/online_style_profiles",
        min_samples=DEFAULT_ONLINE_STYLE_MIN_SAMPLES,
        target_count=DEFAULT_ONLINE_STYLE_TARGET,
        max_seconds=3600,
        activate=False,
        default_cpm=DEFAULT_ACTIVITY_NORMAL_CPM,
    ):
        self.room_display_id = int(room_display_id)
        self.room_id = room_id
        self.max_len = max_len
        self.out_dir = out_dir
        self.min_samples = int(min_samples)
        self.target_count = int(target_count) if target_count else 0
        self.max_seconds = int(max_seconds)
        self.activate = activate
        self.default_cpm = float(default_cpm)
        self.started_at = None
        self.observed_count = 0
        self.comments = []
        self.seen = set()
        self.errors = []
        self.style_result = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return self
        self.started_at = time.time()
        self._thread = threading.Thread(target=self._run, name="online-style-rt", daemon=True)
        self._thread.start()
        return self

    def stop(self, timeout=5.0):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(0.1, float(timeout)))

    def _run(self):
        try:
            bilibili_ws.listen(
                self.room_display_id,
                max(1, self.max_seconds),
                self._on_comment,
                should_stop=self._stop.is_set,
            )
        except Exception as exc:
            with self._lock:
                self.errors.append(str(exc))
            print(f"[online-style-rt] listen failed: {exc}", flush=True)

    def _on_comment(self, text, timestamp):
        cleaned = room_style.clean_comment(text, max_len=self.max_len)
        learned_count = None
        comments_per_minute = None
        with self._lock:
            self.observed_count += 1
            if cleaned and cleaned not in self.seen:
                if not self.target_count or len(self.comments) < self.target_count:
                    self.seen.add(cleaned)
                    self.comments.append(cleaned)
                    learned_count = len(self.comments)
                    comments_per_minute = self._comments_per_minute_locked(time.time())
        if learned_count is not None:
            clock = time.strftime("%H:%M:%S", time.localtime(timestamp))
            print(
                f"[online-style-rt] learn={learned_count:03d} "
                f"cpm={comments_per_minute:.2f} time={clock} text={cleaned}",
                flush=True,
            )
        return False

    def _comments_per_minute_locked(self, now):
        elapsed = max(1.0, now - (self.started_at or now))
        return self.observed_count / elapsed * 60.0

    def snapshot(self):
        now = time.time()
        with self._lock:
            comments_per_minute = self._comments_per_minute_locked(now)
            pacing_cpm = comments_per_minute if self.observed_count else self.default_cpm
            return {
                "room_display_id": self.room_display_id,
                "room_id": self.room_id or self.room_display_id,
                "comments": list(self.comments),
                "activity": {
                    "observed_count": self.observed_count,
                    "usable_count": len(self.comments),
                    "elapsed_seconds": max(1.0, now - (self.started_at or now)),
                    "comments_per_minute": comments_per_minute,
                    "pacing_comments_per_minute": pacing_cpm,
                },
                "errors": list(self.errors),
                "templates_path": (
                    self.style_result["paths"]["templates"]
                    if self.style_result
                    else None
                ),
                "style_result": self.style_result,
            }

    def stop_and_save(self):
        self.stop()
        snapshot = self.snapshot()
        comments = snapshot["comments"]
        if len(comments) >= self.min_samples:
            room_id = snapshot["room_id"]
            if self.room_id is None:
                try:
                    room_id = room_style.room_init(self.room_display_id)
                    self.room_id = room_id
                except Exception as exc:
                    with self._lock:
                        self.errors.append(str(exc))
                    print(f"[online-style-rt] room_init before save failed: {exc}", flush=True)
            self.style_result = room_style.save_room_style(
                room_display_id=self.room_display_id,
                room_id=room_id,
                comments=comments,
                out_dir=Path(self.out_dir),
                activate=self.activate,
            )
            print(
                f"[online-style-rt] saved_templates={self.style_result['paths']['templates'].resolve()} "
                f"samples={len(comments)}",
                flush=True,
            )
        else:
            print(
                f"[online-style-rt] samples={len(comments)} below min_samples={self.min_samples}; "
                "keeping existing templates",
                flush=True,
            )
        return self.snapshot()


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
        "room_display_id": room_display_id,
        "room_id": room_id,
        "comments": all_comments,
        "stage_summaries": stage_summaries,
        "activity": activity,
        "style_result": result,
        "templates_path": result["paths"]["templates"] if result else None,
    }
