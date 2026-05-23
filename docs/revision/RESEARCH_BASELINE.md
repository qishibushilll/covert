# CovLBCG Research Baseline

Baseline date: 2026-05-11

The following pair is the primary baseline for subsequent CovLBCG research:

- `CovLBCG_Sender_5_multimodal.py`
- `CovLBCG_Receiver_5_multimodal.py`

Current baseline characteristics:

- Multimodal carrier design: symbol, punctuation, and spacing carriers.
- Shared core constants: `TARGET_ROOM_ID`, `TIME_OFFSET`, `JOIN_COMMAND`, `SYNC_COMMAND`, and `SAFE_CHARS`.
- Sender side includes Selenium browser sending flow.
- Receiver side includes Bilibili live danmaku listening flow.
- Both sides include post-quantum encryption and Reed-Solomon style recovery components.

Immediate research notes:

- Treat this pair as the source of truth before making changes to older `Sender_*` or `Receiver_*` variants.
- Source-file encoding has been verified as valid UTF-8 without BOM. If PowerShell shows mojibake, it is a console display/encoding issue, not source corruption.
- Add future experiments around this baseline rather than branching from `Advanced`, `chaos`, or `stealth` variants unless explicitly needed.

Confirmed local Python environment:

- Recommended interpreter: `C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe`
- Version: Python 3.13.7
- Syntax check: `CovLBCG_Receiver_5_multimodal.py` and `CovLBCG_Sender_5_multimodal.py` pass `py_compile` under Python 3.13.
- Runtime imports verified under Python 3.13: `selenium`, `webdriver_manager`, `bilibili_api`, `pqcrypto.kem.ml_kem_512`, and `numpy`.
- `numpy` version observed: 2.2.6

Avoid using `C:\Users\15052\AppData\Local\Programs\Python\Python314\python.exe` for this research baseline for now. It is Python 3.14.0a5 and is missing several required packages in the current environment.

Offline baseline test:

- Test script: `offline_baseline_test.py`
- Command: `C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe -X utf8 .\offline_baseline_test.py`
- Sender-to-receiver closed-loop cases pass for:
  - `hello world#` -> `hello_world`
  - `CovLBCG_test_123#` -> `CovLBCG_test_123`
  - `主播加油，测试！#` -> `,!` after current safe-character sanitization
- Initial loss boundary check:
  - No drop: pass
  - Drop first payload: fail
  - Drop one middle payload in the seeded run: pass
  - Drop final key-length payload: fail

Research implication: the current baseline can complete a clean offline sender/receiver round trip, but packet-loss robustness is not yet reliable. The Reed-Solomon component exists in both files, but the active sender/receiver data path does not yet use it for packet recovery.

Stealthiness research update:

- Added `detectability_baseline_test.py` for benign/covert distribution and detector checks.
- Added `stealth_strategy_experiment.py` for comparing carrier scheduling strategies.
- Updated `CovLBCG_Sender_5_multimodal.py` from fixed four-symbol suffixes to two-digit, low-density, punctuation-prioritized per-digit symbol/punctuation fragments.
- Updated `CovLBCG_Receiver_5_multimodal.py` to decode mixed symbol/punctuation fragments and reassemble two fragments into one four-digit protocol code.
- Clean offline sender/receiver round-trip still passes after the scheduling change.
- Current stream-level detectability is improved relative to the original fixed-symbol suffix baseline: the fixed four-symbol rule detector drops to F1 `0.0000`, length JS distance is `0.0150` and carrier-symbol-count JS distance is `0.0816`.
- Loaded-only comments remain distinguishable under the current statistical detector, so the paper should present this as a bandwidth-concealment trade-off rather than a perfect undetectability result.
- A one-digit fragment pilot was tested. It can reduce loaded-only detector scores only when no explicit boundary marker is used, but that mode causes false positives from ordinary punctuation and breaks clean round-trip decoding. Adding explicit boundaries restores decoding but makes the boundary itself detectable and doubles fragment overhead. The two-digit fragment mode remains the current practical baseline.
- A pure-punctuation carrier pilot was tested. It removes carrier-symbol anomalies but increases punctuation anomalies, so the current `3:1` punctuation-to-symbol per-digit mix remains the better measured setting.

External-baseline benchmark update:

