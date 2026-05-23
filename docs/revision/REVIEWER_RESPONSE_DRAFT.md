# Reviewer Response Draft for Submission 4306

## Response To Reviewer 1

### Comment 1: In-depth Analysis of Steganographic Undetectability

Thank you for pointing this out. We agree that decoding robustness alone is not sufficient for evaluating a covert communication framework. In the revised manuscript, we add a new stealthiness and detectability analysis subsection.

Specifically, we now evaluate comment length distribution, carrier-symbol count, carrier-punctuation count, whitespace-run features, loaded-comment density and distributional distance from benign bullet comments. We further introduce two detectors: a rule-based detector for fixed carrier suffixes and a statistical z-score detector trained from benign-comment feature statistics. Both loaded-only and stream-level views are reported. The loaded-only view represents a strong adversary that can isolate protocol-bearing comments, while the stream-level view represents an observer who sees the mixed public bullet-comment stream.

The new results show that the original fixed four-symbol suffix is trivially detectable, with rule-detector F1 equal to 1.0000. We therefore revised the carrier scheduling mechanism to use short fragments, punctuation-prioritized mixed carriers and ordinary filler comments. After this change, the fixed four-symbol rule detector drops to F1 0.0000. We also explicitly report that loaded-only comments remain distinguishable under the statistical detector, and we present this as a robustness-overhead-concealment trade-off rather than claiming perfect undetectability.

In the latest revision, we further replace the legacy five-character mixed-carrier suffix with a compact in-text carrier mapping. The logical fragment record is unchanged, but it is packed into four common punctuation carriers and embedded into the wrapper text instead of being appended as a fixed suffix. This preserves the sequence-indexed recovery result under loss while reducing loaded-comment length and eliminating special-symbol carrier usage. In the compact-vs-legacy experiment, loaded-comment mean length decreases from 12.2260 to 10.9940 and stream-level length JS divergence decreases from 0.1244 to 0.0727. Loaded-only detection remains possible, so we present this as an incremental concealment improvement.

We also validate this compact mapping on the authorized real Bilibili browser/WebSocket path. Using the learned popular-room template file in room 23087172, the sender transmits `hi#` as 17 browser-input comments. The receiver observes the calibration marker, extracts 14 compact-carrier fragments, reconstructs seven protocol codes with no missing sequence index and recovers `hi`. This is reported as a low-flow implementation validation; the statistical detectability conclusions remain based on controlled repeatable experiments.

We additionally implement a room-adaptive style learning stage. Before transmission in a target room, the sender observes recent public comments from that room and builds a room-specific template/profile file. The generated covert stream then samples wrappers and filler comments from this learned local profile rather than from a fixed global template library. In our real-room corpus experiment, this reduces stream-level length JS divergence from 0.3834 to 0.1054 and punctuation JS divergence from 0.4718 to 0.1914. We clarify that this improves stream-level naturalness but does not remove loaded-only detectability.

We further add a high-fidelity popular-room style transfer validation. Popular rooms are used only for passive style learning; no covert payload is transmitted to unrelated popular rooms. The learned template file is then replayed in the authorized test room 23087172 through the browser input path. Compared with fixed templates, the learned popular-room templates reduce stream-level z-score detector F1 from 0.8933 to 0.6667, length JS divergence from 0.6801 to 0.1257 and punctuation JS divergence from 0.5507 to 0.1900. In the authorized replay, the receiver extracts 14 mixed-carrier fragments, reconstructs seven protocol codes with no missing sequence index and recovers `hi`. We present this as evidence that room-style-adaptive wrappers can replace fixed templates while preserving decodability, not as a claim of perfect undetectability.

### Comment 2: Implementation Details of Post-Quantum Integration

Thank you for the suggestion. In the revised manuscript, we clarify that ordinary messages do not carry full post-quantum material in every round. Ordinary messages use lightweight session advancement, while post-quantum resynchronization is periodic. We further clarify that a resynchronization payload is fragmented using the same protocol packet and carrier-mapping mechanism as ordinary protected payloads.

