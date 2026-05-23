# Next Revision Tasks

## Manuscript Editing

Done in local support files:

- `中文_审稿回复草稿.md` now contains a direct Chinese rebuttal draft.
- `MANUSCRIPT_REVISION_TEXT.md` now includes the popular-room passive style learning and authorized replay validation.
- `REVIEWER_RESPONSE_DRAFT.md` now mentions the popular-room style transfer experiment.
- `MANUSCRIPT_REVISION_TEXT.md` and response drafts now include compact in-text carrier mapping as an incremental loaded-only concealment improvement.

Remaining manuscript insertion tasks:

1. Insert `MANUSCRIPT_REVISION_TEXT.md` Section 1 into the evaluation-metrics part.
2. Add the stealthiness/detectability subsection after the lossy-channel experiment setup.
3. Add the sequence-indexed redundant fragment recovery description to the method section.
4. Add the external baseline comparison table to the performance evaluation section.
5. Add the trade-off sweep table after the baseline comparison.
6. Add the limitations paragraph near the end of the evaluation or conclusion.
7. Add a short real-platform feasibility paragraph after the controlled experiments, clearly stating that it is not the basis for statistical robustness or detectability claims.
8. Add the room-style learning stage to the method section before the sender-side carrier mapping workflow.
9. Add the popular-room passive style learning and authorized-room replay validation as a small-scale high-fidelity validation, not as proof of perfect undetectability.
10. Add compact in-text carrier mapping to the carrier scheduling subsection and report it as incremental concealment improvement, not complete undetectability.

## Section II-B / II-C Condensing

1. Keep II-B focused on observer model, platform filtering, message loss/reordering and basic requirements.
2. Remove repeated continuous-session motivation from II-B.
3. Move detailed lightweight advancement and PQ resynchronization mechanics into the method section.
4. Keep the resynchronization part short unless the final paper includes a dedicated overhead table.

## Figure And Table Work

1. Add a detector comparison table:
   - fixed-symbol suffix baseline
   - short-fragment scheduling
   - sequence-indexed redundancy
2. Add the external baseline comparison table.
3. Add the replica/filler sweep table.
4. Optionally convert the sweep table into a figure:
   - x-axis: average comments
   - y-axis: success rate
   - marker color: loaded ratio or stream length JS
5. Optionally add a small implementation-validation table:
   - platform room
   - message length
   - transmitted comments
   - extracted fragments
   - recovered plaintext

## Experimental Caveats To State

1. The external baselines are protocol-level reproductions under a shared channel model, not original author implementations.
2. Loaded-only comments remain detectable under the current metadata-bearing redundancy design.
3. The proposed method improves stream-level concealment but should not be claimed as perfectly undetectable.
4. The selected operating point `FRAGMENT_REPLICAS=3`, `FILLERS_PER_PAYLOAD=2` prioritizes robustness under 10% loss.
5. The real Bilibili test is only a small-scale feasibility validation using `replicas=1`, `fillers=0`; do not present it as large-scale platform evidence.
6. Room-style learning improves stream-level naturalness, but it does not make metadata-bearing loaded comments fully indistinguishable.
7. Compact in-text carrier mapping reduces loaded length and removes special-symbol carriers, but loaded-only F1 remains high.

## Code Baseline To Preserve

Current main operating point:

- `FRAGMENT_REPLICAS = 3`
- `FILLERS_PER_PAYLOAD = 2`
- `PROTOCOL_FRAGMENT_SIZE = 2`
- sequence-indexed redundant fragment format: `seq + frag_idx + fragment`

Validation commands:

```powershell
& 'C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe' -X utf8 .\offline_baseline_test.py
& 'C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe' -X utf8 .\comparative_benchmark.py
& 'C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe' -X utf8 .\tradeoff_sweep.py
```

Real-platform feasibility commands:

```powershell
& 'C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe' -X utf8 .\room_style_learner.py --room 6963590 --target-count 80 --rounds 12 --sleep 5
& 'C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe' -X utf8 .\bilibili_full_http_sender_probe.py --room 6963590 --message 'hi#' --replicas 1 --fillers 0 --learn-style --learn-target-count 80 --learn-rounds 12 --learn-sleep 5 --max-comments 60
& 'C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe' -X utf8 .\bilibili_full_receiver_probe.py --room 6963590 --seconds 300
& 'C:\Users\15052\AppData\Local\Programs\Python\Python313\python.exe' -X utf8 .\bilibili_full_http_sender_probe.py --room 6963590 --message 'hi#' --replicas 1 --fillers 0 --learn-style --learn-target-count 80 --learn-rounds 12 --learn-sleep 5 --max-comments 60 --send
```