- Added `comparative_benchmark.py`.
- Compared current proposed path against protocol-level `time_modulation` and `nlg_comment_choice` baselines.
- Clean and reorder-only conditions: all methods recover successfully.
- Light loss (`p_loss=0.02`, `reorder_jitter=0.10`): proposed succeeds in `0.4400` of trials; simplified baselines fail under the current reproduction settings.
- Default loss (`p_loss=0.10`, `reorder_jitter=0.10`): all current implementations fail.
- Research implication: the current code now has a useful external comparison harness, but the proposed path still needs sequence-indexed redundancy or packet-level metadata before it can support the manuscript's stronger 10% loss robustness claims.

Sequence-indexed redundancy update:

- Implemented sequence-indexed redundant fragments.
- Fragment record format: `seq(2 digits) + frag_idx(1 digit) + fragment(2 digits)`.
- `FRAGMENT_REPLICAS = 3`.
- Receiver reconstructs protocol codes by grouping on `seq`, voting by `frag_idx` and then sorting sequence numbers.
- Offline clean round-trip and simple single-drop checks pass.
- Comparative benchmark after the change:
  - Clean: proposed success `1.0000`
  - Reorder-only: proposed success `1.0000`
  - Light loss (`p_loss=0.02`): proposed success `1.0000`
  - Default loss (`p_loss=0.10`): proposed success `0.9200`
- Cost: benchmark average comments increase to `361.00`, and loaded-only detectability becomes worse. This should be reported as a robustness-overhead-concealment trade-off.
- A `FRAGMENT_REPLICAS = 2` pilot was also tested:
  - Average comments: `241.00`
  - Light loss success: `0.9800`
  - Default 10% loss success: `0.6000`
  - Because the 10% loss success is much lower than the `FRAGMENT_REPLICAS = 3` result (`0.9200`), the main code remains at `FRAGMENT_REPLICAS = 3`.

Trade-off sweep update:

- Added `tradeoff_sweep.py`.
- Swept `FRAGMENT_REPLICAS in {1,2,3,4}` and `FILLERS_PER_PAYLOAD in {1,2,3}`.
- Channel: `p_loss=0.10`, `reorder_jitter=0.10`, `30` trials per setting.
- Current main setting remains `FRAGMENT_REPLICAS = 3`, `FILLERS_PER_PAYLOAD = 2`.
- In the sweep, this setting achieved success `0.9667`, average comments `361.00`, loaded ratio `0.3333`, stream Z-F1 `0.6667` and stream length JS `0.1226`.
- The sweep supports using `3/2` as the manuscript's balanced operating point. `4/1` is robustness-efficient but has higher loaded density, while `3/3` is more stream-concealing but has higher comment overhead.

Room-adaptive wrapper update:

- Added `room_adaptive_stealth_experiment.py`.
- Added optional sender support for `room_comments.txt`; if this file exists, sender uses live-room comments as payload wrappers and filler comments.
- Added `room_comments.example.txt` as a sample format.
- Added `room_style_learner.py` as the general pre-communication learning stage:
  - for any target live room, collect recent public comments
  - clean and deduplicate comments
  - generate `room_profiles/room_<room_id>_comments.txt`
  - generate `room_profiles/room_<room_id>_templates.txt`
  - generate `room_profiles/room_<room_id>_profile.json`
  - optionally activate the learned templates as `room_comments.txt`
- Updated `bilibili_full_http_sender_probe.py` with `--learn-style`, so a real-room dry run or authorized send can follow the sequence:
  - learn target-room style
  - load the learned template file
  - generate covert payload comments
  - optionally send only when `--send` is explicitly provided
- Updated sender wrapper selection to preserve learned-room punctuation and wording instead of stripping ordinary Chinese punctuation from the wrapper.
- With synthetic room corpus:
  - `fixed_templates` stream length JS: `0.1593`
  - `room_adaptive` stream length JS: `0.0341`
  - `fixed_templates` stream punctuation JS: `0.2743`
  - `room_adaptive` stream punctuation JS: `0.1900`
  - `fixed_templates` duplicate rate: `0.6280`
  - `room_adaptive` duplicate rate: `0.2720`
- Interpretation: room-adaptive wrappers reduce stream-level template repetition and distributional deviation, but loaded-only detection remains high because metadata-bearing fragments are still visible.
- Fetched public history comments from Bilibili live room `6963590` into `room_comments.txt` using `fetch_bilibili_room_comments.py`.
- Current real-room corpus size: `18`.
- With this real-room corpus:
  - `fixed_templates` stream Z-F1: `0.8420`
  - `room_adaptive` stream Z-F1: `0.6667`
  - `fixed_templates` stream length JS: `0.3834`
  - `room_adaptive` stream length JS: `0.1054`
  - `fixed_templates` stream punctuation JS: `0.4718`
  - `room_adaptive` stream punctuation JS: `0.1914`