We add an overhead discussion showing that the average overhead can be understood as an amortized quantity over the rekey interval. The revised text separates ordinary per-message overhead from periodic resynchronization overhead and explains how fragmentation and redundancy affect the number of bullet comments.

### Comment 3: Lack of Comparative Benchmarking With Existing Methods

We agree that the original evaluation focused too much on internal configurations. In the revised manuscript, we add protocol-level baseline comparisons with two representative approaches: a time-modulation baseline and a natural-comment/comment-choice baseline. These are described as protocol-level reproductions under the same lossy public text-layer channel, not as the original authors' code.

Under clean and reorder-only conditions, all methods recover successfully. Under light loss, the proposed method achieves 1.0000 success after sequence-indexed redundancy, while the two simplified baselines fail because loss shifts their repeated timing or comment-choice groups. Under the default 10% loss condition, the proposed method achieves 0.9200 success, while both baselines remain at 0.0000 in this reproduction. The revised paper reports success rate, average number of comments, rule-detector F1, statistical-detector F1 and length JS divergence.

We also add a small-scale real-platform feasibility validation on Bilibili live room 6963590. A short test message was encoded into 17 bullet comments and successfully recovered by the receiver from the actual live bullet-comment stream. We report this only as an implementation feasibility check; the robustness and detectability claims are based on the controlled repeatable experiments.

## Response To Reviewer 2

### Comment: Evaluation of Stealthiness/Anti-Detection Is Weak

Thank you for this important comment. We add adversarial detectability experiments and explicitly analyze the capacity-concealment trade-off. The revised evaluation includes rule-based and statistical detectors, benign/covert distributional comparisons and two evaluation views: loaded-only and stream-level.

The results show that stream-level concealment improves after short-fragment scheduling and filler-comment insertion. However, loaded-only comments remain distinguishable, especially when sequence-indexed redundancy is enabled. We now discuss this limitation explicitly and avoid claiming perfect undetectability. Instead, the revised manuscript presents the framework as configurable: increasing redundancy improves recovery under loss, while increasing filler comments reduces loaded-comment density and stream-level statistical deviation at the cost of more public comments.

### Comment: Analyze Trade-Off Between Bandwidth Capacity and Concealment

We add a parameter sweep over fragment replicas and filler-comment count. The sweep shows how success rate, average number of comments, loaded-comment ratio, statistical detector F1 and length JS divergence change under the default lossy channel. For example, with `FRAGMENT_REPLICAS=3` and `FILLERS_PER_PAYLOAD=2`, the system achieves 0.9667 success under 10% loss in the sweep, with an average of 361 comments and a loaded ratio of 0.3333. Increasing the filler count lowers loaded-comment density but increases traffic; increasing replicas improves robustness but also increases overhead and loaded-comment detectability.

This new experiment directly supports the robustness-overhead-concealment trade-off analysis requested by the reviewer.

### Comment: Sections II-B and II-C Contain Duplicated Text

We have condensed Sections II-B and II-C. The revised II-B focuses on the threat model, observer capabilities, platform filtering and basic requirements. Detailed discussion of lightweight session advancement and periodic resynchronization is moved to the method section, where it is connected to the protocol workflow. This removes repeated motivation and makes the framework description more concise.

## Summary Of Major Revisions

1. Added stealthiness and detectability experiments with rule-based and statistical detectors.
2. Added loaded-only and stream-level evaluation views.
3. Replaced the fixed four-symbol suffix design with short-fragment mixed-carrier scheduling.
4. Added sequence-indexed redundant fragment recovery for loss tolerance.
5. Added protocol-level comparisons with time-modulation and natural-comment/comment-choice baselines.
6. Added a robustness-overhead-concealment parameter sweep.
7. Clarified post-quantum resynchronization overhead and fragmentation.
8. Condensed the duplicated discussion in Sections II-B and II-C.
9. Added a pre-transmission room-style learning stage and a small-scale real-platform feasibility validation.
