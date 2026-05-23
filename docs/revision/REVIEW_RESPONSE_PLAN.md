# Submission 4306 Review Response Plan

Paper: `A Multi Carrier Covert Communication Framework for Live Streaming Bullet Comments`

Local source examined:

- `D:\Study\论文\Nana\殷亮亮\A Multi Carrier Covert Communication Framework for Live Streaming Bullet Comments.docx`
- Extracted text: `paper_submission_4306_extracted.txt`

## Main Reviewer Concerns

1. **Steganographic undetectability is under-evaluated.**
   - Both reviewers ask for statistical detectability or adversarial detection experiments.
   - The current paper mainly reports recovery/robustness, not distributional similarity to normal bullet comments.

2. **PQ integration is not detailed enough.**
   - Reviewer 1 specifically asks how large ML-KEM/Kyber ciphertext material is fragmented across short bullet comments.
   - The paper should separate ordinary lightweight session advancement from less frequent PQ resynchronization and report the amortized overhead.

3. **Comparative benchmarking is insufficient.**
   - Current evaluation mainly compares internal carrier strategies and redundancy values.
   - The paper claims better reliability than existing work, but does not directly benchmark time-modulation or natural-language-generation baselines.

4. **Sections II-B and II-C should be condensed.**
   - Current lines 23-28 repeat scenario constraints, continuous communication motivation, and synchronization requirements.
   - Condense II-B to threat/requirements and move session/PQ mechanism details to the method section.

## Required Manuscript Changes

### A. Add Stealthiness Evaluation

Add a new subsection after the lossy-channel experiments:

`D. Stealthiness and Detectability Analysis`

Suggested metrics:

- Carrier-symbol frequency distribution.
- Punctuation distribution.
- Whitespace-run distribution.
- Comment length distribution.
- Loaded-comment ratio in a sliding window.
- Inter-arrival time distribution if real sending logs are available.
- Statistical distance from benign bullet comments, e.g. chi-square distance, Jensen-Shannon divergence, or Kolmogorov-Smirnov distance.
- Binary detector performance: accuracy, precision, recall, F1, and ROC-AUC if enough samples are available.

Suggested detectors:

- Rule-based detector: abnormal count of carrier symbols, long whitespace runs, or high loaded-comment density.
- Statistical detector: z-score or chi-square anomaly score against benign bullet comment profiles.
- Lightweight ML detector: logistic regression or random forest on text-level features, if `scikit-learn` is available.

Important expected conclusion:

- Do not claim perfect undetectability.
- Claim that carrier scheduling, low loaded-comment density, and mixed natural templates reduce statistical deviation under the tested profile.
- Report the bandwidth/stealth trade-off explicitly.

Current baseline warning:

- Script: `detectability_baseline_test.py`
- Command: `C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe -X utf8 .\detectability_baseline_test.py`
- Result on the original fixed-symbol-suffix baseline:
  - Benign mean carrier-symbol count: `0.0000`
  - Covert mean carrier-symbol count: `4.0000`
  - Rule detector `ends_with_four_symbols`: precision `1.0000`, recall `1.0000`, F1 `1.0000`
  - Z-score detector: accuracy `1.0000`, precision `1.0000`, recall `1.0000`, F1 `1.0000`

Interpretation: the original implementation is robust enough for a clean offline communication baseline, but it is not stealthy. The fixed four-symbol suffix is trivially detectable.

Current implemented stealth adjustment:

- Sender now uses two-digit protocol fragments instead of four-digit suffixes.
- Sender uses punctuation-prioritized per-digit mixed carriers: each digit in a two-digit fragment independently selects punctuation or symbol, with a `3:1` punctuation-to-symbol weight.
- Sender uses a sparse payload suffix set, mostly empty, to reduce loaded-comment length and punctuation inflation.
- Each protocol-bearing bullet comment is followed by ordinary distraction comments.
- Receiver now supports both symbol and punctuation suffix decoding, extracts the rightmost short carrier fragment and reassembles two fragments into one four-digit protocol code.

Current detectability result after the adjustment:

