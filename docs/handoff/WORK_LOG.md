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

## Update: 2026-05-23 LLM Style Audit Gate

Files changed:

- `src/live_bullet_covert/llm_style_audit.py`
- `scripts/bilibili/send_browser_cdp.py`
- `scripts/bilibili/probes/full_http_sender.py`
- `tests/test_llm_style_audit.py`
- `README.md`
- `docs/handoff/WORK_LOG.md`

Behavioral summary:

- Recreated `.venv` with `C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe` because the old virtual environment pointed at missing `Python312`.
- Reinstalled project dependencies with `pip install -r requirements.txt -e .`.
- Added an optional OpenAI-compatible LLM style audit gate.
- The audit can only return `pass`, `delay`, or `stop`; it is not used to generate, rewrite, improve, paraphrase, or suggest chat messages.
- The parser rejects LLM responses containing generated, rewritten, candidate, replacement, or suggestion fields.
- Integrated the audit gate into both browser-CDP and HTTP probe sender entry points through `--llm-style-audit`.
- Real sending still requires `--send --confirm-authorized`; audit `stop` prevents real sending and audit `delay` only increases spacing.

Validation:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 -m py_compile '.\src\live_bullet_covert\llm_style_audit.py' '.\src\live_bullet_covert\style_gate.py' '.\scripts\bilibili\send_browser_cdp.py' '.\scripts\bilibili\probes\full_http_sender.py' '.\tests\test_llm_style_audit.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_llm_style_audit.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_style_gate.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\offline_baseline_test.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\scripts\bilibili\probes\full_http_sender.py' --room 23087172 --message 'hi#' --replicas 1 --fillers 0 --sleep 10 --style-gate --llm-style-audit --llm-style-audit-min-samples 999 --style-file '.\data\profiles\popular_style_profiles_ws\popular_templates.txt' --max-comments 30
```

Result: passed. The dry-run did not use `--send`; no real send was performed. The LLM audit path returned `status=stop` before any model call because the test threshold required 999 baseline samples.

Commit: `ea587dc`

## Update: 2026-05-23 Cross-Room Learning Source

Files changed:

- `src/live_bullet_covert/online_style.py`
- `scripts/bilibili/send_browser_cdp.py`
- `scripts/bilibili/probes/full_http_sender.py`
- `tests/test_online_style.py`
- `README.md`
- `docs/handoff/WORK_LOG.md`

Behavioral summary:

- Added `--online-style-source-room` to passively learn activity from a separate room while keeping real sends targeted at `--room`.
- Intended usage for the current test setup: learn from room `7243837`, send only to authorized room `23087172`.
- Cross-room learning is conservative: source-room activity can only influence pacing/audit baselines; source-room templates are not applied as send-room templates.
- Existing authorization checks still run against `--room`, and real sending still requires `--send --confirm-authorized`.
- Updated README to note the active `.venv` is Python 3.13.

Validation:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 -m py_compile '.\src\live_bullet_covert\online_style.py' '.\scripts\bilibili\send_browser_cdp.py' '.\scripts\bilibili\probes\full_http_sender.py' '.\tests\test_online_style.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_online_style.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_style_gate.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_llm_style_audit.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\scripts\bilibili\probes\full_http_sender.py' --room 23087172 --online-style-source-room 7243837 --message 'hi#' --replicas 1 --fillers 0 --sleep 10 --online-style-learning --online-style-stages 1 --online-style-seconds 1 --online-style-target 1 --online-style-min-samples 999 --adaptive-sleep --max-comments 30
```

Result: passed. The dry-run showed `room_display_id=23087172`, `online_style_source_room=7243837`, and `effective_send_sleep=30.00`; no real send was performed.

Commit: `c8d7ec8`

## Test: 2026-05-23 Cross-Room Live Send Trial

Files changed:

- `docs/handoff/WORK_LOG.md`

Purpose:

