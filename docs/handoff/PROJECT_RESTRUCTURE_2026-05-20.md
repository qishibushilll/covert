# Project Restructure 2026-05-20

The project was reorganized around its actual scope: live-stream bullet-comment
covert communication. The Python package name is now:

```text
live_bullet_covert
```

## Main Mapping

| Old path | New path |
|---|---|
| `CovLBCG_Sender_5_multimodal.py` | `src/live_bullet_covert/sender.py` |
| `CovLBCG_Receiver_5_multimodal.py` | `src/live_bullet_covert/receiver.py` |
| `bilibili_ws_danmaku.py` | `src/live_bullet_covert/bilibili_ws.py` |
| `browser_cdp.py` | `src/live_bullet_covert/browser_cdp.py` |
| `room_style_learner.py` | `src/live_bullet_covert/room_style.py` |
| `bilibili_browser_sender_cdp.py` | `scripts/bilibili/send_browser_cdp.py` |
| `bilibili_ws_receiver_probe.py` | `scripts/bilibili/receive_ws_decode.py` |
| `bilibili_ws_style_learner.py` | `scripts/bilibili/learn_ws_style.py` |
| `detectability_baseline_test.py` | `experiments/detectability_baseline.py` |
| `compact_embedding_experiment.py` | `experiments/compact_embedding.py` |
| `offline_baseline_test.py` | `tests/offline_baseline_test.py` |

## Directories

- `src/live_bullet_covert/`: active library code.
- `scripts/bilibili/`: real-platform entry points.
- `experiments/`: repeatable evaluation scripts.
- `tests/`: local regression checks.
- `docs/`: manuscript and rebuttal material.
- `data/`: non-secret style profiles and examples.
- `figures/`: generated paper figures and source tables.
- `runs/`: logs from previous runs.
- `local_secrets/`: cookies, Chrome profiles and keys.
- `archive/`: historical prototypes and old run scripts retained for reference.

## Deleted

- Stale `*.pid` files.
- Empty throwaway files `r1.py` and `room_comments.txt`.
- Non-venv `__pycache__` directories.
- Temporary dry-run Chrome profile.

## Validation After Restructure

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pip install -e .
.\.venv\Scripts\python.exe -X utf8 -m py_compile .\src\live_bullet_covert\sender.py .\src\live_bullet_covert\receiver.py .\src\live_bullet_covert\browser_cdp.py .\src\live_bullet_covert\bilibili_ws.py .\src\live_bullet_covert\room_style.py .\scripts\bilibili\send_browser_cdp.py .\scripts\bilibili\receive_ws_decode.py .\experiments\detectability_baseline.py .\experiments\compact_embedding.py .\tests\offline_baseline_test.py
.\.venv\Scripts\python.exe -X utf8 .\tests\offline_baseline_test.py
.\.venv\Scripts\python.exe -X utf8 .\experiments\compact_embedding.py
.\.venv\Scripts\python.exe -X utf8 .\experiments\detectability_baseline.py
```

All checks passed.
