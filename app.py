"""
app.py — Streamlit app for the Kuku Promo Finder tool.

Provides:
- Upload screenplay files or use the bundled input pack
- Run the promo finder with or without LLM enhancement
- Browse, filter, and rank discovered promos
- Export results as JSON
"""

import streamlit as st
import os
import json
import tempfile
import shutil
from pathlib import Path

from screenplay_parser import load_all_episodes, format_timestamp
from promo_finder import run_promo_finder, save_results, PromoCandidate

# ── Page config ──────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Kuku Promo Finder",
    page_icon="🎬",
    layout="wide",
)

# ── Custom CSS ───────────────────────────────────────────────────────────

st.markdown("""
<style>
    .promo-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #e94560;
        color: #eee;
    }
    .promo-rank {
        font-size: 2em;
        font-weight: bold;
        color: #e94560;
    }
    .promo-score {
        font-size: 1.1em;
        color: #0f3460;
        background: #e94560;
        padding: 2px 10px;
        border-radius: 20px;
        display: inline-block;
    }
    .metric-box {
        background: #f0f2f6;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .quality-warning {
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 6px;
        padding: 8px 12px;
        margin: 4px 0;
        font-size: 0.85em;
    }
    .quality-good {
        background: #d4edda;
        border: 1px solid #28a745;
        border-radius: 6px;
        padding: 8px 12px;
        margin: 4px 0;
        font-size: 0.85em;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────

st.title("🎬 Kuku Promo Finder")
st.markdown("""
**Find the best promo-worthy moments from microdrama screenplays.**
Automatically identifies clips with strong hooks, cliffhangers, and standalone appeal for Instagram, TikTok, and YouTube.
""")

# ── Sidebar: Configuration ──────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuration")

    # Input source
    st.subheader("📂 Input")
    input_source = st.radio(
        "Screenplay source",
        ["Bundled input pack", "Upload files"],
        index=0,
    )

    if input_source == "Upload files":
        uploaded_files = st.file_uploader(
            "Upload screenplay .txt files",
            type=["txt"],
            accept_multiple_files=True,
        )
    else:
        uploaded_files = None

    # LLM settings
    st.subheader("🤖 LLM Enhancement")
    use_llm = st.checkbox("Enable LLM ranking (Gemini)", value=False)
    api_key = ""
    model_name = "gemini-2.0-flash"
    if use_llm:
        api_key = st.text_input("Gemini API Key", type="password",
                                help="Free tier key from ai.google.dev")
        model_name = st.selectbox(
            "Model",
            ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
            index=0,
            help="gemini-2.0-flash is free and fast"
        )

    # Promo settings
    st.subheader("🎯 Promo Settings")
    top_n = st.slider("Number of top promos to show", 5, 30, 15)

    # Run button
    st.divider()
    run_button = st.button("🚀 Find Promos", type="primary", use_container_width=True)


# ── Main logic ───────────────────────────────────────────────────────────

def get_input_dir(uploaded_files=None):
    """Get the input directory path."""
    if uploaded_files:
        tmp_dir = tempfile.mkdtemp()
        for uf in uploaded_files:
            with open(os.path.join(tmp_dir, uf.name), "wb") as f:
                f.write(uf.read())
        return tmp_dir

    # Check for bundled input
    bundled_paths = [
        "input_episodes",
        os.path.join(os.path.dirname(__file__), "input_episodes"),
    ]
    for p in bundled_paths:
        if os.path.isdir(p):
            return p

    return None


def display_promo_card(rank: int, promo: PromoCandidate, episodes_map: dict):
    """Display a single promo as a rich card."""
    with st.container():
        # Header row
        col1, col2, col3 = st.columns([1, 6, 2])
        with col1:
            st.markdown(f"### #{rank}")
        with col2:
            eps = ", ".join(f"Ep {e}" for e in promo.episode_numbers)
            st.markdown(f"**{eps}** — {promo.total_duration:.0f}s total")
        with col3:
            st.metric("Score", f"{promo.rank_score:.1f}")

        # Segments
        for seg in promo.segments:
            st.markdown(
                f"📍 **Episode {seg.episode_number}**: "
                f"`{seg.start_ts}` → `{seg.end_ts}` "
                f"({seg.duration_seconds:.0f}s)"
            )

        # Hook, Cliffhanger, Why
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"🪝 **Hook:** {promo.hook_description}")
        with col_b:
            st.markdown(f"⏸️ **Cliffhanger:** {promo.cliffhanger_description}")

        st.markdown(f"💡 **Why it works:** {promo.why_it_works}")

        # Score breakdown
        with st.expander("📊 Score breakdown"):
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Dramatic", f"{promo.dramatic_score:.1f}")
            sc2.metric("Hook", f"{promo.hook_score:.1f}")
            sc3.metric("Cliffhanger", f"{promo.cliffhanger_score:.1f}")
            sc4.metric("Standalone", f"{promo.standalone_score:.1f}")

            if promo.llm_rank is not None:
                st.info(f"🤖 LLM Rank: #{promo.llm_rank}")
            if promo.llm_reasoning:
                st.markdown(f"*{promo.llm_reasoning}*")

        # Quality issues
        if promo.quality_issues:
            with st.expander("⚠️ Quality issues"):
                for issue in promo.quality_issues:
                    st.warning(issue)

        # Show the actual dialogue in this segment
        with st.expander("📜 Dialogue preview"):
            for seg in promo.segments:
                ep = episodes_map.get(seg.episode_number)
                if ep:
                    st.markdown(f"**Episode {seg.episode_number}** [{seg.start_ts} → {seg.end_ts}]")
                    for scene in ep.scenes:
                        for d in scene.dialogue:
                            if d.start_seconds >= seg.start_seconds and d.end_seconds <= seg.end_seconds:
                                st.markdown(
                                    f"**{d.character}** *({d.emotion})*: \"{d.text}\"  "
                                    f"<small>[{d.start_ts}]</small>",
                                    unsafe_allow_html=True,
                                )
                        for a in scene.actions:
                            if (a.type == "ACTION" and
                                a.start_seconds >= seg.start_seconds and
                                a.end_seconds <= seg.end_seconds):
                                st.markdown(
                                    f"*[{a.description}]*  "
                                    f"<small>[{a.start_ts}]</small>",
                                    unsafe_allow_html=True,
                                )

        st.divider()


# ── Run pipeline ─────────────────────────────────────────────────────────

if run_button:
    input_dir = get_input_dir(uploaded_files)

    if not input_dir:
        st.error("❌ No input files found. Upload screenplays or place them in `input_episodes/`.")
        st.stop()

    with st.spinner("🔍 Analyzing screenplays..."):
        promos, episodes = run_promo_finder(
            input_dir,
            api_key=api_key if use_llm else None,
            model_name=model_name,
            top_n=top_n,
        )

    st.session_state["promos"] = promos
    st.session_state["episodes"] = episodes
    st.success(f"✅ Found {len(promos)} top promos from {len(episodes)} episodes!")


# ── Display results ──────────────────────────────────────────────────────

if "promos" in st.session_state and "episodes" in st.session_state:
    promos = st.session_state["promos"]
    episodes = st.session_state["episodes"]
    ep_map = {ep.episode_number: ep for ep in episodes}

    # Summary metrics
    st.header("📊 Overview")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Promos", len(promos))
    m2.metric("Episodes Covered", len(set(e for p in promos for e in p.episode_numbers)))
    m3.metric("Avg Duration", f"{sum(p.total_duration for p in promos)/max(len(promos),1):.0f}s")
    m4.metric("Top Score", f"{promos[0].rank_score:.1f}" if promos else "N/A")

    # Filters
    st.header("🔍 Filter & Browse")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        ep_filter = st.multiselect(
            "Filter by episode",
            sorted(set(e for p in promos for e in p.episode_numbers)),
            default=[],
        )
    with col_f2:
        min_score = st.slider("Minimum score", 0.0, promos[0].rank_score if promos else 50.0,
                              0.0, step=1.0)
    with col_f3:
        sort_by = st.selectbox("Sort by", ["Overall Score", "Hook Score",
                                           "Cliffhanger Score", "Duration"])

    # Apply filters
    filtered = promos
    if ep_filter:
        filtered = [p for p in filtered
                    if any(e in ep_filter for e in p.episode_numbers)]
    filtered = [p for p in filtered if p.rank_score >= min_score]

    # Sort
    if sort_by == "Hook Score":
        filtered.sort(key=lambda p: p.hook_score, reverse=True)
    elif sort_by == "Cliffhanger Score":
        filtered.sort(key=lambda p: p.cliffhanger_score, reverse=True)
    elif sort_by == "Duration":
        filtered.sort(key=lambda p: p.total_duration, reverse=True)
    else:
        filtered.sort(key=lambda p: p.rank_score, reverse=True)

    # Display
    st.header(f"🏆 Top {len(filtered)} Promos — Ranked")
    for i, promo in enumerate(filtered, 1):
        display_promo_card(i, promo, ep_map)

    # Export
    st.header("📥 Export")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        results = {
            "show": "I Married a Broken Soldier. He was a Duke",
            "total_promos": len(filtered),
            "promos": [p.to_dict() for p in filtered],
        }
        st.download_button(
            "⬇️ Download JSON",
            json.dumps(results, indent=2),
            "promos_ranked.json",
            "application/json",
        )
    with col_e2:
        # Markdown report
        md_lines = ["# Promo Report\n"]
        md_lines.append(f"**Show:** I Married a Broken Soldier. He was a Duke\n")
        md_lines.append(f"**Total Promos:** {len(filtered)}\n\n")
        for i, p in enumerate(filtered, 1):
            md_lines.append(f"## Rank #{i}\n")
            for seg in p.segments:
                md_lines.append(f"- Episode {seg.episode_number}: {seg.start_ts} → {seg.end_ts}\n")
            md_lines.append(f"- **Hook:** {p.hook_description}\n")
            md_lines.append(f"- **Cliffhanger:** {p.cliffhanger_description}\n")
            md_lines.append(f"- **Why:** {p.why_it_works}\n")
            md_lines.append(f"- **Score:** {p.rank_score:.1f}\n\n")
        st.download_button(
            "⬇️ Download Markdown Report",
            "".join(md_lines),
            "promos_report.md",
            "text/markdown",
        )

else:
    # No results yet — show instructions
    st.info("👈 Click **Find Promos** in the sidebar to analyze the screenplays.")

    # Show a preview of what's available
    input_dir = get_input_dir()
    if input_dir:
        episodes = load_all_episodes(input_dir)
        st.header("📺 Show Overview")
        st.markdown(f"**Show:** I Married a Broken Soldier. He was a Duke")
        st.markdown(f"**Episodes available:** {len(episodes)}")

        with st.expander("Episode Guide", expanded=True):
            for ep in episodes:
                st.markdown(
                    f"**Ep {ep.episode_number}** — {ep.logline[:100]}..."
                    if len(ep.logline) > 100 else
                    f"**Ep {ep.episode_number}** — {ep.logline}"
                )