- Real-platform test for cross-room learning: passively learn from room `7243837`, then send only to authorized room `23087172`.
- Verify that learned source-room activity controls send spacing.

Commands/results:

```powershell
# Receiver listener, started first.
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 'scripts\bilibili\receive_ws_decode.py' --room 23087172 --seconds 900

# Trial 1: with style gate.
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 'scripts\bilibili\send_browser_cdp.py' --room 23087172 --online-style-source-room 7243837 --message 'hi#' --replicas 1 --fillers 0 --online-style-learning --online-style-stages 1 --online-style-seconds 30 --online-style-target 20 --online-style-min-samples 8 --adaptive-sleep --style-gate --sleep 10 --min-sleep 10 --page-wait 35 --warmup-count 1 --max-comments 30 --port 9342 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_23087172_humanized_demo' --send --confirm-authorized

# Trial 2: pacing-only, without style-gate blocking.
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 'scripts\bilibili\send_browser_cdp.py' --room 23087172 --online-style-source-room 7243837 --message 'hi#' --replicas 1 --fillers 0 --online-style-learning --online-style-stages 1 --online-style-seconds 30 --online-style-target 20 --online-style-min-samples 8 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 35 --warmup-count 1 --max-comments 30 --port 9342 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_23087172_humanized_demo' --send --confirm-authorized
```

Observed logs:

- `runs/logs/recv_23087172_20260523_100847.log`
- `runs/logs/send_cdp_crossroom_20260523_101053.log`
- `runs/logs/send_cdp_crossroom_20260523_101053.err.log`
- `runs/logs/send_cdp_crossroom_real_20260523_101338.log`
- `runs/logs/send_cdp_crossroom_real_20260523_101338.err.log`

Outcome:

- Trial 1 learned `0` samples from `7243837` in 30 seconds. `style-gate` reported `status=insufficient_samples` and stopped real sending before the browser send phase.
- Trial 2 learned `3` samples from `7243837`, `activity_cpm=5.84`, and computed `effective_send_sleep=15.00` from base sleep `10`. This confirms source-room activity controlled pacing.
- Trial 2 targeted `room_display_id=23087172` and reported browser input detection success.
- Trial 2 sent all `17/17` comments with `result={'ok': True}` and no stderr output.
- Receiver observed `JOIN`, `CAL`, and `3` identifiable humanized payload comments, but did not observe `fin` or complete a final decode. Next debugging target is receiver/platform visibility for humanized payloads, not the cross-room pacing path.

Commit: `55fe71f`

## Update: 2026-05-23 Receiver Diagnostics and Successful Decode

Files changed:

- `src/live_bullet_covert/bilibili_ws.py`
- `scripts/bilibili/receive_ws_decode.py`
- `tests/test_receiver_humanized.py`
- `data/profiles/online_style_profiles/room_7243837_comments.txt`
- `data/profiles/online_style_profiles/room_7243837_templates.txt`
- `data/profiles/online_style_profiles/room_7243837_profile.json`
- `docs/handoff/WORK_LOG.md`

Behavioral summary:

- Investigated why the user saw all 17 comments in the live room while the receiver did not decode.
- Confirmed offline that all 14 humanized payload comments from `send_cdp_crossroom_real_20260523_101338.log` are decodable by `receiver.CovLBCG_Decoder`.
- Updated the raw WebSocket listener to load cookies from `local_secrets/bilibili_cookies.json` and to parse brotli-compressed Bilibili message packets when `brotli` is installed.
- Added receiver diagnostic flags:
  - `--log-all`: print every observed comment with carrier detection status.
  - `--collect-after-sync`: after `CAL`, collect every observed comment until `fin` so receiver-side missed detection is visible.
- Added `tests/test_receiver_humanized.py` covering the real 14 payload comments from the cross-room run.