- Caveat: corpus size is currently small, so duplicate-rate improvement is limited.

Latest style-learning dry-run:

- Command pattern:
  - `room_style_learner.py --room <room_id> --target-count 80 --rounds 12 --sleep 5`
  - `bilibili_full_http_sender_probe.py --room <room_id> --message 'hi#' --learn-style ...`
- A light verification on room `6963590` learned current room templates and generated a no-send preview successfully.
- Generated files:
  - `room_profiles/room_6963590_comments.txt`
  - `room_profiles/room_6963590_templates.txt`
  - `room_profiles/room_6963590_profile.json`
- The dry-run preview used the newly learned room comments rather than fixed templates.

Real-platform feasibility update:

- Added `bilibili_full_http_sender_probe.py` and `bilibili_full_receiver_probe.py` for real-platform end-to-end probing.
- Completed one small-scale Bilibili live-room round trip on room `6963590`.
- Test message: `hi#`.
- Public-traffic-minimizing parameters: `replicas=1`, `fillers=0`.
- Transmission size: `17` comments total:
  - warm-up ordinary comment
  - `CAL`
  - `14` protocol-bearing mixed-carrier fragment comments
  - `fin`
- Platform send result: all HTTP send requests returned `code=0`.
- Receiver result:
  - observed `CAL` and `fin` from the real live bullet-comment stream
  - extracted `14` fragment records
  - reconstructed `7` four-digit protocol codes
  - missing sequence count: `0`
  - decrypted plaintext: `hi#`
  - final displayed result: `成功解码: hi`
- Interpretation: the current implementation can complete a real Bilibili end-to-end round trip. This should be reported as feasibility evidence only; statistical robustness and detectability claims should remain based on controlled repeatable experiments.
- Ethical/operational note: do not run high-redundancy or high-volume tests in a public live room. Use an owned or explicitly authorized test room for repeated real-platform trials.

Second real-platform test on room `23087172`:

- Added dependency-free raw WebSocket helpers:
  - `bilibili_ws_danmaku.py`
  - `bilibili_ws_style_learner.py`
  - `bilibili_ws_receiver_probe.py`
- Reason: the available Python runtime did not include `bilibili_api/aiohttp`, and room `23087172` returned no comments through the history API.
- Style-learning result:
  - history API sample count: `0`
  - WebSocket learning window: `60` seconds
  - WebSocket natural-comment sample count: `0`
  - interpretation: this room had no observable background comments during the learning window, so no room-specific template could be formed in this run.
- Sender fallback:
  - `room_comments_enabled=False`
  - fixed fallback templates were used for this test only.
- Real send:
  - room: `23087172`
  - message: `hi#`
  - parameters: `replicas=1`, `fillers=0`
  - transmission size: `17` comments total
  - platform send result: all `17` HTTP send requests returned `code=0`
- Raw WebSocket receiver result:
  - observed `主播加油`
  - observed `CAL`
  - extracted `14` mixed-carrier fragment records
  - observed `fin`
  - reconstructed `7` four-digit protocol codes
  - missing sequence count: `0`
  - decrypted plaintext: `hi#`
  - final displayed result: `成功解码: hi`
- Important caveat: this test validates the real Bilibili end-to-end transport and raw WebSocket receiver, but it does not validate room-adaptive style learning because the room had no learnable ambient comments during the observation window.

Third real-platform test on short room `7777`:

- Display room id: `7777`.
- Resolved actual room id: `545068`.
- Important implementation fix:
  - `bilibili_full_http_sender_probe.py` now resolves the display room id to the actual Bilibili `room_id` before calling `msg/send`.
  - This matters for short room ids such as `7777`; sending with `roomid=7777` can return `code=0` but not appear in the actual live stream.
- Style-learning result:
  - `learn_style=1`
  - final successful run sample count: `11`
  - learned templates came from the current `7777` room stream/history.
- Important platform-length fix:
  - Bilibili rejected an earlier payload with `code=1003212`, message `超出限制长度`.
  - `CovLBCG_Sender_5_multimodal.py` now enforces `MAX_COMMENT_LENGTH = 20` and truncates/selects wrappers so that `wrapper + carrier` stays within the platform limit.
