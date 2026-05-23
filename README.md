# Live Bullet Covert

This project contains the implementation and revision experiments for a live
bullet-comment covert communication framework.

## Layout

- `src/live_bullet_covert/`: main sender, receiver and platform helpers.
- `scripts/bilibili/`: real-platform Bilibili learning, sender and receiver entry points.
- `experiments/`: detectability, robustness, baseline and trade-off experiments.
- `tests/`: local regression tests.
- `docs/`: manuscript revision and reviewer-response materials.
- `data/`: non-secret learned style profiles and example inputs.
- `figures/`: publication figures and source data.
- `runs/`: generated logs from local and platform runs.
- `local_secrets/`: cookies, Chrome profiles and local keys. Do not publish this directory.
- `archive/`: historical prototypes and old run scripts retained for reference.

## Python

Use the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -X utf8
```

The environment is based on Python 3.13 and the core dependency list is in
`requirements.txt`.

Install/update the editable package after structural changes:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pip install -e .
```

## Core Checks

```powershell
.\.venv\Scripts\python.exe -X utf8 -m py_compile .\src\live_bullet_covert\sender.py .\src\live_bullet_covert\receiver.py
.\.venv\Scripts\python.exe -X utf8 .\tests\offline_baseline_test.py
.\.venv\Scripts\python.exe -X utf8 .\experiments\detectability_baseline.py
```

## Work Log

For future Codex sessions, start from `docs/handoff/WORK_LOG.md`,
`SESSION_HANDOFF.md`, and this README. Substantial changes should update the
work log, then be committed and pushed to GitHub with a meaningful commit
message.

## Minimal Authorized Bilibili Demo

Receiver:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\receive_ws_decode.py --room 23087172 --seconds 180
```

Sender:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 23087172 --message 'hi#' --replicas 1 --fillers 0 --sleep 10 --page-wait 35 --warmup-count 1 --max-comments 30 --port 9342 --user-data-dir local_secrets\chrome_profiles\chrome_cdp_profile_23087172_humanized_demo --send --confirm-authorized
```

Run real-platform tests only in authorized rooms. Real sending is guarded by a
low-disturbance policy: default authorized room `23087172`, default minimum send
interval `10` seconds, default maximum `30` comments, and explicit
`--confirm-authorized` for `--send`.

Optional passive online style learning and conservative activity-adaptive
spacing:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 23087172 --message 'hi#' --replicas 1 --fillers 0 --online-style-learning --online-style-stages 2 --online-style-seconds 30 --adaptive-sleep --sleep 10 --min-sleep 10 --max-comments 30 --send --confirm-authorized
```

The adaptive spacing is conservative: observed low room activity can increase
the interval, but the sender will not go below `--min-sleep`.

To learn activity from a separate source room while sending only to the
authorized room, keep `--room` as the authorized send room and add
`--online-style-source-room`:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 23087172 --online-style-source-room 7243837 --message 'hi#' --replicas 1 --fillers 0 --online-style-learning --online-style-stages 2 --online-style-seconds 30 --adaptive-sleep --sleep 10 --min-sleep 10 --max-comments 30
```

When the source room differs from the send room, learned source-room templates
are used only for pacing and audit baselines. They are not applied as send-room
comment templates.

For lower startup latency, use realtime online style monitoring instead of the
blocking staged learner. This starts sending setup immediately while a
background listener learns the source-room activity and adjusts later inter-send
sleep values from the latest observed CPM:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 23087172 --online-style-source-room 6 --message 'hi#' --replicas 1 --fillers 0 --realtime-online-style --realtime-online-style-seconds 900 --adaptive-sleep --sleep 10 --min-sleep 10 --max-comments 30
```

Realtime monitoring does not change payload text by itself. By default it only
updates activity pacing, style-gate baselines, LLM-audit baselines, and saved
source-room profiles. To rebuild payload comments from samples learned during
the same run, add `--realtime-template-payloads`; the browser sender rebuilds
the payload queue after the page wait and prints `preview_rebuilt`. Real sends
with realtime template payloads are allowed only when the realtime source room
matches `--room`.

Payload comments use the built-in humanized codebook by default. To explicitly
wrap compact carrier records in a learned template file during a dry run or an
authorized same-room test, add `--template-payloads --style-file <path>`.
For real sends, `room_<id>_templates.txt`, `room_<id>_comments.txt`, and
`room_<id>_profile.json` paths are rejected when their room id differs from
`--room`; cross-room templates remain dry-run only.

Optional style gate:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 23087172 --message 'hi#' --replicas 1 --fillers 0 --online-style-learning --adaptive-sleep --style-gate --sleep 10 --min-sleep 10 --max-comments 30
```

The style gate is a conservative send/no-send check. It scores queued comments
against passively collected room samples and can delay or stop a real send when
the batch is far from the current room sample distribution. It does not generate
or rewrite comments.

Optional LLM style audit:

```powershell
$env:COVLBCG_LLM_STYLE_AUDIT_ENDPOINT="https://your-openai-compatible-endpoint/v1/chat/completions"
$env:COVLBCG_LLM_STYLE_AUDIT_API_KEY="..."
$env:COVLBCG_LLM_STYLE_AUDIT_MODEL="your-model"
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 23087172 --message 'hi#' --replicas 1 --fillers 0 --online-style-learning --adaptive-sleep --style-gate --llm-style-audit --sleep 10 --min-sleep 10 --max-comments 30
```

The LLM audit is also a gate only. The prompt and parser reject generated,
rewritten, or candidate chat messages. The allowed outcomes are `pass`, `delay`,
or `stop`.