Validation:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 -m py_compile '.\src\live_bullet_covert\bilibili_ws.py' '.\scripts\bilibili\receive_ws_decode.py' '.\tests\test_receiver_humanized.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_receiver_humanized.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\offline_baseline_test.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_online_style.py'
```

Result: passed.

Live diagnostic trial:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 'scripts\bilibili\receive_ws_decode.py' --room 23087172 --seconds 900 --log-all --collect-after-sync
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 'scripts\bilibili\send_browser_cdp.py' --room 23087172 --online-style-source-room 7243837 --message 'a#' --replicas 1 --fillers 0 --online-style-learning --online-style-stages 1 --online-style-seconds 20 --online-style-target 10 --online-style-min-samples 8 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 35 --warmup-count 1 --max-comments 30 --port 9343 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_23087172_humanized_demo' --send --confirm-authorized
```

Observed logs:

- `runs/logs/recv_diag_23087172_20260523_105331.log`
- `runs/logs/send_diag_crossroom_20260523_105425.log`

Live result:

- Source room `7243837` produced `8` samples in 20 seconds, `activity_cpm=22.49`, so `effective_send_sleep=10.00`.
- Sender targeted authorized room `23087172` and sent all `17/17` comments successfully.
- Enhanced receiver observed `JOIN`, `CAL`, all `14/14` humanized payload comments, and `fin`.
- Receiver decoded successfully: `a`.
- Conclusion: the previous failure was receiver-side collection/diagnostic weakness, not the payloads being undecodable. The user-visible 17 comments were valid; the old receiver did not reliably capture/decode the full sequence.

Commit: `7e15e72`

## Update: 2026-05-23 Template Payload Guardrails

Files changed:

- `src/live_bullet_covert/online_style.py`
- `scripts/bilibili/send_browser_cdp.py`
- `scripts/bilibili/probes/full_http_sender.py`
- `tests/test_online_style.py`
- `tests/test_sender_payload_modes.py`
- `README.md`
- `docs/handoff/WORK_LOG.md`

Behavioral summary:

- Added `--template-payloads` to both sender entry points. Default payloads remain the built-in humanized codebook; the new flag explicitly switches payloads back to learned-template wrappers carrying compact records.
- Real sends now reject explicit `room_<id>_templates.txt`, `room_<id>_comments.txt`, or `room_<id>_profile.json` style paths when the learned room id differs from `--room`.
- The explicit style-file guard runs before online learning, room initialization, browser launch, or HTTP sending, so a cross-room style file is rejected before touching the platform.
- Cross-room learned templates are still allowed for dry runs and still used only for pacing/audit baselines when learned through `--online-style-source-room`.

Validation:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 -m py_compile '.\src\live_bullet_covert\online_style.py' '.\scripts\bilibili\send_browser_cdp.py' '.\scripts\bilibili\probes\full_http_sender.py' '.\tests\test_online_style.py' '.\tests\test_sender_payload_modes.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_online_style.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_sender_payload_modes.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\offline_baseline_test.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_style_gate.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_llm_style_audit.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_receiver_humanized.py'
```

Result: passed.

CLI guard smoke tests:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\scripts\bilibili\probes\full_http_sender.py' --room 23087172 --message 'a#' --replicas 1 --fillers 0 --sleep 10 --style-file '.\data\profiles\online_style_profiles\room_7243837_templates.txt' --template-payloads --max-comments 30 --send --confirm-authorized
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\scripts\bilibili\send_browser_cdp.py' --room 23087172 --message 'a#' --replicas 1 --fillers 0 --sleep 10 --style-file '.\data\profiles\online_style_profiles\room_7243837_templates.txt' --template-payloads --max-comments 30 --send --confirm-authorized
```

Both exited before network/browser work with:

```text
refusing --send with style_file learned from room 7243837; send room is 23087172
```

Environment note:

- Inside the filesystem sandbox, direct `.venv` invocations can report missing base Python `C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe`.
- The same `.venv` works when run outside the sandbox, so this is a sandbox path-visibility issue, not a project virtualenv failure.
- Final validation used `.venv` outside the sandbox.