- Loaded-only profile:
  - Loaded ratio: `0.3333`
  - Rule detector `ends_with_four_symbols` F1: `0.0000`
  - Z-score detector F1: `0.9133`
  - Length JS distance: `0.2226`
  - Carrier-symbol-count JS distance: `0.2728`
- Stream-level profile:
  - Loaded ratio: `0.3333`
  - Rule detector `ends_with_four_symbols` F1: `0.0000`
  - Z-score detector F1: `0.6667`
  - Length JS distance: `0.0150`
  - Carrier-symbol-count JS distance: `0.0816`

Interpretation: short-fragment scheduling removes the most obvious fixed four-symbol suffix pattern and improves stream-level distributional similarity. Loaded-only comments remain distinguishable mainly because each loaded comment is still longer and has more carrier punctuation than benign comments. The next research step should reduce the per-loaded-comment signal further, for example by using one-digit punctuation fragments with stronger packet validation, carrier placement inside existing punctuation positions, or benign-template balancing by length bucket.

One-digit fragment pilot:

- A one-digit fragment version was tested as a more aggressive concealment strategy.
- Without a boundary marker, it reduced loaded-only statistical detector F1 to about `0.8256`, but the receiver confused ordinary template punctuation with one-digit fragments and clean round-trip decoding failed.
- With explicit boundary markers, clean round-trip decoding was restored, but the boundary itself became a detectable feature; loaded-only statistical detector F1 returned to about `0.9618`.
- The one-digit approach also doubled the number of protocol-bearing fragments compared with two-digit fragments.

Conclusion: the current two-digit, punctuation-prioritized, low-density fragment strategy is the better practical operating point for the main implementation. The one-digit variant is useful as a trade-off experiment but not yet suitable as the primary protocol path.

Carrier weighting pilot:

- A pure-punctuation fragment version was tested.
- It removed carrier-symbol count anomalies, but increased punctuation count on loaded comments and raised loaded-only statistical detector F1 back to about `0.9728`.
- The `3:1` punctuation-to-symbol per-digit mix is currently better for the loaded-only detector, with F1 about `0.9133`, while preserving clean round-trip decoding.

### B. Add PQ Overhead and Fragmentation Details

Add a subsection in the session mechanism part:

`Post-Quantum Resynchronization Overhead`

Clarify:

- Ordinary messages do not carry a full PQ ciphertext.
- PQ material is only inserted every `K` rounds or after recovery failure.
- A PQ resynchronization message is fragmented into the same protocol packet format as ordinary protected payloads.
- The overhead is amortized across a session:

`O_avg = O_ord + O_pq / K`

where `O_ord` is ordinary per-round overhead, `O_pq` is the additional PQ resynchronization payload size, and `K` is the rekey interval.

Also report:

- PQ ciphertext bytes.
- Number of protocol packets required.
- Number of bullet comments after redundancy.
- Average bullet comments per ordinary round under each rekey interval.

Implementation warning:

- The current `CovLBCG_*_5_multimodal.py` baseline imports `pqcrypto.kem.ml_kem_512`, but the active `PostQuantumEncryption` path uses a seed-derived XOR stream for the message payload. For the revised paper, either implement a real ML-KEM resynchronization experiment or narrow the claim to a simulated/PQ-ready resynchronization layer.

### C. Add External Baselines

Add a direct comparison table:

`Table X. Comparison with Existing Covert Bullet-Comment Methods`

Baselines:

- Time modulation baseline based on references [1], [2].
- Natural-language/comment-generation baseline based on reference [5].
- Proposed symbol-only.
- Proposed punctuation-only.
- Proposed space-only.
- Proposed multimodal.

Metrics:

- Decoding success rate under the same lossy channel.
- Average bullet comments per message.
- Robustness under reordering.
- Robustness under symbol/punctuation/space damage.
- Detectability score or detector F1.

If exact reimplementation of prior work is not possible, state:

- The baselines are protocol-level reproductions under the same channel model, not authors' original implementations.
- Parameters are chosen to match the reported carrier assumptions as closely as possible.

Current external-baseline benchmark:

