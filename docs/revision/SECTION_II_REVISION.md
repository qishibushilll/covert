# Condensed Revision for Sections II-B and II-C

Use this text to replace the current Section II-B and Section II-C content.

## II-B. Threat Model and Basic Requirements

In live streaming bullet-comment scenarios, the covert channel is observed in a public and lossy text stream. We consider two types of external observers. The first type consists of ordinary viewers, who can see both the live content and the bullet comments but usually treat them as normal interactive messages. The second type consists of platform-side mechanisms, which can receive, forward, filter, review or suppress bullet comments according to content and behavior rules. Therefore, a covert transmission mechanism must consider not only whether the secret payload can be recovered by the receiver, but also whether the generated comments and sending behavior deviate from ordinary interaction patterns.

The public bullet-comment channel also introduces transmission uncertainty. Individual comments may be lost, delayed, reordered or partially normalized by the platform, and the receiver may observe only an incomplete subsequence of the public stream. In addition, each comment is short and publicly visible, which limits the amount of carrier information that can be embedded in a single message. These constraints make direct long-payload embedding unsuitable for this scenario.

Based on the above model, the framework is designed to satisfy three requirements. First, it should use the existing bullet-comment interaction channel without relying on private side channels. Second, it should tolerate public text-layer perturbations such as comment loss, order perturbation and local carrier damage. Third, it should support continuous communication across multiple message rounds while avoiding excessive synchronization overhead. These requirements motivate the multi-carrier packet design, redundancy mechanism and lightweight session management described in the following sections.

## II-C. Lightweight Session Advancement and Periodic Resynchronization

For continuous covert communication, each recovered message must be consistent not only at the payload layer but also at the session-state layer. Reestablishing a complete session for every message would introduce unnecessary overhead and increase the number of protocol-bearing comments. Therefore, ordinary messages use lightweight state advancement. After a message is encapsulated and authenticated, the sender advances the local session state using the current root state and the commitment value of the current round. Once the receiver successfully verifies the message, it applies the same update rule and keeps its state synchronized with the sender.

This lightweight mechanism is efficient when consecutive rounds are received successfully, but it has a clear boundary. If one or more complete message rounds are lost, the receiver may miss the commitment values required to advance along the same state chain. In this case, later protocol packets may still be reconstructed at the carrier layer, but authentication can fail because the receiver derives keys from an outdated state.

To address this problem, the framework introduces periodic resynchronization. After a configurable number of ordinary rounds, the sender inserts a resynchronization message carrying fresh key-establishment material. The receiver uses this message to derive a new epoch root state and resume subsequent communication without depending on the missing intermediate states. In this way, ordinary messages keep per-round overhead low, while periodic resynchronization provides recovery capability after complete round loss.

The resynchronization payload is fragmented and transmitted using the same carrier packetization mechanism as ordinary protected payloads. Therefore, its overhead is controlled by the same redundancy and filler-comment parameters. If the resynchronization interval is denoted by \(K\), the average per-round overhead can be expressed as the sum of ordinary message overhead and the amortized resynchronization overhead over \(K\) rounds. This formulation makes the trade-off between communication continuity, robustness and overhead explicit.

## Replacement Map

Current extracted manuscript lines:

- Replace lines 23-26 with the revised II-B text.
- Replace line 28 with the revised II-C text.
- Keep the evaluation metrics section after II-C.

Rationale:

- The revised II-B now focuses only on observers, channel uncertainty and requirements.
- The revised II-C now explains session advancement and periodic resynchronization once, without repeating the full scenario motivation.
- Detailed protocol packetization and sequence-indexed fragment recovery should remain in the method section, not in II-B.