Commit: `d6acdf2`

## Test: 2026-05-23 Popular Room 6 Learning and Authorized Send

Files changed:

- `data/profiles/online_style_profiles/room_6_comments.txt`
- `data/profiles/online_style_profiles/room_6_templates.txt`
- `data/profiles/online_style_profiles/room_6_profile.json`
- `docs/handoff/WORK_LOG.md`

Purpose:

- Learn template samples and activity from active Bilibili League of Legends room `6`.
- Send only to authorized test room `23087172`; no comments were sent to room `6`.
- Verify that source-room activity controls pacing and that the authorized-room send decodes end to end.

Commands:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 'scripts\bilibili\receive_ws_decode.py' --room 23087172 --seconds 900 --log-all --collect-after-sync
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 'scripts\bilibili\send_browser_cdp.py' --room 23087172 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --online-style-learning --online-style-stages 3 --online-style-seconds 60 --online-style-target 80 --online-style-min-samples 20 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 45 --warmup-count 1 --max-comments 30 --port 9345 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_23087172_room6_popularfreq' --send --confirm-authorized
```

Observed logs:

- `runs/logs/send_popular_room6_20260523_160003.log`
- `runs/logs/send_popular_room6_20260523_160003.err.log`
- `runs/logs/recv_popularfreq_23087172_20260523_155414.log`
- `runs/logs/recv_popularfreq_23087172_20260523_155414.err.log`

Outcome:

- Stage 1 from source room `6`: `observed=38`, `usable=29`, `cpm=37.33`.
- Stage 2 from source room `6`: `observed=36`, `usable=33`, `cpm=35.52`.
- Stage 3 from source room `6`: `observed=69`, `usable=60`, `cpm=67.77`.
- Saved `116` source-room samples to `data/profiles/online_style_profiles/room_6_templates.txt`.
- Aggregate `activity_cpm=46.89`; `effective_send_sleep=10.00`, because source-room activity was above normal and the sender never goes below `--min-sleep`.
- Cross-room templates were kept for pacing/audit only; payloads used the default humanized codebook (`template_payloads=False`).
- Browser-CDP send to room `23087172` completed `17/17` comments with `result={'ok': True}` and empty stderr.
- Receiver collected `14/14` humanized payload comments, observed `fin`, and decoded successfully: `a`.

Commit: `e9adb80`

## Update: 2026-05-23 Realtime Online Style Monitoring

Files changed:

- `src/live_bullet_covert/bilibili_ws.py`
- `src/live_bullet_covert/online_style.py`
- `scripts/bilibili/send_browser_cdp.py`
- `scripts/bilibili/probes/full_http_sender.py`
- `tests/test_online_style.py`
- `README.md`
- `docs/handoff/WORK_LOG.md`

Behavioral summary:

- Added `--realtime-online-style` as a non-blocking alternative to `--online-style-learning`.
- The realtime mode starts a background source-room listener and immediately proceeds with payload generation, browser setup, and dry-run/send preparation.
- Before each sent comment, the sender recomputes conservative sleep from the latest observed source-room CPM. If no samples have arrived yet, pacing falls back to the configured normal CPM instead of treating the room as quiet.
- Realtime learning saves source-room templates at shutdown when enough samples were collected.
- `--realtime-online-style` is mutually exclusive with staged `--online-style-learning` and `--fixed-templates`.

Validation:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 -m py_compile '.\src\live_bullet_covert\online_style.py' '.\src\live_bullet_covert\bilibili_ws.py' '.\scripts\bilibili\send_browser_cdp.py' '.\scripts\bilibili\probes\full_http_sender.py' '.\tests\test_online_style.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_online_style.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_sender_payload_modes.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\offline_baseline_test.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_style_gate.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_llm_style_audit.py'
```

