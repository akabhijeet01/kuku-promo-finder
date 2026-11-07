# Solution Document — Problem 1: Find the Promos

**Abhijeet Kumar** | Kuku AI Generalist Assignment

---

## Problem Choice & Why

I chose Problem 1 because it's a clean information retrieval problem with a clear evaluation signal: does the clip make you stop scrolling and want to watch the show? The input pack gives 50 timestamped screenplays — structured enough to build a real tool, messy enough to require thoughtful engineering.

## Assumptions

- A "promo" is a 20–60 second continuous clip (or a splice of 2–3 short clips).
- The screenplay's emotion tags (e.g., "Furious", "Devastated") are reliable signals of dramatic intensity.
- CAMERA and ACTION blocks describe visual composition but cannot replace actual footage review.
- A good promo for social media is 25–40 seconds; longer clips risk losing scrollers on TikTok.
- "Standalone clarity" means a first-time viewer understands the emotional stakes without knowing character backstories.

## How It Works

**Architecture: Rule-based engine + optional LLM re-ranking.**

1. **Parse**: Custom parser converts each screenplay into structured data — episodes → scenes → timestamped dialogue lines and action beats.

2. **Sliding window search**: For every episode, scan all 20–55 second windows (5s step). Score each window on four dimensions:
   - *Emotional intensity*: scored from dialogue emotion tags, normalized per 30s to avoid length bias
   - *Hook strength*: keyword detection for violence, reveals, shocking lines (slap, betray, propose)
   - *Cliffhanger quality*: unresolved phrases ("Who are you?", "No!") + proximity to scene/episode boundaries
   - *Standalone clarity*: character count as a proxy (2–3 characters = clearer than 6)

3. **Deduplicate**: Overlapping windows merged, highest score kept. Max 2 promos per episode ensures coverage.

4. **Cross-episode promos**: Last 15s of episode N + first 15s of episode N+1, scored for setup→payoff tension.

5. **LLM enhancement** (optional): Sends candidates to Gemini Flash for semantic evaluation and re-ranking. Model is a single function call — easy to swap.

## Top 5 Promos — Why Post These First

| # | Episode | Time | Duration | Hook | Why Post First |
|---|---------|------|----------|------|----------------|
| 1 | Ep 3 | 0:00–0:55 | 55s | "Look at you…" (sister gloating at stolen wedding) | Universal jealousy/betrayal, zero context needed |
| 2 | Ep 28 | 0:10–1:05 | 55s | Catherine framing Juliana for poisoning | Villain reveal + falsely accused heroine = rage bait |
| 3 | Ep 11 | 0:10–0:50 | 40s | Gerald accusing Alexander of theft | Love triangle confrontation, punchy at 40s |
| 4 | Ep 3 | 0:50–1:45 | 55s | Stranger rescuing Juliana from guards | Rescue fantasy hook, ends on "Who are you?" |
| 5 | Ep 43 | 0:55–1:50 | 55s | Crown exposing Rupert's treason | Satisfying villain takedown, standalone justice story |

**Posting strategy**: Lead with Rank 1 (wedding betrayal = most universal). Follow with Rank 4 (mysterious savior = curiosity gap). Rank 2 for rage engagement. Rank 5 for satisfying payoff content.

## Where It Fails (Quality Check)

| Failure Mode | Example | Why |
|---|---|---|
| Keyword ≠ semantic hook | "Look at you…" scores high but the *visual* (sister in gold gown) is the real hook | Tool reads text, not images |
| Length bias | Despite normalization, 55s windows still dominate the top 10 | Dense drama concentrates in long scenes |
| Missing quiet power | Ep 1's final shot (hand clenching gown, tears hardening to defiance) ranks poorly | Minimal dialogue = low score, but iconic visual |
| Standalone confusion | Ep 42's 6-character courtroom scene ranks #7 but would confuse a new viewer | Character count used as positive signal, should be negative past 3 |
| 28% episode coverage | Only 14 of 50 episodes appear in the top 20 | Drama peaks are real — not all episodes have promo material |

## How It Scales

The rule-based engine processes 50 episodes in **<1 second**, no API cost. LLM pass adds ~10s per batch. At Kuku's weekly release cadence: a new show's promos are ready in seconds, an editor reviews a shortlist of 5 instead of watching all episodes. Cost: ~$0.01/episode with Gemini Flash free tier.

**To run on a new show**: `python promo_finder.py /path/to/new/show/episodes/`

## Tools Used

- **Antigravity (Claude Opus 4.6 with Thinking)**: Architecture design, code generation, iterative debugging, solution doc writing.
- **Where AI got it wrong**: Initial scoring was biased toward 55-second windows because raw emotional keyword counts scale with length. Fixed by normalizing to emotion-per-30-seconds density. AI also initially used character count as a *positive* signal for standalone clarity, when past 3–4 characters it should be *negative*.

## Prototype

- **GitHub repo** with clear run steps
- **Streamlit app**: `streamlit run app.py` — interactive browse, filter, export
- **Raw outputs**: `raw_outputs/` folder with JSON, detailed report, and quality analysis
