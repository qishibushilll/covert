# CovLBCG session handoff

This file preserves the current research state locally so the work can continue
even if the remote Codex context-compaction request fails.

## Project structure update

On 2026-05-20 the project was reorganized around the actual project scope:
live-stream bullet-comment covert communication. The active Python package is now
`live_bullet_covert`.

Main active files:

- Sender: `src/live_bullet_covert/sender.py`
- Receiver: `src/live_bullet_covert/receiver.py`
- Bilibili WebSocket helper: `src/live_bullet_covert/bilibili_ws.py`
- Chrome/CDP helper: `src/live_bullet_covert/browser_cdp.py`
- Room-style learner: `src/live_bullet_covert/room_style.py`
- Browser sender entry point: `scripts/bilibili/send_browser_cdp.py`
- WebSocket receiver entry point: `scripts/bilibili/receive_ws_decode.py`
- Offline regression: `tests/offline_baseline_test.py`
- Detectability experiment: `experiments/detectability_baseline.py`
- Compact/humanized ablation: `experiments/compact_embedding.py`

Details and old-to-new mapping are recorded in
`docs/handoff/PROJECT_RESTRUCTURE_2026-05-20.md`.

## Current Python environment

Use the project virtual environment as the primary runtime:

```powershell
D:\Study\CovLBCG\.venv\Scripts\python.exe
```

It is based on:

```text
C:\Users\15052\AppData\Local\Programs\Python\Python312\python.exe
Python 3.12.0 64-bit
```

Key installed packages now include:

```text
numpy==2.4.6
matplotlib==3.10.9
pillow==12.0.0
requests==2.32.5
websocket-client==1.9.0
websockets==16.0
bilibili-api-python==17.4.1
selenium==4.41.0
cryptography==46.0.5
pycryptodome==3.23.0
```

`requirements.txt` has been added for the core project/runtime/figure dependencies.
The older pdf2zh runtime is still usable as an emergency standard-library fallback,
but it has no `pip`, no `matplotlib`, no `numpy` and should not be the main runtime.

## Current base version

- Main sender: `CovLBCG_Sender_5_multimodal.py`
- Main receiver: `CovLBCG_Receiver_5_multimodal.py`
- Working Python runtime:
  `D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe`

## Implemented tooling

- `room_style_learner.py`: passively learns room comment style from Bilibili history.
- `bilibili_ws_style_learner.py`: passively learns live room style through raw WebSocket.
- `popular_style_experiment.py`: high-fidelity safe experiment. It learns style from popular rooms, then evaluates fixed templates vs learned templates locally.
- `bilibili_browser_sender_cdp.py`: dependency-free Chrome DevTools sender for authorized-room/browser-style sending.
- `bilibili_ws_receiver_probe.py`: dependency-free raw WebSocket receiver/decoder.
- `browser_cdp.py`: local Chrome CDP helper.

## Real-platform findings

- Room `6963590`: earlier low-flow HTTP + WebSocket test decoded `hi`.
- Room `7777`:
  - Display room `7777` resolves to real room id `545068`.
  - Low-flow learned-style test succeeded and decoded `hi`.
  - A 93-comment HTTP full run at about 1.2 s interval hit `10031` frequency limit.
- Room `23087172`:
  - Low-flow raw WebSocket + HTTP sender decoded `hi`.
  - Full Chrome/CDP browser-style test succeeded:
    - 95 total sends: 3 warmups + CAL + 90 payload/filler + FIN.
    - Receiver reconstructed encrypted text `EDYd`, decrypted `hi#`, final output `成功解码: hi`.
  - Popular-room style transfer test succeeded:
    - style source: passive samples from rooms `6` and `7777`
    - replay target: authorized room `23087172`
    - 17 total sends: 1 warmup + CAL + 14 payload comments + FIN
    - receiver extracted 14 mixed-carrier fragments, reconstructed 7 protocol codes, decrypted `hi#`, final output `成功解码: hi`.
- Room `6`:
  - Display room `6` resolves to real room id `7734200`.
  - HTTP responses often returned `msg=f`; only partial messages appeared publicly.
  - Conclusion: room-level filtering makes it unsuitable for reliable decoding without filter-aware retry.

## Safe high-fidelity stealth experiment

Popular-room traffic was used passively only. No covert payload was sent to
unrelated popular rooms.