Dry-run smoke test:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\scripts\bilibili\send_browser_cdp.py' --room 23087172 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --realtime-online-style --realtime-online-style-seconds 20 --online-style-target 10 --online-style-min-samples 999 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 3 --warmup-count 1 --max-comments 30 --port 9346 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_23087172_realtime_dryrun'
```

Result:

- Passed.
- The dry-run entered payload generation and browser preview immediately, without waiting for the 20-second realtime learning window to finish.
- No real send was performed.

Commit: `9065558`

## Update: 2026-05-23 Realtime Template Payload Rebuild

Files changed:

- `src/live_bullet_covert/online_style.py`
- `src/live_bullet_covert/sender.py`
- `scripts/bilibili/send_browser_cdp.py`
- `scripts/bilibili/probes/full_http_sender.py`
- `tests/test_online_style.py`
- `tests/test_sender_payload_modes.py`
- `README.md`
- `docs/handoff/WORK_LOG.md`

Behavioral summary:

- Clarified realtime online style monitoring semantics: by default it only
  affects pacing/audit baselines and saved profiles, not payload text.
- Added `--realtime-template-payloads` plus sample threshold/wait controls.
  With the browser/CDP sender, this rebuilds the payload queue after the page
  wait using realtime samples collected in the same run, then prints
  `preview_rebuilt` before dry-run/send.
- Real sends with realtime template payloads are guarded by a same-room check:
  `source_room` must equal `--room`. Cross-room realtime templates are rejected
  for real sends just like cross-room style files.
- `CovLBCG_Core` can now accept in-memory room comments, so realtime samples do
  not have to be written to a template file before use.

Validation:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 -m py_compile '.\src\live_bullet_covert\online_style.py' '.\src\live_bullet_covert\sender.py' '.\scripts\bilibili\send_browser_cdp.py' '.\scripts\bilibili\probes\full_http_sender.py' '.\tests\test_online_style.py' '.\tests\test_sender_payload_modes.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_online_style.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_sender_payload_modes.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\offline_baseline_test.py'
```

Result: passed.

Dry-run smoke test:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\scripts\bilibili\send_browser_cdp.py' --room 6 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --realtime-online-style --realtime-template-payloads --realtime-template-min-samples 4 --realtime-template-wait 20 --realtime-online-style-seconds 60 --online-style-target 20 --online-style-min-samples 999 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 5 --warmup-count 1 --max-comments 30 --port 9349 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_room6_realtime_templates_dryrun'
```

Result:

- No `--send`; no comments were sent.
- Initial `preview` still showed the default humanized codebook because it is
  generated before browser setup.
- After page wait, realtime samples from room `6` were available and the sender
  rebuilt payloads with `realtime_template_payloads_active=True`.
- `preview_rebuilt` used current-room samples from the same run, including
  examples like `神人`, `贪吃`, `幻视AL打T1`, and `大树来抓一波就炸了`.
- Port `9349` was free after the run.

## Update: 2026-05-23 Live Chat Input Guard and Realtime Template Filtering

Files changed:

- `src/live_bullet_covert/browser_cdp.py`
- `src/live_bullet_covert/sender.py`
- `scripts/bilibili/send_browser_cdp.py`
- `scripts/bilibili/probes/full_http_sender.py`
- `tests/test_online_style.py`
- `tests/test_sender_payload_modes.py`
- `README.md`
- `docs/handoff/WORK_LOG.md`
- `NEW_CHAT_HANDOFF_CN.md`
- `SESSION_HANDOFF.md`

Root cause of the latest failed room-6 test:

- The sender log showed `input_candidates` contained only
  `INPUT cls=nav-search-input`.
- Browser sends reported `ok=True` because text was inserted into the top search
  input, not the live chat input.
- The receiver kept listening but could not decode because `CAL`, payload
  comments, and `fin` never entered the public live chat.
- The unnatural `preview_rebuilt` texts were caused by using too-short or
  emoji-only realtime samples as wrappers, then appending/splitting a four-char
  compact carrier record.

Behavioral summary:

- `browser_cdp.FIND_INPUT_JS` now marks candidates with `is_chat_input` and
  `is_search`.
- `browser_cdp.FOCUS_INPUT_JS` only focuses recognized live-chat inputs and no
  longer falls back to arbitrary text inputs.
- `send_browser_cdp.py` refuses `--send` if no visible live-chat input is found.
- Realtime template rebuilds now filter samples before use. Very short,
  emoji-only, duplicate, and punctuation-heavy comments are rejected.
- If too few usable realtime samples remain, real sends stop instead of falling
  back to an unnatural template-payload preview.
- Compact payload generation now prefers longer wrappers, spreads carrier
  punctuation internally, and rejects payloads with a trailing carrier cluster.

Validation:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 -m py_compile '.\src\live_bullet_covert\browser_cdp.py' '.\src\live_bullet_covert\sender.py' '.\scripts\bilibili\send_browser_cdp.py' '.\scripts\bilibili\probes\full_http_sender.py' '.\tests\test_sender_payload_modes.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_sender_payload_modes.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\offline_baseline_test.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_online_style.py'
```

