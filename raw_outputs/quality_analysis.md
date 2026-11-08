# Quality Analysis — Where the Tool Picks Badly

## Methodology

The promo finder employs a hybrid evaluation pipeline:
1. **Normalized dramatic density** — emotional tags (dialogue) + physical spectacle cues (action/sound).
2. **Hook strength** — physical conflict, shocking reveals, or high-stakes lines in the first 3 seconds.
3. **Cliffhanger tension** — unresolved questions, threats, or boundary cuts leaving maximum tension.
4. **Standalone clarity** — penalizes crowded scenes (5+ characters) and rewards focused 2-3 character tension.
5. **Narrative juxtaposition** — identifies high-contrast cross-episode bridges (setup + twist payoff).

## Known Failure Modes & Tool Limitations

### 1. Inability to evaluate visual performance and actor delivery
The tool inspects screenplay text, not recorded footage. A dramatic line like 'I cannot marry you' can be
delivered weakly on camera, or a silent 2-second stare can be mesmerizing. The tool will rate a line
solely based on written emotion tags ('Heartbroken', 'Cold') and cannot detect audio mixing or actor chemistry.

### 2. Dialogue-sparse visual climaxes require explicit action descriptions
Although we added ACTION keyword parsing, scenes with prolonged physical choreography (e.g. sword fights,
stealth infiltrations) that have minimal spoken lines can still receive lower drama scores than rapid-fire verbal
arguments, despite being visually magnetic on video platforms like TikTok.

### 3. Subtextual cliffhangers missed without explicit triggers
The algorithm reliably catches explicit cliffhangers ('Stop!', 'Who are you?', 'No!'), but can miss subtle,
unspoken dread—such as a character secretly pocketing a poison vial or an ominous smirk unnoticed by others.

### 4. Splice point boundary roughness in multi-segment promos
For cross-episode and juxtaposition promos (e.g. Ep 1 betrayal + Ep 3 proposal), the tool identifies the
story beats accurately, but cannot determine whether the ambient audio (church organ, background rain) matches
across the cut. An editor must insert a transition or title card.

### 5. False positive hooks from formal dialogue tags
Certain high-frequency courtly words ('Your Grace', 'Father') can trigger false relevance when surrounding
dialogue is mundane exposition rather than a genuine scroll-stopping hook.

## Per-Promo Quality Audit

**Rank #1** [Ep41, Ep1, Ep3] — ⚠️ Review Edit
  - Visual-only hook in first 3s (no spoken line) — relies on visual action
  - Multi-segment cut: requires title card or smash cut between scenes

**Rank #2** [Ep31, Ep2, Ep4] — ⚠️ Review Edit
  - Visual-only hook in first 3s (no spoken line) — relies on visual action
  - Multi-segment cut: requires title card or smash cut between scenes

**Rank #3** [Ep28, Ep1, Ep42] — 🔍 Experimental
  - Visual-only hook in first 3s (no spoken line) — relies on visual action
  - Duration > 50s: requires fast-paced visual editing for TikTok retention
  - High character count (9): may confuse viewer unfamiliar with lore
  - Multi-segment cut: requires title card or smash cut between scenes

**Rank #4** [Ep24] — ✅ High Confidence
  - Short clip (< 22s): ensures high completion rate, but minimal character setup

**Rank #5** [Ep43] — ✅ High Confidence
  - Short clip (< 22s): ensures high completion rate, but minimal character setup

**Rank #6** [Ep28, Ep43] — 🔍 Experimental
  - Visual-only hook in first 3s (no spoken line) — relies on visual action
  - Duration > 50s: requires fast-paced visual editing for TikTok retention
  - High character count (6): may confuse viewer unfamiliar with lore
  - Multi-segment cut: requires title card or smash cut between scenes

**Rank #7** [Ep3] — ✅ High Confidence
  - Verified clean hook-to-cliffhanger progression

**Rank #8** [Ep15] — ⚠️ Review Edit
  - Visual-only hook in first 3s (no spoken line) — relies on visual action
  - Short clip (< 22s): ensures high completion rate, but minimal character setup

**Rank #9** [Ep43] — ✅ High Confidence
  - Short clip (< 22s): ensures high completion rate, but minimal character setup

**Rank #10** [Ep33] — ✅ High Confidence
  - Short clip (< 22s): ensures high completion rate, but minimal character setup

**Rank #11** [Ep24] — ✅ High Confidence
  - Verified clean hook-to-cliffhanger progression

**Rank #12** [Ep42] — ✅ High Confidence
  - Short clip (< 22s): ensures high completion rate, but minimal character setup

**Rank #13** [Ep1, Ep3] — ✅ High Confidence
  - Multi-segment cut: requires title card or smash cut between scenes

**Rank #14** [Ep14] — ✅ High Confidence
  - Visual-only hook in first 3s (no spoken line) — relies on visual action

**Rank #15** [Ep3] — ✅ High Confidence
  - Verified clean hook-to-cliffhanger progression

**Rank #16** [Ep15] — ✅ High Confidence
  - Short clip (< 22s): ensures high completion rate, but minimal character setup

**Rank #17** [Ep41, Ep42] — 🔍 Experimental
  - Visual-only hook in first 3s (no spoken line) — relies on visual action
  - Duration > 50s: requires fast-paced visual editing for TikTok retention
  - High character count (6): may confuse viewer unfamiliar with lore
  - Multi-segment cut: requires title card or smash cut between scenes

**Rank #18** [Ep2] — ✅ High Confidence
  - Verified clean hook-to-cliffhanger progression

**Rank #19** [Ep33] — ✅ High Confidence
  - Verified clean hook-to-cliffhanger progression

**Rank #20** [Ep11] — ✅ High Confidence
  - Verified clean hook-to-cliffhanger progression

## Production Statistics

- Total promos generated: 20
- Distinct episodes featured: 14 / 50 (28%)
- Average promo duration: 31.8s (Optimal for Reels & TikTok)
- Multi-segment / Cross-episode promos: 6
- Ready-to-cut promos (<= 1 review note): 20