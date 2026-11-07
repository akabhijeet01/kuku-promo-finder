# Kuku Promo Finder 🎬

**An AI tool that reads microdrama screenplays and finds the best promo clips.**

Built for Kuku's AI Generalist Assignment — Problem 1: Find the Promos.

## What It Does

Reads all 50 episodes of *"I Married a Broken Soldier. He was a Duke"* and automatically identifies the best 20–60 second clips to post as promos on Instagram, TikTok, and YouTube.

For each promo, it gives:
- **Episode and timestamps** — exact start and end points
- **Hook** — what makes someone stop scrolling in the first 3 seconds
- **Cliffhanger** — the unresolved moment where it cuts
- **Why it works** — one-line justification
- **Quality issues** — honest assessment of where it picks badly

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the finder (rule-based, no API key needed)
python promo_finder.py input_episodes

# Generate full outputs (JSON + report + quality analysis)
python generate_full_outputs.py input_episodes

# Launch the Streamlit UI
streamlit run app.py
```

## With LLM Enhancement (Optional)

```bash
# Set your free Gemini API key
export GEMINI_API_KEY="your-key-from-ai.google.dev"

# Run with LLM-enhanced ranking
python promo_finder.py input_episodes
```

Or enable it in the Streamlit sidebar.

## How It Works

### 1. Parse (screenplay_parser.py)
Parses the timestamped screenplay format into structured data: episodes → scenes → dialogue lines + action beats, each with precise timestamps.

### 2. Find Candidates (promo_finder.py)
Sliding window (20–55s, 5s step) across every episode, scoring each window on:
- **Emotional intensity** — scored from dialogue emotion tags (e.g., "Furious" = 3, "Hurt" = 1)
- **Hook signals** — keyword detection for physical action, reveals, shocking lines
- **Cliffhanger signals** — unresolved phrases + proximity to scene/episode boundaries
- **Duration sweet spot** — 25–40s gets a bonus (optimal for social media)
- **Natural boundaries** — bonus for starting at episode start or ending at episode end

### 3. Deduplicate & Diversify
Overlapping windows are merged (keeping highest score). Episode diversity is enforced: max 2 promos per episode in the top results.

### 4. Cross-Episode Promos
Automatically finds cliffhanger→payoff pairs across consecutive episodes.

### 5. LLM Enhancement (Optional)
Sends candidates to Google Gemini for semantic evaluation of hook strength, cliffhanger quality, standalone clarity, and re-ranking.

## Swapping the Model

The LLM is a single function call in `promo_finder.py:enhance_with_llm()`. To swap:

```python
# Change model_name parameter:
promos = run_promo_finder(input_dir, api_key="...", model_name="gemini-1.5-pro")

# Or use any OpenAI-compatible API by modifying enhance_with_llm()
```

The rule-based engine works without any LLM — the model only adds re-ranking.

## Project Structure

```
kuku.ai/
├── app.py                    # Streamlit web UI
├── screenplay_parser.py      # Parses screenplay .txt files
├── promo_finder.py           # Core promo finding engine
├── generate_full_outputs.py  # Generates all raw outputs
├── requirements.txt          # Python dependencies
├── input_episodes/           # 50 episode screenplays (input pack)
└── raw_outputs/              # Generated outputs
    ├── promos_ranked.json        # All promos with scores (machine-readable)
    ├── promos_detailed_report.md # Full report with dialogue excerpts
    └── quality_analysis.md       # Honest failure analysis
```

## Scaling to Every Show

| Dimension | Current | At Scale |
|-----------|---------|----------|
| Input | 50 episodes, 1 show | 100s of shows/week |
| Speed | <1 second, all episodes | Parallel batch processing |
| Cost | Free (rule-based) | ~$0.01/episode with Gemini Flash |
| Human review | Read the ranked list | Editor reviews top 5, not all episodes |

The rule-based engine processes all 50 episodes in under 1 second. The LLM pass adds ~10 seconds per batch of 5 promos. At scale, the tool reduces an editor's work from watching every episode to reviewing a ranked shortlist.

## AI Tools Used

- **Antigravity (Claude)** — Architecture design, code generation, iterative debugging
- **One place AI got it wrong:** Initially generated a scoring system that was biased toward 55-second windows (longer = more emotional keywords = higher score). Fixed by normalizing emotional density per 30 seconds instead of using raw totals.