Result: passed.

Room-6 dry-run verification, no send:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 6 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --realtime-online-style --realtime-template-payloads --realtime-template-min-samples 4 --realtime-template-wait 10 --realtime-online-style-seconds 30 --online-style-target 20 --online-style-min-samples 999 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 5 --warmup-count 1 --max-comments 30 --port 9353 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_room6_guard_dryrun'
```

Observed result:

- `input_candidates` showed only `nav-search-input` with
  `is_chat_input=False` and `is_search=True`.
- The realtime run collected raw samples but had `0` usable long wrappers after
  filtering in that short window.
- Because the run was a dry run, it printed
  `realtime usable template samples insufficient after filtering` and did not
  send.
- With `--send`, the same visible-input state would stop before sending.

Important local state:

- `src/live_bullet_covert/send_policy.py` may contain a user-local
  `DEFAULT_AUTHORIZED_ROOM_ID = 6` change. Do not commit or overwrite that
  unless the user explicitly asks.
- Run-generated files under
  `data/profiles/online_style_profiles/room_6_*` are still local data changes
  and should not be mixed into code commits.

Commit: `9b9d443`

## Update: 2026-05-24 Resolved-Room Navigation and Input Wait

Files changed:

- `src/live_bullet_covert/browser_cdp.py`
- `scripts/bilibili/send_browser_cdp.py`
- `README.md`
- `docs/handoff/WORK_LOG.md`
- `NEW_CHAT_HANDOFF_CN.md`
- `SESSION_HANDOFF.md`

Root cause of the latest `live chat input not found` report:

- Room display id `6` currently renders a Bilibili LPL赛事/活动 outer page.
- The normal live-room UI is inside an iframe pointing at
  `https://live.bilibili.com/blanc/7734200?liteVersion=true`.
- A fixed post-navigation sleep can run before the iframe exposes the real
  `TEXTAREA.chat-input`; at that moment only `nav-search-input` is visible.

Behavioral summary:

- `browser_cdp` input discovery now scans same-origin iframes, shadow roots,
  `[contenteditable]`, and `role=textbox`, and can print hidden/all candidates
  plus page diagnostics.
- `send_browser_cdp.py` now navigates Chrome to the resolved actual room id
  returned by `room_style.room_init()`, so `--room 6` opens
  `https://live.bilibili.com/7734200` instead of staying on the outer display
  room page.
- Added `--input-wait` and `--input-poll`; after `--page-wait`, the sender
  polls for a visible live-chat input before deciding that the page is not
  ready.
- The send refusal is still intact: if no chat input is visible after polling,
  real `--send` stops and prints diagnostics instead of using the search box.