- Script: `comparative_benchmark.py`
- Command: `C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe -X utf8 .\comparative_benchmark.py`
- Baselines:
  - `time_modulation`: protocol-level timing-gap baseline with repeated bits.
  - `nlg_comment_choice`: protocol-level natural-comment choice baseline with repeated 2-bit symbols.
  - `proposed`: current CovLBCG sender/receiver path.
- Trials: `50`
- Message: `CovLBCG_test_123#`

| Condition | Loss | Reorder | Method | Success | Avg. Comments | Rule F1 | Stat. F1 | Length JS |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| clean | 0.00 | 0.00 | proposed | 1.0000 | 121.00 | 0.0000 | 0.6667 | 0.0198 |
| clean | 0.00 | 0.00 | time_modulation | 1.0000 | 409.00 | 0.0000 | 0.6667 | 0.0029 |
| clean | 0.00 | 0.00 | nlg_comment_choice | 1.0000 | 204.00 | 0.0000 | 0.6667 | 0.3018 |
| reorder_only | 0.00 | 0.10 | proposed | 1.0000 | 121.00 | 0.0000 | 0.6667 | 0.0198 |
| reorder_only | 0.00 | 0.10 | time_modulation | 1.0000 | 409.00 | 0.0000 | 0.6667 | 0.0029 |
| reorder_only | 0.00 | 0.10 | nlg_comment_choice | 1.0000 | 204.00 | 0.0000 | 0.6667 | 0.3018 |
| light_loss | 0.02 | 0.10 | proposed | 0.4400 | 121.00 | 0.0000 | 0.6667 | 0.0198 |
| light_loss | 0.02 | 0.10 | time_modulation | 0.0000 | 409.00 | 0.0000 | 0.6667 | 0.0027 |
| light_loss | 0.02 | 0.10 | nlg_comment_choice | 0.0000 | 204.00 | 0.0000 | 0.6667 | 0.3018 |
| default_loss | 0.10 | 0.10 | proposed | 0.0000 | 121.00 | 0.0000 | 0.6667 | 0.0198 |
| default_loss | 0.10 | 0.10 | time_modulation | 0.0000 | 409.00 | 0.0000 | 0.6667 | 0.0017 |
| default_loss | 0.10 | 0.10 | nlg_comment_choice | 0.0000 | 204.00 | 0.0000 | 0.6667 | 0.3018 |

Interpretation:

- The current implementation is more comment-efficient than the two simplified baselines under clean and reorder-only settings.
- Under light loss, the current implementation still recovers some trials while the two simplified baselines fail because loss shifts repeated timing/comment groups.
- Under the paper's default 10% loss setting, the current implementation also fails because protocol fragments do not yet carry explicit sequence identifiers or loss-tolerant grouping metadata.
- Next protocol work: add sequence-indexed redundant fragments or packet-level metadata so the receiver can recover fragment positions under loss instead of relying on strict arrival order.

Sequence-indexed redundancy update:

- Implemented sequence-indexed redundant fragments in `CovLBCG_Sender_5_multimodal.py`.
- Each four-digit protocol code is split into two two-digit fragments.
- Each fragment carries `seq(2 digits) + frag_idx(1 digit) + fragment(2 digits)` and is sent with `FRAGMENT_REPLICAS = 3`.
- Receiver groups fragments by sequence number and fragment index, applies majority voting and reconstructs the four-digit protocol code in sequence order.

Updated benchmark after sequence-indexed redundancy:

| Condition | Loss | Reorder | Method | Success | Avg. Comments | Rule F1 | Stat. F1 | Length JS |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| clean | 0.00 | 0.00 | proposed | 1.0000 | 361.00 | 0.0000 | 0.6667 | 0.1253 |
| reorder_only | 0.00 | 0.10 | proposed | 1.0000 | 361.00 | 0.0000 | 0.6667 | 0.1253 |
| light_loss | 0.02 | 0.10 | proposed | 1.0000 | 361.00 | 0.0000 | 0.6667 | 0.1253 |
| default_loss | 0.10 | 0.10 | proposed | 0.9200 | 361.00 | 0.0000 | 0.6667 | 0.1253 |

Trade-off:

- Robustness improves substantially: default 10% loss success increases from `0.0000` to `0.9200`.
- Communication overhead increases: average comments for the benchmark message increase from `121.00` to `361.00`.
- Detectability cost increases for loaded comments because each fragment now contains metadata as well as data. This should be presented as the redundancy-concealment trade-off.