Latest run:

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' .\popular_style_experiment.py --rooms 6 7777 --target-per-room 60 --history-rounds 2 --history-sleep 2 --ws-seconds 30 --max-len 20 --out-dir popular_style_profiles_ws
```

Output files:

- `popular_style_profiles_ws/popular_comments.txt`
- `popular_style_profiles_ws/popular_templates.txt`
- `popular_style_profiles_ws/popular_profile.json`
- `popular_style_profiles_ws/popular_style_detectability.csv`

Key result:

- Fixed templates:
  - `stream_z_f1 = 0.8933`
  - `stream_length_js = 0.6801`
  - `stream_punctuation_js = 0.5507`
  - `duplicate_rate = 0.6260`
- Popular-style templates:
  - `stream_z_f1 = 0.6667`
  - `stream_length_js = 0.1257`
  - `stream_punctuation_js = 0.1900`
  - `duplicate_rate = 0.6360`

Interpretation: learned popular-room templates substantially reduce distribution
deviation in length and punctuation statistics, and reduce detector separability
relative to fixed templates.

## Authorized-room replay command

Dry run:

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' .\bilibili_browser_sender_cdp.py --room 23087172 --message 'hi#' --replicas 1 --fillers 0 --style-file popular_style_profiles_ws\popular_templates.txt --sleep 1.2 --page-wait 35 --warmup-count 1 --max-comments 60
```