Validation:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 -m py_compile '.\src\live_bullet_covert\browser_cdp.py' '.\scripts\bilibili\send_browser_cdp.py' '.\scripts\bilibili\probes\full_http_sender.py' '.\tests\test_sender_payload_modes.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_sender_payload_modes.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_online_style.py'
```

Result: passed.

Room-6 dry-run, no send:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\scripts\bilibili\send_browser_cdp.py' --room 6 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --realtime-online-style --realtime-template-payloads --realtime-template-min-samples 4 --realtime-template-wait 5 --realtime-online-style-seconds 20 --online-style-target 20 --online-style-min-samples 999 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 8 --input-wait 30 --warmup-count 1 --max-comments 30 --port 9358 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_room6_waitinput_dryrun'
```

Observed result:

- `room_display_id=6`, `room_id=7734200`.
- Browser navigated to `https://live.bilibili.com/7734200`.
- `input_candidates` included the real iframe chat box:
  `TEXTAREA cls='chat-input border-box' placeholder='发个弹幕呗~' is_chat_input=True`.
- No `--send` was used; no comments were sent.
- Realtime template rebuild still correctly refused when usable long wrappers
  were only `3/4` in that short sampling window.

Commit: `12ff6bf`

## Update: 2026-05-24 Auto Same-Room Realtime Payload Rebuild

Files changed:

- `src/live_bullet_covert/online_style.py`
- `src/live_bullet_covert/sender.py`
- `scripts/bilibili/send_browser_cdp.py`
- `scripts/bilibili/probes/full_http_sender.py`
- `tests/test_sender_payload_modes.py`
- `README.md`
- `docs/handoff/WORK_LOG.md`
- `NEW_CHAT_HANDOFF_CN.md`
- `SESSION_HANDOFF.md`

Root cause of the latest user report:

- The user command included `--realtime-online-style` but did not include
  `--realtime-template-payloads`.
- The log explicitly showed `realtime_template_payloads=False`, so outgoing
  payload text used the built-in humanized codebook and looked like the old
  templates.
- Receiver logs with `carrier=unknown code=` were consistent with the visible
  stream not carrying a recognizable payload sequence from that old-template
  run.

Behavioral summary:

- Browser and HTTP senders now auto-enable realtime template payload rebuilds
  when `--realtime-online-style` learns from the same room as `--room`.
- Default realtime template threshold is now `4` high-quality payload wrappers,
  with a default wait of `60` seconds.
- Rebuild now waits for usable payload wrappers after filtering, not only raw
  realtime comments.
- Payload-wrapper filtering is stricter than profile saving: it rejects very
  short comments, emoji/emote-tag comments, long ASCII runs, and punctuation-
  heavy samples before they can become payload wrappers.
- If not enough usable wrappers are available, real sends stop instead of
  falling back to the old built-in preview.
- Compact carrier insertion avoids splitting ASCII words and preserves word
  boundaries when removing existing punctuation.

Validation:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 -m py_compile '.\src\live_bullet_covert\online_style.py' '.\src\live_bullet_covert\sender.py' '.\scripts\bilibili\send_browser_cdp.py' '.\scripts\bilibili\probes\full_http_sender.py' '.\tests\test_sender_payload_modes.py' '.\tests\test_online_style.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_sender_payload_modes.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\offline_baseline_test.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_online_style.py'
```

Result: passed.

Room-6 dry-run, no send:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\scripts\bilibili\send_browser_cdp.py' --room 6 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --realtime-online-style --realtime-online-style-seconds 60 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 10 --input-wait 20 --warmup-count 1 --max-comments 30 --port 9362 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_room6_auto_realtime_template_dryrun4'
```

Observed result:

- Auto-enable message printed:
  `auto-enabled realtime template payload rebuild for same-room realtime learning`.
- `realtime_template_payloads=True`.
- The sender no longer silently used the old template payloads.
- In that short dry-run only `2/4` high-quality payload wrappers survived the
  stricter filter, so dry-run kept the initial preview. With `--send`, the same
  condition would stop before sending.

Commit: `d635ee6`

## Update: 2026-05-24 Short Realtime Wrapper Composition

