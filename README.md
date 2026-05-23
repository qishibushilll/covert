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

The environment is based on Python 3.12 and the core dependency list is in
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

Optional style gate:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 23087172 --message 'hi#' --replicas 1 --fillers 0 --online-style-learning --adaptive-sleep --style-gate --sleep 10 --min-sleep 10 --max-comments 30
```

The style gate is a conservative send/no-send check. It scores queued comments
against passively collected room samples and can delay or stop a real send when
the batch is far from the current room sample distribution. It does not generate
or rewrite comments.