Authorized send:

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' .\bilibili_browser_sender_cdp.py --room 23087172 --message 'hi#' --replicas 1 --fillers 0 --style-file popular_style_profiles_ws\popular_templates.txt --sleep 1.2 --page-wait 35 --warmup-count 1 --max-comments 60 --send
```

Use `--page-wait 35` for Chrome input initialization; a previous 5-second dry run
did not find the live chat input.

## Compact error handling

Error:

```text
Error running remote compact task: stream disconnected before completion:
error sending request for url (https://chatgpt.com/backend-api/codex/responses/compact)
```

This is a remote ChatGPT/Codex context-compaction network or backend-stream
failure, not a CovLBCG code error. Workaround:

- Continue from this file if the session context is shortened.
- Retry after refreshing or reopening the session.
- If it repeats, start a new shorter thread and paste or reference this file.
- Avoid very long uninterrupted sessions; periodically keep local handoff notes.

## Latest successful authorized-room replay

Command:

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' .\bilibili_browser_sender_cdp.py --room 23087172 --message 'hi#' --replicas 1 --fillers 0 --style-file popular_style_profiles_ws\popular_templates.txt --sleep 1.2 --page-wait 35 --warmup-count 1 --max-comments 60 --port 9336 --user-data-dir chrome_cdp_profile_23087172_popularstyle_retry --send
```

Result:

- browser input candidates included `textarea.chat-input`
- all `17` comments reported `ok=True`
- receiver observed `CAL`
- receiver extracted `14` mixed-carrier fragments
- sequence reconstruction produced `7` protocol codes with `0` missing sequence ids
- seed: `22`
- key length: `4`
- encrypted message: `EDYd`
- decrypted plaintext: `hi#`
- final result: `成功解码: hi`

The result has been recorded in `中文_审稿实验与回复说明.md` and
`RESEARCH_BASELINE.md`.

## Next research step

Convert the popular-style experiment into manuscript/rebuttal wording:

- describe the two-stage safe setup: passive popular-room learning, authorized-room replay
- report stream-level detectability reduction
- avoid claiming complete undetectability
- state that the method improves naturalness by adapting wrappers to live-room style while preserving decodability

## 2026-05-19 continuation notes

Added and updated rebuttal/manuscript wording:

- Added `中文_审稿回复草稿.md`: direct Chinese reviewer-response draft covering stealthiness, popular-room style transfer, authorized-room replay, PQ overhead wording, external baselines, trade-off analysis and II-B/II-C condensation.
- Updated `MANUSCRIPT_REVISION_TEXT.md` with Section 10, "Passive Popular-Room Style Learning and Authorized Replay".
- Updated `REVIEWER_RESPONSE_DRAFT.md` with the high-fidelity popular-room style transfer validation paragraph.

Re-verified local/offline results with the currently available runtime:

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -X utf8 -c "import sys, runpy; sys.path.insert(0, r'D:\Study\CovLBCG'); runpy.run_path(r'D:\Study\CovLBCG\detectability_baseline_test.py', run_name='__main__')"
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -X utf8 -c "import sys, runpy; sys.path.insert(0, r'D:\Study\CovLBCG'); runpy.run_path(r'D:\Study\CovLBCG\room_adaptive_stealth_experiment.py', run_name='__main__')"
```

Current detectability re-check:

- current short-fragment/sequence-indexed stream-level:
  - rule detector F1: `0.0000`
  - z-score detector F1: `0.6667`
  - length JS: `0.1262`
  - loaded-only z-score F1 remains `1.0000`
- synthetic room-adaptive experiment:
  - fixed stream length JS: `0.1593`
  - room-adaptive stream length JS: `0.0341`
  - fixed duplicate rate: `0.6280`
  - room-adaptive duplicate rate: `0.2720`
- existing popular-style CSV was regenerated from saved templates and remains:
  - fixed templates stream Z-F1: `0.8933`
  - popular-style stream Z-F1: `0.6667`
  - fixed length JS: `0.6801`
  - popular-style length JS: `0.1257`
  - fixed punctuation JS: `0.5507`
  - popular-style punctuation JS: `0.1900`

Runtime note:

- The pdf2zh runtime is isolated; `PYTHONPATH` is ignored and `sys.path` does not include the project directory.
- For scripts that import local modules but do not manually modify `sys.path`, run them through `runpy` with `sys.path.insert(0, r'D:\Study\CovLBCG')`, or use scripts that already insert the project directory.

Syntax check passed:

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -m py_compile .\detectability_baseline_test.py .\room_adaptive_stealth_experiment.py .\popular_style_experiment.py .\bilibili_browser_sender_cdp.py .\bilibili_ws_receiver_probe.py .\CovLBCG_Sender_5_multimodal.py .\CovLBCG_Receiver_5_multimodal.py
```

## Compact in-text carrier update

Implemented the first loaded-only concealment improvement:

- Sender now defaults to compact in-text carrier mapping.
- `seq + frag_idx + fragment` is still the logical record.
- The five visible decimal carriers are packed into four common punctuation carriers:
  - `COMPACT_CARRIER_ALPHABET = "，。！？；：、～…—,."`
  - `COMPACT_RECORD_SIZE = 4`
- Receiver supports both compact in-text records and legacy trailing mixed-carrier records.
- `COVLBCG_COMPACT_EMBEDDING=0` restores the legacy mixed suffix.
- Added `compact_embedding_experiment.py`.

Validation:

- `offline_baseline_test.py`: pass.
- `comparative_benchmark.py`: clean/reorder/light loss `1.0000`; default 10% loss `0.9200`.
- `tradeoff_sweep.py`: main `replicas=3, fillers=2` gives success `0.9667`, loaded Z-F1 `0.9852`, stream length JS `0.0835`.
- `compact_embedding_experiment.py`:
  - legacy loaded Z-F1 `0.9970`
  - compact loaded Z-F1 `0.9881`
  - legacy stream length JS `0.1244`
  - compact stream length JS `0.0727`
  - legacy loaded symbol mean `1.2100`
  - compact loaded symbol mean `0.0000`

Interpretation:

- This improves loaded-only concealment slightly and stream-level length distribution more clearly.
- It does not solve loaded-only detectability.
- Next step: semantic punctuation placement/template punctuation rewriting so compact carriers land on natural clause boundaries.

Authorized Bilibili compact test:

- Room: `23087172`.
- Message: `hi#`.
- Sender: Chrome/CDP browser input.
- Style file: `popular_style_profiles_ws\popular_templates.txt`.
- Carrier mode: compact in-text.
- Parameters: `replicas=1`, `fillers=0`, `sleep=1.2`, `page_wait=35`, `warmup_count=1`.
- Total browser sends: `17`.
- Browser send result: `17/17 ok=True`.
- Receiver log: `bilibili_ws_receiver_23087172_compact.log`.
- Receiver result:
  - observed `CAL`
  - extracted `14` compact fragments
  - sequence reconstruction produced `7` protocol codes with `0` missing sequence ids
  - seed `22`
  - key length `4`
  - encrypted message `EDYd`
  - decrypted plaintext `hi#`
  - final output `成功解码: hi`

## 2026-05-19 remote compact failure recovery

Observed UI/API error:

```text
Error running remote compact task: stream disconnected before completion:
error sending request for url (https://chatgpt.com/backend-api/codex/responses/compact)
```

Diagnosis:

- This is a ChatGPT/Codex remote context-compaction stream failure.
- It is not caused by `CovLBCG_Sender_5_multimodal.py`, `CovLBCG_Receiver_5_multimodal.py`, Bilibili, Chrome/CDP, or the local Python runtime.
- The local mitigation is to keep this handoff file current and continue from it after refresh/new session.

Practical recovery path:

1. Refresh or reopen the Codex session and retry once.
2. If it repeats, start a new shorter session and ask the assistant to read `D:\Study\CovLBCG\NEW_CHAT_HANDOFF_CN.md` and `D:\Study\CovLBCG\SESSION_HANDOFF.md`.
3. Keep long-running experiment state in these handoff files instead of relying only on remote automatic compaction.
4. For unstable network/proxy conditions, avoid starting large benchmark runs immediately before expected context compaction.

## Humanized carrier update

After the compact in-text experiment, user feedback showed that punctuation-heavy payloads
such as repeated `，，，、` still looked non-human in Bilibili chat. A second-stage
humanized carrier mode was implemented.

Current behavior:

- Sender defaults to humanized carrier mode through `COVLBCG_HUMANIZED_CARRIER=1`.
- The visible payload is no longer a punctuation blob. Each encoded record maps into a
  short room-style sentence built from topic words, modal particles, punctuation, and
  reaction phrases.
- Receiver detects humanized carriers first, then falls back to compact and legacy carriers.
- `COVLBCG_HUMANIZED_CARRIER=0` disables the mode for ablation.

Representative generated payload comments for `hi#`, `replicas=1`, `fillers=0`:

```text
主播～爽局了
手机玩过头了。手机啊
操作嘛～笑死
一波线!爽局呢
手机玩过头了？补刀呀
一波线…可以吧
蛮王，爽局吧
这也太离谱了？操作吧
爽局,可以吧
一波线。爽局啊
没空鸟你？手机嘛
操作!可以啊
爽局！爽局啊
有点意思，操作吧
```

Validation already completed locally:

- `py_compile` passed for sender and receiver.
- `offline_baseline_test.py` passed.
- Humanized detectability check:
  - loaded-only z-score F1: `0.6667`
  - stream-level z-score F1: `0.6667`
  - stream length JS: `0.0105`
  - carrier symbol count: `0.0000`

Caveats:

- The current humanized codebook is deterministic and can still repeat recognizable
  phrase patterns under longer messages.

## 2026-05-19 continuation: humanized decoder and ablation fix

Completed the two immediate follow-up items from the humanized carrier update:

- `CovLBCG_Receiver_5_multimodal.py` now builds a deterministic
  humanized-text-to-record dictionary once per process. This replaces the old
  per-comment brute-force scan over all `20480` topic/modal/punctuation/reaction
  combinations while preserving the previous first-match behavior for truncated
  template collisions.
- `compact_embedding_experiment.py` now explicitly saves, toggles and restores
  `HUMANIZED_CARRIER_ENABLED`. The ablation rows now separate legacy suffix,
  compact positional, compact semantic and humanized phrase-carrier modes.

Validation run with the pdf2zh isolated runtime:

```powershell
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -m py_compile .\CovLBCG_Receiver_5_multimodal.py .\compact_embedding_experiment.py
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -X utf8 -c "import sys, runpy; sys.path.insert(0, r'D:\Study\CovLBCG'); runpy.run_path(r'D:\Study\CovLBCG\offline_baseline_test.py', run_name='__main__')"
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -X utf8 -c "import sys, runpy; sys.path.insert(0, r'D:\Study\CovLBCG'); runpy.run_path(r'D:\Study\CovLBCG\compact_embedding_experiment.py', run_name='__main__')"
& 'D:\Downloads\qq\pdf2zh-v2.6.4-BabelDOC-v0.5.10-with-assets-win64\pdf2zh\runtime\python.exe' -X utf8 -c "import sys, runpy; sys.path.insert(0, r'D:\Study\CovLBCG'); runpy.run_path(r'D:\Study\CovLBCG\detectability_baseline_test.py', run_name='__main__')"
```

Key current ablation output:

```text
legacy_mixed_suffix: loaded_z_f1=0.9970, stream_length_js=0.1244
compact_position_in_text: loaded_z_f1=0.9881, stream_length_js=0.0727
compact_semantic_in_text: loaded_z_f1=0.9881, stream_length_js=0.0746
humanized_phrase_carrier: loaded_z_f1=0.6667, stream_length_js=0.0183
```

Default humanized detectability baseline remains:

```text
loaded-only z-score F1 = 0.6667
stream-level z-score F1 = 0.6667
stream length JS = 0.0105
carrier_symbol_count_js = 0.0000
```

Next useful step:

- Improve the humanized codebook diversity so longer messages do not repeat the
  same deterministic phrase skeletons too visibly, then run a longer
  comparative benchmark before any additional authorized-room replay.

## 2026-05-20 authorized minimal-traffic Bilibili demo

Ran a successful minimal-traffic real-platform demonstration for the group
meeting, using only the authorized test room.

Setup:

- Room: `23087172`.
- Message: `hi#`.
- Sender: Chrome/CDP browser input.
- Carrier mode: default humanized phrase carrier.
- Parameters: `replicas=1`, `fillers=0`, `warmup_count=1`,
  `sleep=1.2`, `page_wait=35`, `max_comments=30`.
- Total browser sends: `17` comments
  (`1` warmup + `CAL` + `14` payload comments + `fin`).
- Receiver log:
  `bilibili_ws_receiver_23087172_humanized_demo.log`.

Sender result:

```text
room_id = 23087172
payload_count = 14
total_comments_with_markers = 17
input_candidates = textarea.chat-input
browser send = 17/17 ok=True
```

Receiver result:

```text
observed CAL at 09:05:03
extracted 14 humanized fragments
sequence reconstruction = 7 protocol codes
missing sequence ids = 0
seed = 22
key length = 4
encrypted message = EDYd
plaintext = hi#
final output = 成功解码: hi
```

Representative transmitted humanized payload comments:

```text
主播～爽局了
手机玩过头了。手机啊
操作嘛～笑死
一波线!爽局呢
手机玩过头了？补刀呀
一波线…可以吧
蛮王，爽局吧
这也太离谱了？操作吧
爽局,可以吧
一波线。爽局啊
没空鸟你？手机嘛
操作!可以啊
爽局！爽局啊
有点意思，操作吧
```

This is a small-scale feasibility/demo run, not a large-scale robustness or
undetectability proof.

## 2026-05-23 realtime learning and template payload update

Use this section first when resuming in a new session. The active repo is:

```text
D:\Study\CovLBCG
```

Latest pushed commits on `main`:

```text
4c3e13b Add realtime template payload rebuild
12cf52b Record realtime monitoring commit reference
9065558 Add realtime online style monitoring
173c8f4 Record room 6 trial commit reference
e9adb80 Record room 6 popular learning trial
d6acdf2 Guard cross-room template payload sends
```

Important correction:

- The first realtime implementation did not make outgoing payload text use
  newly learned realtime samples.
- `--realtime-online-style` starts a background listener and updates pacing,
  audit baselines and saved source-room profiles only.
- Payload text was still generated before room samples arrived, so it used the
  default humanized codebook unless a style file or template mode was provided.

Current fixed behavior in `4c3e13b`:

- `--realtime-online-style`: realtime activity/profile monitoring only.
- `--realtime-template-payloads`: after browser page wait, collect realtime
  samples from the same run, rebuild payload comments from those samples, and
  print `preview_rebuilt`.
- `--realtime-template-min-samples`: minimum samples required for rebuild.
- `--realtime-template-wait`: extra wait before send/dry-run to reach the
  sample threshold.
- Real sends with realtime template payloads are allowed only when the realtime
  source room equals `--room`. Cross-room realtime templates are rejected for
  real sends.

Changed files:

- `src/live_bullet_covert/online_style.py`
- `src/live_bullet_covert/sender.py`
- `scripts/bilibili/send_browser_cdp.py`
- `scripts/bilibili/probes/full_http_sender.py`
- `tests/test_online_style.py`
- `tests/test_sender_payload_modes.py`
- `README.md`
- `docs/handoff/WORK_LOG.md`
- `NEW_CHAT_HANDOFF_CN.md`
- `SESSION_HANDOFF.md`

Verified realtime-template dry-run, no send:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 6 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --realtime-online-style --realtime-template-payloads --realtime-template-min-samples 4 --realtime-template-wait 20 --realtime-online-style-seconds 60 --online-style-target 20 --online-style-min-samples 999 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 5 --warmup-count 1 --max-comments 30 --port 9349 --user-data-dir 'local_secrets\chrome_profiles\chrome_cdp_profile_room6_realtime_templates_dryrun'
```

Observed result:

```text
initial preview = default humanized codebook
realtime_template_payloads_active=True
realtime_template_samples=10
preview_rebuilt used current room-6 samples from the same run
examples: 神人, 贪吃, 幻视AL打T1, 大树来抓一波就炸了
no --send was used, so actual sends = 0
port 9349 was free after cleanup
```

Latest safe authorized send pattern:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 23087172 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --realtime-online-style --realtime-online-style-seconds 180 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 35 --warmup-count 1 --max-comments 30 --send --confirm-authorized
```

This uses room `6` only for passive realtime activity/style monitoring and sends
only to the authorized test room `23087172`.

Safety and policy state:

- Do not send to public/unverified popular rooms. Room `6` can be used for
  passive learning and dry-run only unless a controlled authorization setup is
  provided and can pass the local authorized-room guard.
- Real sends require `--send --confirm-authorized`.
- Default authorized room: `23087172`.
- Low-disturbance defaults: minimum sleep `10s`, maximum comments `30`.
- Cross-room learned style files are rejected for real sends.
- Cross-room realtime template payloads are rejected for real sends.

Validation already passed:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m py_compile .\src\live_bullet_covert\online_style.py .\src\live_bullet_covert\sender.py .\scripts\bilibili\send_browser_cdp.py .\scripts\bilibili\probes\full_http_sender.py .\tests\test_online_style.py .\tests\test_sender_payload_modes.py
.\.venv\Scripts\python.exe -X utf8 .\tests\test_online_style.py
.\.venv\Scripts\python.exe -X utf8 .\tests\test_sender_payload_modes.py
.\.venv\Scripts\python.exe -X utf8 .\tests\offline_baseline_test.py
```

Current workspace status after pushing `4c3e13b`:

```text
main and origin/main match at 4c3e13b.
The only remaining unstaged changes are run-generated room-6 profile data:
data/profiles/online_style_profiles/room_6_comments.txt
data/profiles/online_style_profiles/room_6_profile.json
data/profiles/online_style_profiles/room_6_templates.txt
```

Do not mix those run-generated profile changes into unrelated feature commits.
If they are needed as updated samples, review and commit them separately.

## 2026-05-23 room-6 failure diagnosis and guard update

The latest user-run room-6 attempt exposed two separate bugs:

- Sender input targeting was wrong. The log showed
  `input_candidates=[{'tag': 'INPUT', 'cls': 'nav-search-input', ...}]`, and
  each `browser_send` focused that same `nav-search-input`. Those messages went
  to the page search box, not the live chat input, so the receiver kept
  listening without seeing a decodable `CAL`/payload/`fin` sequence.
- Realtime template payloads accepted too-short wrappers such as `😧` or `宫中`,
  so compact carrier records appeared as short text followed by clustered
  punctuation. That was not natural room style.

Current fix:

- `browser_cdp.py` marks candidates as `is_chat_input` and `is_search`.
- The browser sender refuses `--send` when no visible live-chat input is found.
- Realtime template rebuilds now filter unusable wrappers before building
  payloads and stop real sends if too few usable samples remain.
- Compact payload generation prefers longer wrappers and rejects trailing
  compact-carrier clusters.

Validated with py_compile, sender payload tests, offline baseline, and
`test_online_style.py`. A room-6 dry run with no `--send` confirmed that a page
showing only `nav-search-input` is identified as non-chat and that insufficient
usable realtime wrappers do not produce a rebuilt payload preview.

Local-state warning: the user's `src/live_bullet_covert/send_policy.py` change
to `DEFAULT_AUTHORIZED_ROOM_ID = 6` is not part of this fix and should not be
committed unless explicitly requested.

Commit containing the fix: `9b9d443`.

## 2026-05-24 room-6 input wait update

A follow-up user screenshot still showed:

```text
input_candidates=[INPUT cls=nav-search-input ... is_chat_input=False]
live chat input not found
```

Diagnosis:

- Display room `6` is an LPL赛事/活动 outer page.
- The real live-room iframe points to room id `7734200`.
- The chat input can appear a few seconds after the fixed `--page-wait`; reading
  the retained CDP page later showed
  `TEXTAREA cls='chat-input border-box' placeholder='发个弹幕呗~'`.

Current fix:

- Browser navigation uses the resolved actual room id returned by
  `room_style.room_init()`, so `--room 6` opens
  `https://live.bilibili.com/7734200`.
- Input discovery scans same-origin iframes and shadow roots.
- `send_browser_cdp.py` has `--input-wait` and `--input-poll`, defaulting to an
  extra 30-second poll window after `--page-wait`.
- Real sends still stop if no visible live-chat input is found after polling.

Validated by dry-run with no `--send`: `--room 6` navigated to room `7734200`
and `input_candidates` included `TEXTAREA chat-input border-box` with
`is_chat_input=True`.

Commit containing the update: `12ff6bf`.

## 2026-05-24 auto same-room realtime payload update

The user ran:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\bilibili\send_browser_cdp.py --room 6 --online-style-source-room 6 --message 'a#' --replicas 1 --fillers 0 --realtime-online-style --realtime-online-style-seconds 180 --adaptive-sleep --sleep 10 --min-sleep 10 --page-wait 35 --warmup-count 1 --max-comments 30 --send --confirm-authorized
```

and reported that sends still used old templates and the receiver did not
decode. The log showed `realtime_template_payloads=False`, so the sender was
only doing realtime activity learning, not realtime payload-text rebuild.

Current fix:

- Same-room `--realtime-online-style` now automatically enables realtime
  template payload rebuilds.
- Defaults: `realtime_template_min_samples=4`,
  `realtime_template_wait=60`.
- Rebuild waits for usable payload wrappers after filtering, not only raw
  comments.
- Payload wrapper filtering rejects emoji/emote tags, long ASCII runs, very
  short comments and punctuation-heavy samples.
- If usable wrappers are insufficient, real sends stop instead of falling back
  to old built-in templates.

Dry-run confirmed the auto-enable path prints the auto-enable message and
`realtime_template_payloads=True`. In one room-6 dry-run only `2/4` wrappers
passed the stricter filter, so no send occurred and no old-template payload was
used.

Commit containing the update: `d635ee6`.

## 2026-05-24 short realtime wrapper composition

The latest same-room room-6 run proved that realtime collection itself was not
the problem:

```text
observed=1013
saved_templates ... samples=40
realtime usable template samples insufficient after filtering: 0/4
```

The blocker was that room `6` currently contains many short live comments. The
previous payload-wrapper filter expected each wrapper to be long enough by
itself, so clean short comments such as `刀妹入场`, `对的对的`, and `刀妹来了`
were all rejected for payload use.

Current fix:

- Short, clean CJK realtime comments can now be composed into longer payload
  wrappers before compact carrier insertion.
- Emoji/emote tags, pure numeric/ASCII samples, long ASCII runs, and punctuation-
  heavy samples are still rejected.
- Compact carrier insertion now prefers semantic boundaries and reduces trailing
  carrier clustering.
- Added sender payload tests covering room-6-like short samples and full `a#`
  round-trip decoding with `replicas=1`, `fillers=0`.

Dry-run with no send confirmed realtime template rebuild now proceeds:

```text
rebuilding payloads from realtime templates: samples=35 raw_samples=40
preview_rebuilt printed
```

Commit containing the update: `09c52f2`.

## 2026-05-24 receiver auto-decode without fin

The user then showed a real same-room room-6 send where the browser sender
reported `17/17 ok=True`, including `CAL`, all payload comments, and `fin`, but
the receiver window did not print a final decode.

Diagnosis:

- The receiver only decoded when it observed `fin`.
- In room `6`, `fin` can be missed or filtered even when the browser sender
  reports the page input accepted it.
- The receiver was also collecting occasional false-positive compact records
  from ordinary comments with repeated punctuation, such as `反你的野!!!!!`
  producing `code=22222`.

Current fix:

- `scripts/bilibili/receive_ws_decode.py` now auto-attempts decoding after
  `--auto-decode-records` encoded records after `CAL`; default is `14` for the
  current `a#`, `replicas=1`, `fillers=0` test path.
- `src/live_bullet_covert/receiver.py` now rebuilds only contiguous protocol
  sequences starting at `0`, so high-sequence false positives are ignored.
- Added `tests/test_receiver_realtime_compact.py` using the user's actual
  realtime compact payloads, with no `fin`, plus one high-sequence false
  positive before the payloads. Both decode to `a`.

Commit containing the update: `b2bca1b`.
