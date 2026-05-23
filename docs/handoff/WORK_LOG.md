# Work Log

This file is the short restart checkpoint for future Codex sessions.

## Repository

- GitHub: `https://github.com/qishibushilll/covert`
- Branch: `main`
- Local path: `D:\Study\CovLBCG`
- Python: `D:\Study\CovLBCG\.venv\Scripts\python.exe`
- Git proxy for this repo: `http://127.0.0.1:7890`

## Collaboration Rules

- At the start of a new chat, read this file, `README.md`, and `SESSION_HANDOFF.md`.
- Keep `local_secrets/`, `runs/`, `.venv/`, `archive/`, caches, and generated credentials out of Git.
- Do not hard-code cookies, SESSDATA, CSRF tokens, private keys, or browser profiles.
- For substantial changes, update this work log with:
  - date
  - files changed
  - behavioral summary
  - validation commands and results
  - Git commit hash after commit
- For substantial changes, commit and push to GitHub with a meaningful commit message.
- Use `git status --short` before and after edits.

## Current State: 2026-05-23

Project was initialized as a Git repository and pushed to GitHub.

Commit:

```text
b0f9835 Initial project import
```

Published repository:

```text
https://github.com/qishibushilll/covert
```

Important safety cleanup before publishing:

- `.gitignore` excludes `.venv/`, `local_secrets/`, `runs/`, `archive/`, caches, egg-info, logs, pid files, and `.env` files.
- Hard-coded Bilibili `SESSDATA` was removed from active receiver code and replaced with `BILIBILI_SESSDATA`.
- GitHub warned that `figures/concealment_improvement_cn.tiff` is about 87 MB. It is below the 100 MB hard limit but above the recommended 50 MB threshold.

Recent implementation state:

- Added low-disturbance send policy in `src/live_bullet_covert/send_policy.py`.
- Added passive staged online style learning and conservative activity-adaptive spacing in `src/live_bullet_covert/online_style.py`.
- Integrated these controls into:
  - `scripts/bilibili/send_browser_cdp.py`
  - `scripts/bilibili/probes/full_http_sender.py`
- Real sending requires `--send --confirm-authorized`.
- Default real-send guardrails:
  - authorized room default: `23087172`
  - minimum send interval: `10` seconds
  - maximum comments: `30`

Latest validation already run:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m py_compile .\src\live_bullet_covert\online_style.py .\src\live_bullet_covert\send_policy.py .\scripts\bilibili\send_browser_cdp.py .\scripts\bilibili\probes\full_http_sender.py .\tests\offline_baseline_test.py
.\.venv\Scripts\python.exe -X utf8 .\tests\offline_baseline_test.py
```

Both passed.

## Update: 2026-05-23 Work-Log Discipline

Files changed:

- `docs/handoff/WORK_LOG.md`
- `README.md`

Behavioral summary:

- Added a concise restart checkpoint for future Codex sessions.
- Recorded the rule that substantial changes should update this file, then be committed and pushed to GitHub with a meaningful commit message.
- Added a README pointer to the work log.

Validation:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m py_compile .\src\live_bullet_covert\receiver.py .\src\live_bullet_covert\sender.py .\src\live_bullet_covert\online_style.py .\src\live_bullet_covert\send_policy.py
.\.venv\Scripts\python.exe -X utf8 .\tests\offline_baseline_test.py
```

Result: passed.

Commit: `9086f96` introduced this work-log discipline entry.

## Update: 2026-05-23 Conservative Style Gate

Files changed:

- `src/live_bullet_covert/style_gate.py`
- `scripts/bilibili/send_browser_cdp.py`
- `scripts/bilibili/probes/full_http_sender.py`
- `tests/test_style_gate.py`
- `README.md`
- `docs/handoff/WORK_LOG.md`

Behavioral summary:

- Added a conservative style gate that scores queued messages against passively collected room samples.
- The gate can return `pass`, `delay`, `stop`, or `insufficient_samples`.
- The gate only delays or stops real sending when style deviation is high; it does not generate or rewrite comments.
- Integrated the gate into both browser-CDP and HTTP probe sender entry points through `--style-gate`.
- Documented the option in README.

Validation:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m py_compile .\src\live_bullet_covert\style_gate.py .\scripts\bilibili\send_browser_cdp.py .\scripts\bilibili\probes\full_http_sender.py .\tests\test_style_gate.py
.\.venv\Scripts\python.exe -X utf8 .\tests\offline_baseline_test.py
.\.venv\Scripts\python.exe -X utf8 .\tests\test_style_gate.py
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\probes\full_http_sender.py --room 23087172 --message hi# --replicas 1 --fillers 0 --sleep 10 --style-gate --style-file data\profiles\popular_style_profiles_ws\popular_templates.txt --max-comments 30
```

Result: passed. The dry-run style gate reported `status=pass`; no real send was performed.

Commit: `7067204`