Replica-count pilot:

| Fragment Replicas | Avg. Comments | Light Loss Success | Default 10% Loss Success |
|---:|---:|---:|---:|
| 2 | 241.00 | 0.9800 | 0.6000 |
| 3 | 361.00 | 1.0000 | 0.9200 |

Interpretation: `FRAGMENT_REPLICAS = 2` provides a lower-overhead operating point, but `FRAGMENT_REPLICAS = 3` is retained as the main manuscript configuration because it better supports the 10% loss robustness claim.

Replica/filler sweep:

- Script: `tradeoff_sweep.py`
- Command: `C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe -X utf8 .\tradeoff_sweep.py`
- Trials per setting: `30`
- Channel: `p_loss=0.10`, `reorder_jitter=0.10`

| Replicas | Fillers | Success | Avg. Comments | Loaded Ratio | Loaded Z-F1 | Stream Z-F1 | Stream Length JS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 0.0000 | 81.00 | 0.5000 | 1.0000 | 0.6967 | 0.2244 |
| 1 | 2 | 0.0000 | 121.00 | 0.3333 | 1.0000 | 0.6667 | 0.1307 |
| 1 | 3 | 0.0333 | 161.00 | 0.2500 | 1.0000 | 0.6667 | 0.0960 |
| 2 | 1 | 0.5333 | 161.00 | 0.5000 | 1.0000 | 0.6875 | 0.2200 |
| 2 | 2 | 0.6333 | 241.00 | 0.3333 | 1.0000 | 0.6667 | 0.1255 |
| 2 | 3 | 0.6333 | 321.00 | 0.2500 | 1.0000 | 0.6667 | 0.0981 |
| 3 | 1 | 0.8667 | 241.00 | 0.5000 | 1.0000 | 0.6888 | 0.2203 |
| 3 | 2 | 0.9667 | 361.00 | 0.3333 | 1.0000 | 0.6667 | 0.1226 |
| 3 | 3 | 0.9333 | 481.00 | 0.2500 | 1.0000 | 0.6667 | 0.0903 |
| 4 | 1 | 0.9667 | 321.00 | 0.5000 | 1.0000 | 0.6822 | 0.2158 |
| 4 | 2 | 0.9667 | 481.00 | 0.3333 | 1.0000 | 0.6667 | 0.1287 |
| 4 | 3 | 0.9667 | 641.00 | 0.2500 | 1.0000 | 0.6667 | 0.0873 |

Operating-point interpretation:

- `Replicas=3, Fillers=2` is the current main setting: high robustness (`0.9667`) with moderate loaded-comment ratio (`0.3333`) and lower overhead than `Replicas=4, Fillers=2`.
- `Replicas=4, Fillers=1` is a robustness-oriented alternative with the same measured success (`0.9667`) and fewer comments (`321.00`), but it has a much higher loaded ratio (`0.5000`) and worse stream length distribution (`0.2158`).
- `Replicas=3, Fillers=3` is a concealment-oriented alternative with lower stream length JS (`0.0903`) but more comments (`481.00`) and slightly lower success (`0.9333`).
- Loaded-only detection remains easy in all sequence-indexed settings because metadata-bearing fragments are structurally different from benign comments. The manuscript should therefore report both loaded-only and stream-level detector views.

Room-adaptive wrapper experiment:

- Added `room_adaptive_stealth_experiment.py`.
- Added optional sender support for `room_comments.txt`.
- Added `room_style_learner.py` as a general pre-transmission learning stage.
- Instead of relying only on fixed templates, the sender first observes the target live room, generates room-specific templates/profile files, and then selects payload wrappers and filler comments from that learned local profile.
- With the synthetic room corpus used in the initial experiment:

| Method | Loaded Len Mean | Stream Len Mean | Loaded Z-F1 | Stream Z-F1 | Stream Length JS | Stream Punctuation JS | Duplicate Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed templates | 12.2160 | 9.3300 | 1.0000 | 0.6667 | 0.1593 | 0.2743 | 0.6280 |
| room adaptive | 8.9280 | 8.1840 | 1.0000 | 0.6667 | 0.0341 | 0.1900 | 0.2720 |