Files changed:

- `src/live_bullet_covert/sender.py`
- `tests/test_sender_payload_modes.py`
- `docs/handoff/WORK_LOG.md`
- `SESSION_HANDOFF.md`
- `NEW_CHAT_HANDOFF_CN.md`

Root cause:

- Room `6` had very high live traffic and the realtime monitor collected many
  comments, but most current-room comments were short phrases such as
  `刀妹入场`, `逆天`, `对的对的`, or `刀妹来了`.
- The previous payload-wrapper filter required a single long, mostly-CJK
  wrapper, so `40` raw realtime samples could become `0/4` usable payload
  wrappers. Real sends correctly stopped, but the failure mode was too strict
  for high-traffic short-comment rooms.

Behavioral summary:

- Added short-comment payload-wrapper composition. Short, clean CJK pieces can
  be combined into a longer wrapper before compact carrier insertion.
- Still rejects emoji/emote tags, long ASCII runs, pure numeric/ASCII samples,
  and punctuation-heavy samples before they can become payload wrappers.
- Compact insertion now prefers semantic boundary positions and limits trailing
  fallback carrier clustering.

Validation:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 -m py_compile '.\src\live_bullet_covert\sender.py' '.\tests\test_sender_payload_modes.py' '.\scripts\bilibili\send_browser_cdp.py' '.\scripts\bilibili\probes\full_http_sender.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_sender_payload_modes.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\offline_baseline_test.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_online_style.py'
```

Result: passed.

Room-6 dry-run, no send:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\scripts\bilibili\send_browser_cdp.py' --room 6 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --realtime-online-style --realtime-template-min-samples 4 --realtime-template-wait 5 --realtime-online-style-seconds 20 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 10 --input-wait 30 --warmup-count 1 --max-comments 30 --port 9365 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_room6_shortwrapper_dryrun2'
```

Observed result:

- `input_candidates` included the real `TEXTAREA chat-input`.
- Realtime rebuild used `samples=35 raw_samples=40` instead of stopping at
  `0/4`.
- `preview_rebuilt` was printed and no comments were sent because this was a
  dry run.

Commit: `09c52f2`

## Update: 2026-05-24 Receiver Auto-Decode Without FIN

Files changed:

- `src/live_bullet_covert/receiver.py`
- `scripts/bilibili/receive_ws_decode.py`
- `tests/test_receiver_realtime_compact.py`
- `docs/handoff/WORK_LOG.md`
- `SESSION_HANDOFF.md`
- `NEW_CHAT_HANDOFF_CN.md`

Root cause:

- In the same-room room-6 run, the browser sender reported `17/17 ok=True`,
  including `CAL`, `14` payload comments, and `fin`.
- The receiver did not reach final decode because it only decoded when `fin`
  was observed. In a high-traffic/filtering room, `fin` can be missed or not
  rebroadcast to the WebSocket listener.
- Ordinary public comments can also look like compact carrier records when they
  contain four carrier punctuation marks, e.g. `反你的野!!!!!` producing a high
  false-positive sequence such as `22222`.

Behavioral summary:

- `receive_ws_decode.py` now has `--auto-decode-records` with default `14`.
  After `CAL`, once enough encoded records are collected, the receiver attempts
  decode without waiting for `fin`.
- `receiver.CovLBCG_Decoder` now rebuilds only contiguous protocol sequences
  starting from sequence `0`; high-sequence false positives from ordinary
  comments are ignored instead of polluting seed/key extraction.

Validation:

```powershell
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 -m py_compile '.\src\live_bullet_covert\receiver.py' '.\scripts\bilibili\receive_ws_decode.py' '.\tests\test_receiver_realtime_compact.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_receiver_realtime_compact.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_receiver_humanized.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\offline_baseline_test.py'
& 'D:\Study\CovLBCG\.venv\Scripts\python.exe' -X utf8 '.\tests\test_sender_payload_modes.py'
```

Result: passed.