- Real send:
  - message: `hi#`
  - parameters: `replicas=1`, `fillers=0`
  - transmission size: `17` comments total
  - platform send result: all `17` HTTP send requests returned `code=0`
- Raw WebSocket receiver result:
  - observed `主播加油`
  - observed `CAL`
  - extracted `14` mixed-carrier fragment records
  - observed `fin`
  - reconstructed `7` four-digit protocol codes
  - missing sequence count: `0`
  - decrypted plaintext: `hi#`
  - final displayed result: `成功解码: hi`
- User-facing terminal scripts added for visible logging:
  - `run_bili_receiver_7777.ps1`
  - `run_bili_sender_7777.ps1`

Fourth real-platform test on room display id `6`:

- URL tested: `https://live.bilibili.com/6?...`.
- Display room id: `6`.
- Resolved actual room id: `7734200`.
- Style-learning result:
  - `learn_style=1`
  - sample count: `9`
  - generated:
    - `room_profiles/room_6_templates.txt`
    - `room_profiles/room_6_profile.json`
- Low-flow send attempt:
  - message: `hi#`
  - parameters: `replicas=1`, `fillers=0`
  - total comments: `17`
  - platform send result: all requests returned `code=0`
  - however many responses returned `msg=f`.
- Observation:
  - WebSocket and history API showed only a subset of the sent comments.
  - First attempt captured only `主播加油`, `CAL`, and the first payload fragment.
  - Slow retry with `sleep=6.0` captured `主播加油`, `CAL`, fragment `00004`, and a few later fragments (`03100`, `04000`, `04100`).
  - `fin` was not visible in the public stream.
- Result:
  - no successful end-to-end decode in room `6`.
  - reason: room/platform filtering suppressed many protocol-bearing comments even though the HTTP API returned `code=0`.
- Interpretation:
  - Room `6` is stricter than room `7777` and `23087172`.
  - For this room, the sender needs filter-aware retry/ack logic, e.g. treat `msg=f` as not publicly delivered, regenerate the same fragment with a different learned wrapper/carrier, slow down further, and retry until public visibility is observed.
- User-facing terminal scripts added:
  - `run_bili_receiver_6.ps1`
  - `run_bili_sender_6.ps1`

Full browser-simulated test on room `23087172`:

- Reason for this test:
  - The HTTP `msg/send` path triggered `10031` rate limiting under the full `replicas=3`, `fillers=2` configuration.
  - The browser-simulated path sends through the live-page input box and avoids the HTTP API frequency limit.
- Added dependency-free Chrome DevTools Protocol sender:
  - `browser_cdp.py`
  - `bilibili_browser_sender_cdp.py`
- Browser setup:
  - local Chrome launched with remote debugging
  - Bilibili cookies injected from `bilibili_cookies.json`
  - page opened at `https://live.bilibili.com/23087172`
  - input box detected as `textarea.chat-input`
- Important browser-readiness fix:
  - the first browser attempt missed early comments because the live chat component was not fully ready
  - added `--page-wait` and `--warmup-count`
  - successful run used `--page-wait 35` and `--warmup-count 3`
- Test parameters:
  - room: `23087172`
  - message: `hi#`
  - sender mode: browser/CDP simulated input
  - template mode: fixed templates
  - `replicas=3`
  - `fillers=2`
  - `sleep=1.2`
  - warmups: `3`
  - total browser sends: `95` comments (`3` warmups + `CAL` + `90` payload/filler comments + `fin`)
- Receiver result:
  - observed warm-up comment and `CAL`
  - extracted `30` mixed-carrier fragment records
  - sequence-indexed reconstruction produced `5` four-digit protocol codes
  - missing sequence count: `0`
  - extracted seed: `22`
  - extracted key length: `4`
  - reconstructed encrypted message: `EDYd`
  - decrypted plaintext: `hi#`
  - final displayed result: `成功解码: hi`
- Interpretation:
  - Full robust configuration succeeds on real Bilibili room `23087172` when sent through the browser input path.
  - The browser path is a better real-platform test method than direct HTTP for high-comment-count configurations because it avoids the HTTP API's strict rate limiter.

High-fidelity popular-style transfer test:

- Goal:
  - passively learn comment style from popular rooms
  - do not send covert traffic to unrelated popular rooms
  - replay the learned style in authorized test room `23087172`
- Passive style source:
  - rooms: `6`, `7777`
  - output directory: `popular_style_profiles_ws`
  - learned template file: `popular_style_profiles_ws/popular_templates.txt`