Interpretation: room-adaptive sampling reduces template repetition and stream-level distributional deviation. It should be presented as a pre-communication style-learning step and a stream-level concealment improvement, not as a complete solution to loaded-only detectability.

Real-room corpus update:

- Fetched public history comments from Bilibili live room `6963590` into `room_comments.txt`.
- Current real-room corpus size: `18` comments.
- With this small real-room corpus:

| Method | Loaded Len Mean | Stream Len Mean | Loaded Z-F1 | Stream Z-F1 | Stream Length JS | Stream Punctuation JS | Duplicate Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed templates | 12.2160 | 9.3300 | 0.9785 | 0.8420 | 0.3834 | 0.4718 | 0.6280 |
| room adaptive | 12.8340 | 9.8800 | 0.9728 | 0.6667 | 0.1054 | 0.1914 | 0.6320 |

Interpretation: the real-room adaptive setting lowers stream-level detector F1 and distributional divergence. Duplicate rate does not improve in this run because only 18 real comments were available; this caveat should be stated.

Real-platform feasibility update:

- Added `bilibili_full_http_sender_probe.py` and `bilibili_full_receiver_probe.py`.
- Completed one small-scale end-to-end test on Bilibili live room `6963590`.
- Message: `hi#`.
- Parameters: `replicas=1`, `fillers=0` to minimize public-room traffic.
- Transmission: `17` comments total (`CAL`, `14` protocol-bearing fragments, `fin`, plus one warm-up ordinary comment).
- Platform API result: all send requests returned `code=0`.
- Receiver result: extracted `14` mixed-carrier fragment records, reconstructed `7` protocol codes with missing sequence count `0`, and decoded `hi`.
- Manuscript usage: report only as implementation feasibility validation; keep statistical robustness and detectability claims based on controlled repeatable experiments.

### D. Condense Sections II-B and II-C

Suggested edit:

- II-B: keep only observer model, platform filtering, length/frequency constraints, and three requirements.
- Move the detailed lightweight advancement and PQ resynchronization description from II-C to the method section.
- Shorten duplicated motivation about continuous communication and state loss.

## Proposed Response To Reviewers

Reviewer 1, Comment 1:

We agree that robustness alone is insufficient for evaluating a covert communication framework. In the revised manuscript, we add a new stealthiness and detectability evaluation. We compare benign bullet comments and generated covert comments using length, punctuation, carrier-symbol, whitespace-run, loaded-comment-density, and timing features. We further evaluate rule-based and statistical detectors and report the bandwidth-concealment trade-off under different redundancy and carrier-scheduling settings.

We also add a room-adaptive style learning stage. Instead of relying only on a fixed template library, the sender first observes the target room and builds a room-specific template/profile file. It then samples learned local comments as wrappers and filler comments. This reduces stream-level length and punctuation divergence in our real-room corpus experiment, while loaded-only comments remain detectable due to protocol metadata.

Reviewer 1, Comment 2:

We clarify that the post-quantum material is not attached to every ordinary message. Ordinary messages use lightweight session advancement, while ML-KEM-based resynchronization is inserted periodically. We add fragmentation details showing how the resynchronization payload is serialized into protocol packets and distributed across bullet comments, and we report the number of additional packets and amortized overhead under different rekey intervals.

Reviewer 1, Comment 3:

We add direct baseline comparisons with time-modulation and natural-language-generation style covert channels under the same lossy channel model. The revised evaluation reports decoding success, overhead, sensitivity to reordering and text cleaning, and detectability scores for each method.

We additionally report a small-scale real-platform feasibility validation on Bilibili live room 6963590. A short message was encoded into 17 bullet comments and recovered by the receiver from the actual live bullet-comment stream. This is presented as implementation evidence only, not as a replacement for controlled robustness and detectability experiments.

Reviewer 2:

We add adversarial detectability experiments and explicitly analyze the trade-off between capacity and concealment. We also condense Sections II-B and II-C by removing repeated scenario motivation and moving session-resynchronization details to the method section.