- Detectability comparison:
  - fixed templates:
    - `stream_z_f1 = 0.8933`
    - `stream_length_js = 0.6801`
    - `stream_punctuation_js = 0.5507`
  - popular-style templates:
    - `stream_z_f1 = 0.6667`
    - `stream_length_js = 0.1257`
    - `stream_punctuation_js = 0.1900`
- Authorized replay:
  - room: `23087172`
  - message: `hi#`
  - sender mode: browser/CDP simulated input
  - template mode: popular-room learned templates
  - `replicas=1`
  - `fillers=0`
  - `sleep=1.2`
  - `page_wait=35`
  - warmups: `1`
  - total browser sends: `17` comments (`1` warm-up + `CAL` + `14` payload comments + `fin`)
- Receiver result:
  - observed warm-up comment and `CAL`
  - extracted `14` mixed-carrier fragment records
  - sequence-indexed reconstruction produced `7` four-digit protocol codes
  - missing sequence count: `0`
  - extracted seed: `22`
  - extracted key length: `4`
  - reconstructed encrypted message: `EDYd`
  - decrypted plaintext: `hi#`
  - final displayed result: `成功解码: hi`
- Interpretation:
  - learned popular-room wrappers can replace fixed templates while preserving end-to-end decodability on the real Bilibili browser path
  - this supports the paper revision claim that room-style-adaptive template generation reduces stream-level detectability compared with fixed wrappers

Compact in-text carrier update:

- Implemented compact in-text carrier mapping in `CovLBCG_Sender_5_multimodal.py` and compatible decoding in `CovLBCG_Receiver_5_multimodal.py`.
- Legacy format: five visible mixed-carrier characters encode `seq(2) + frag_idx(1) + fragment(2)` as a trailing suffix.
- New default format:
  - packs the same logical record into a base-12 value
  - uses four common punctuation carriers from `COMPACT_CARRIER_ALPHABET`
  - embeds them inside the wrapper text instead of always appending a five-character suffix
  - receiver still supports old trailing mixed-carrier records for compatibility
- New environment flag:
  - `COVLBCG_COMPACT_EMBEDDING=0` disables the compact mapping and restores the legacy mixed suffix.
- Added `compact_embedding_experiment.py`.
- Compact-vs-legacy result:
  - legacy loaded length mean: `12.2260`
  - compact loaded length mean: `10.9940`
  - legacy loaded symbol mean: `1.2100`
  - compact loaded symbol mean: `0.0000`
  - legacy loaded Z-F1: `0.9970`
  - compact loaded Z-F1: `0.9881`
  - legacy stream length JS: `0.1244`
  - compact stream length JS: `0.0727`
- Current detectability re-check:
  - loaded-only Z-F1: `0.9852`
  - stream-level Z-F1: `0.6667`
  - stream length JS: `0.0835`
  - carrier-symbol-count JS: `0.0000`
- Comparative benchmark remains stable:
  - clean/reorder/light-loss success: `1.0000`
  - default 10% loss success: `0.9200`
  - average comments: `361.00`
- Trade-off sweep under the main `replicas=3, fillers=2` setting:
  - success at 10% loss: `0.9667`
  - loaded ratio: `0.3333`
  - loaded Z-F1: `0.9852`
  - stream Z-F1: `0.6667`
  - stream length JS: `0.0835`
- Interpretation:
  - this is an incremental loaded-only concealment improvement, not a complete solution
  - next step should be semantic punctuation placement or template-level punctuation rewriting so the four compact carrier marks align with natural clause boundaries
- Authorized real-platform compact test on room `23087172`:
  - sender mode: Chrome/CDP browser input
  - template mode: popular-room learned templates
  - carrier mode: compact in-text
  - message: `hi#`
  - parameters: `replicas=1`, `fillers=0`, `sleep=1.2`, `page_wait=35`, `warmup_count=1`
  - total browser sends: `17`
  - browser send result: `17/17 ok=True`
  - receiver result:
    - observed `CAL`
    - extracted `14` compact-carrier fragments
    - reconstructed `7` four-digit protocol codes
    - missing sequence count: `0`
    - seed: `22`
    - key length: `4`
    - encrypted message: `EDYd`
    - decrypted plaintext: `hi#`
    - final displayed result: `成功解码: hi`
  - interpretation: compact in-text mapping survives the real Bilibili browser/WebSocket path in the authorized low-flow validation
