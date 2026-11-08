"""
app.py — Kuku Promo Intelligence Studio
Autonomous Screenplay Mining for Microdrama Ads (Instagram Reels, TikTok & YouTube Shorts)

Built for Problem 1: Find the Promos (Ads).
"""

import streamlit as st
import os
import json
import tempfile
from pathlib import Path
from typing import Optional

from screenplay_parser import load_all_episodes, format_timestamp
from promo_finder import run_promo_finder, PromoCandidate

# ── Page Configuration ───────────────────────────────────────────────────

st.set_page_config(
    page_title="Kuku Promo Intelligence Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Modern Human Frontend Styling (Linear / Vercel Aesthetic) ────────────

st.markdown("""
<style>
    /* Global Resets & Typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #e2e8f0;
    }

    /* Clean background container */
    .stApp {
        background-color: #0b0f19;
    }

    /* Top Brand Navigation */
    .nav-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 0 24px 0;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 24px;
    }
    .brand-title {
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .brand-badge {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        background: rgba(99, 102, 241, 0.15);
        color: #818cf8;
        border: 1px solid rgba(99, 102, 241, 0.3);
        padding: 3px 8px;
        border-radius: 4px;
    }
    .brand-subtext {
        font-size: 13px;
        color: #94a3b8;
        margin-top: 4px;
    }

    /* KPI Cards */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 28px;
    }
    .kpi-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }
    .kpi-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 24px;
        font-weight: 700;
        color: #f8fafc;
        letter-spacing: -0.02em;
    }
    .kpi-hint {
        font-size: 12px;
        color: #94a3b8;
        margin-top: 4px;
    }

    /* Promo Cards */
    .promo-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
        transition: border-color 0.15s ease;
    }
    .promo-card:hover {
        border-color: #374151;
    }
    .card-top-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 14px;
    }
    .rank-pill {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        font-weight: 600;
        background: #1f2937;
        color: #e2e8f0;
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid #374151;
    }
    .type-pill {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.25);
        padding: 3px 8px;
        border-radius: 4px;
    }
    .score-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 14px;
        font-weight: 700;
        color: #f43f5e;
        background: rgba(244, 63, 94, 0.1);
        border: 1px solid rgba(244, 63, 94, 0.25);
        padding: 4px 10px;
        border-radius: 4px;
    }

    /* Narrative Timeline Beats (Connect-the-Dots) */
    .timeline-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        background: #0d121f;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 14px;
        margin: 14px 0;
    }
    .timeline-beat {
        border-left: 2px solid #6366f1;
        padding-left: 10px;
    }
    .beat-num {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #818cf8;
    }
    .beat-title {
        font-size: 13px;
        font-weight: 600;
        color: #f1f5f9;
        margin-top: 2px;
    }
    .beat-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #64748b;
        margin-top: 2px;
    }

    /* Call to Action Banner */
    .cta-banner {
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.12) 0%, rgba(245, 158, 11, 0.08) 100%);
        border: 1px dashed rgba(239, 68, 68, 0.4);
        border-radius: 6px;
        padding: 10px 14px;
        margin: 12px 0;
        font-size: 13px;
        color: #fca5a5;
    }

    /* Storyboard Card */
    .storyboard-card {
        background: #090d16;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 10px;
        font-size: 12px;
    }
    .shot-header {
        display: flex;
        justify-content: space-between;
        color: #94a3b8;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        margin-bottom: 6px;
    }

    /* Quality Warning Box */
    .qa-box {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.25);
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 12px;
        color: #fcd34d;
        margin-top: 8px;
    }

    /* Subdued Code Blocks */
    code {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        background-color: #1e293b !important;
        color: #38bdf8 !important;
        padding: 2px 5px;
        border-radius: 3px;
    }

    /* Streamlit overrides for clean UI */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        border-bottom: 1px solid #1e293b;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0 0;
        color: #94a3b8;
        font-size: 13px;
        font-weight: 500;
        padding: 0 16px;
    }
    .stTabs [aria-selected="true"] {
        color: #f8fafc !important;
        border-bottom: 2px solid #6366f1 !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Data Loading & State Management ──────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_default_data():
    """Load precomputed 50-episode ranked results and parsed episodes instantly."""
    ranked_json_path = Path("raw_outputs/promos_ranked.json")
    
    episodes = []
    if os.path.isfile("merged.txt"):
        episodes = load_all_episodes("merged.txt")
    elif os.path.isdir("input_episodes"):
        episodes = load_all_episodes("input_episodes")
        
    promos_data = []
    if ranked_json_path.exists():
        with open(ranked_json_path) as f:
            data = json.load(f)
            promos_data = data.get("promos", [])

    return episodes, promos_data

# Initialize session state
default_episodes, default_promos_json = load_default_data()

if "episodes" not in st.session_state:
    st.session_state["episodes"] = default_episodes

if "promos_data" not in st.session_state:
    st.session_state["promos_data"] = default_promos_json


# ── Sidebar: Input & Pipeline Controls ───────────────────────────────────

with st.sidebar:
    st.markdown("### Studio Controls")
    
    input_mode = st.radio(
        "Source Material",
        ["Merged File (merged.txt - 50 eps)", "Input Pack (input_episodes/)", "Upload Screenplay File (.txt)"],
        index=0,
        help="Reads screenplays with scene, action, dialogue, and timestamp metadata."
    )

    uploaded_files = None
    if input_mode == "Upload Screenplay File (.txt)":
        uploaded_files = st.file_uploader(
            "Upload Screenplays or Merged .txt",
            type=["txt"],
            accept_multiple_files=True
        )

    st.markdown("---")
    st.markdown("### Model & Scoring Parameters")
    
    top_n_slider = st.slider("Candidate Output Count", min_value=5, max_value=30, value=20, step=1)
    
    use_gemini = st.checkbox("Enable Gemini 2.0 Free-Tier Polish", value=False)
    gemini_key = ""
    if use_gemini:
        gemini_key = st.text_input("Gemini API Key", type="password", help="ai.google.dev API key")

    st.markdown("---")
    rerun_button = st.button("Re-Run Extraction Pipeline", type="primary", use_container_width=True)

    if rerun_button:
        with st.spinner("Analyzing dramatic density and timestamp boundaries across episodes..."):
            if input_mode == "Merged File (merged.txt - 50 eps)":
                target_source = "merged.txt"
            elif input_mode == "Input Pack (input_episodes/)":
                target_source = "input_episodes"
            else:
                target_source = "merged.txt"
                if uploaded_files:
                    temp_dir = tempfile.mkdtemp()
                    for uf in uploaded_files:
                        temp_path = os.path.join(temp_dir, uf.name)
                        with open(temp_path, "wb") as f:
                            f.write(uf.read())
                    target_source = temp_path if len(uploaded_files) == 1 else temp_dir

            ranked_objs, parsed_eps = run_promo_finder(
                target_source,
                api_key=gemini_key if use_gemini else None,
                top_n=top_n_slider
            )
            st.session_state["episodes"] = parsed_eps
            st.session_state["promos_data"] = [p.to_dict() for p in ranked_objs]
            st.success(f"Discovered {len(ranked_objs)} promos from {len(parsed_eps)} episodes.")
            st.rerun()

    st.markdown("---")
    st.markdown("### Export Artifacts")
    if st.session_state.get("promos_data"):
        export_payload = json.dumps({
            "show": "I Married a Broken Soldier. He was a Duke",
            "total_promos": len(st.session_state["promos_data"]),
            "promos": st.session_state["promos_data"]
        }, indent=2)
        st.download_button(
            "Download Raw JSON",
            export_payload,
            "promos_ranked.json",
            "application/json",
            use_container_width=True
        )


# ── Main Stage Header ────────────────────────────────────────────────────

st.markdown("""
<div class="nav-header">
    <div>
        <div class="brand-title">
            KUKU · PROMO INTELLIGENCE STUDIO
            <span class="brand-badge">Production Engine</span>
        </div>
        <div class="brand-subtext">
            Autonomous Screenplay Mining for Microdrama Paid Ads (Meta Reels, TikTok & YouTube Shorts)
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── KPI Stat Strip ───────────────────────────────────────────────────────

promos_list = st.session_state.get("promos_data", [])
episodes_list = st.session_state.get("episodes", [])
ep_map = {ep.episode_number: ep for ep in episodes_list}

total_promos_count = len(promos_list)
episodes_covered = len(set(seg["episode"] for p in promos_list for seg in p.get("segments", [])))
avg_duration = sum(p.get("total_duration_seconds", 0) for p in promos_list) / max(total_promos_count, 1)
connect_count = sum(1 for p in promos_list if "Connect the Dots" in p.get("promo_type", ""))

st.markdown(f"""
<div class="kpi-container">
    <div class="kpi-card">
        <div class="kpi-label">Ranked Promos</div>
        <div class="kpi-value">{total_promos_count}</div>
        <div class="kpi-hint">Top acquisition candidates</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Episodes Analyzed</div>
        <div class="kpi-value">{len(episodes_list)}</div>
        <div class="kpi-hint">Across 50 screenplays</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Connect-The-Dots Ads</div>
        <div class="kpi-value">{connect_count}</div>
        <div class="kpi-hint">High-converting 3-beat arcs</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Average Runtime</div>
        <div class="kpi-value">{avg_duration:.0f}s</div>
        <div class="kpi-hint">Optimal 20–60s ad spec</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Tab Navigation ───────────────────────────────────────────────────────

tab_connect, tab_ranked, tab_storyboard, tab_quality, tab_scripts = st.tabs([
    "Connect-the-Dots Ads",
    "Ranked Promos Library",
    "AI Video Storyboard & Prompts",
    "Quality & Failure Audit",
    "Screenplay Browser"
])


# ══════════════════════════════════════════════════════════════════════════
# TAB 1: CONNECT-THE-DOTS ADS (Microdrama Acquisition Formula)
# ══════════════════════════════════════════════════════════════════════════

with tab_connect:
    st.markdown("""
    ### Microdrama User Acquisition Formula
    Industry benchmark data from apps like **ReelShort** and **DramaBox** demonstrates that single-scene clips often suffer from context drop-off.
    The highest-converting ad format uses a **3-Beat Narrative Arc**:
    1. **Future Climax Teaser (0–14s):** High-stakes visceral shock (cathedral explosion, dungeon torture, false poisoning accusation).
    2. **Connect-the-Dots Origin (14–28s):** Cut back to Episode 1/2 public altar betrayal in her mother's gown to establish emotional sympathy.
    3. **Turning Point & Paywall Cliffhanger (28–50s):** The mysterious broken soldier intervenes and proposes $\\to$ viewer must download the app and spend coins to reveal his ducal identity.
    """)

    connect_promos = [p for p in promos_list if "Connect the Dots" in p.get("promo_type", "")]

    if not connect_promos:
        st.info("No Connect-the-Dots promos discovered in this dataset run.")
    else:
        for idx, promo in enumerate(connect_promos, 1):
            segments = promo.get("segments", [])
            seg_text = " → ".join(f"Ep {s['episode']} ({s['start']}–{s['end']})" for s in segments)
            
            with st.container():
                st.markdown(f"""
                <div class="promo-card">
                    <div class="card-top-row">
                        <div>
                            <span class="rank-pill">FLAGSHIP AD #{idx}</span>
                            <span class="type-pill" style="margin-left: 8px;">{promo.get('marketing_hook_angle', 'Flash-Forward Arc')}</span>
                            <div style="font-size: 15px; font-weight: 600; color: #f8fafc; margin-top: 6px;">
                                {seg_text} · <span style="color: #94a3b8; font-weight: 400;">{promo.get('total_duration_seconds', 0):.0f}s Total Runtime</span>
                            </div>
                        </div>
                        <div class="score-badge">
                            SCORE {promo.get('scores', {}).get('overall', 0):.1f}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # 3-Beat Timeline Visualization
                if len(segments) >= 3:
                    s1, s2, s3 = segments[0], segments[1], segments[2]
                    st.markdown(f"""
                    <div class="timeline-grid">
                        <div class="timeline-beat">
                            <div class="beat-num">Beat 1 · 00:00–00:14</div>
                            <div class="beat-title">Upcoming Thriller Hook</div>
                            <div class="beat-meta">Episode {s1['episode']} [{s1['start']} → {s1['end']}]</div>
                            <div style="margin-top: 6px; font-size: 12px; color: #cbd5e1;">Visceral high-stakes spectacle grabs cold scrollers before 3-second drop-off.</div>
                        </div>
                        <div class="timeline-beat" style="border-left-color: #38bdf8;">
                            <div class="beat-num" style="color: #38bdf8;">Beat 2 · 00:14–00:28</div>
                            <div class="beat-title">Connect the Dots (Origin)</div>
                            <div class="beat-meta">Episode {s2['episode']} [{s2['start']} → {s2['end']}]</div>
                            <div style="margin-top: 6px; font-size: 12px; color: #cbd5e1;">Cut back to sister stealing her fiancé at the altar. Instant audience empathy.</div>
                        </div>
                        <div class="timeline-beat" style="border-left-color: #34d399;">
                            <div class="beat-num" style="color: #34d399;">Beat 3 · 00:28–00:49</div>
                            <div class="beat-title">Turning Point & Paywall Cut</div>
                            <div class="beat-meta">Episode {s3['episode']} [{s3['start']} → {s3['end']}]</div>
                            <div style="margin-top: 6px; font-size: 12px; color: #cbd5e1;">Scarred soldier offers his hand. Hard cut leaves identity unrevealed.</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Call to Action Banner
                cta_copy = promo.get("call_to_action", "Download Kuku to unlock full episodes!")
                st.markdown(f"""
                <div class="cta-banner">
                    <strong>IN-APP MONETIZATION CTA:</strong> {cta_copy}
                </div>
                """, unsafe_allow_html=True)

                col_h, col_c = st.columns(2)
                with col_h:
                    st.markdown(f"**Hook (First 3s):** {promo.get('hook', 'N/A')}")
                with col_c:
                    st.markdown(f"**Cliffhanger Cut:** {promo.get('cliffhanger', 'N/A')}")

                st.markdown(f"**Why This Converts:** {promo.get('why_it_works', 'N/A')}")

                # Storyboard Expander
                storyboard_beats = promo.get("storyboard_beats", [])
                if storyboard_beats:
                    with st.expander(f"Inspect Visual Storyboard & AI Video Prompts ({len(storyboard_beats)} Shot Cards)"):
                        for beat in storyboard_beats:
                            st.markdown(f"""
                            <div class="storyboard-card">
                                <div class="shot-header">
                                    <span>SHOT #{beat.get('shot_index')} · EPISODE {beat.get('episode')} [{beat.get('time_range')}]</span>
                                    <span>{beat.get('camera_framing')}</span>
                                </div>
                                <div style="color: #e2e8f0; font-weight: 500;">{beat.get('character')}: {beat.get('dialogue_subtitle')}</div>
                                <div style="color: #94a3b8; margin-top: 4px;">Sound Cue: {beat.get('audio_cue')}</div>
                                <div style="margin-top: 6px;">
                                    <span style="color: #818cf8; font-weight: 600;">Runway/Sora Video Prompt:</span><br>
                                    <code>{beat.get('ai_video_prompt')}</code>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# TAB 2: RANKED PROMOS LIBRARY (Single-Episode Moments & Climaxes)
# ══════════════════════════════════════════════════════════════════════════

with tab_ranked:
    st.markdown("### Ranked Promo Library Across All 50 Episodes")
    
    # Filter controls
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        selected_ep = st.selectbox(
            "Filter by Episode",
            ["All Episodes"] + sorted(list(set(str(s["episode"]) for p in promos_list for s in p.get("segments", []))), key=lambda x: int(x))
        )
    with fc2:
        sort_mode = st.selectbox(
            "Sort Order",
            ["Overall Score", "Hook Score", "Cliffhanger Score", "Duration (Longest)", "Duration (Shortest)"]
        )
    with fc3:
        min_score_filter = st.slider("Minimum Quality Score", 0.0, 70.0, 0.0, step=5.0)

    # Filter data
    filtered_promos = promos_list
    if selected_ep != "All Episodes":
        filtered_promos = [p for p in filtered_promos if any(str(s["episode"]) == selected_ep for s in p.get("segments", []))]
    filtered_promos = [p for p in filtered_promos if p.get("scores", {}).get("overall", 0) >= min_score_filter]

    # Sort
    if sort_mode == "Hook Score":
        filtered_promos.sort(key=lambda p: p.get("scores", {}).get("hook", 0), reverse=True)
    elif sort_mode == "Cliffhanger Score":
        filtered_promos.sort(key=lambda p: p.get("scores", {}).get("cliffhanger", 0), reverse=True)
    elif sort_mode == "Duration (Longest)":
        filtered_promos.sort(key=lambda p: p.get("total_duration_seconds", 0), reverse=True)
    elif sort_mode == "Duration (Shortest)":
        filtered_promos.sort(key=lambda p: p.get("total_duration_seconds", 0))
    else:
        filtered_promos.sort(key=lambda p: p.get("scores", {}).get("overall", 0), reverse=True)

    st.markdown(f"Displaying **{len(filtered_promos)}** candidate clips matching criteria:")

    for idx, promo in enumerate(filtered_promos, 1):
        segments = promo.get("segments", [])
        seg_desc = ", ".join(f"Episode {s['episode']}: {s['start']} → {s['end']} ({s['duration_seconds']:.0f}s)" for s in segments)
        scores = promo.get("scores", {})

        with st.container():
            st.markdown(f"""
            <div class="promo-card">
                <div class="card-top-row">
                    <div>
                        <span class="rank-pill">RANK #{idx}</span>
                        <span class="type-pill" style="margin-left: 8px;">{promo.get('promo_type', 'Single-Scene Climax')}</span>
                        <div style="font-size: 15px; font-weight: 600; color: #f8fafc; margin-top: 6px;">
                            {seg_desc}
                        </div>
                    </div>
                    <div class="score-badge">
                        SCORE {scores.get('overall', 0):.1f}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Hook (0–3s):** {promo.get('hook', 'N/A')}")
            with col2:
                st.markdown(f"**Cliffhanger Cut:** {promo.get('cliffhanger', 'N/A')}")

            st.markdown(f"**Why It Works:** {promo.get('why_it_works', 'N/A')}")

            # Score metric breakdown
            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.caption(f"Dramatic: **{scores.get('dramatic', 0):.1f}**")
            sm2.caption(f"Hook: **{scores.get('hook', 0):.1f}**")
            sm3.caption(f"Cliffhanger: **{scores.get('cliffhanger', 0):.1f}**")
            sm4.caption(f"Standalone: **{scores.get('standalone', 0):.1f}**")

            # Quality notes
            q_issues = promo.get("quality_issues", [])
            if q_issues:
                st.markdown(f"""
                <div class="qa-box">
                    <strong>Editorial Note:</strong> {"; ".join(q_issues)}
                </div>
                """, unsafe_allow_html=True)

            # Dialogue Transcript Preview
            with st.expander("Read Exact Screenplay Lines for Editors"):
                for s in segments:
                    ep_obj = ep_map.get(s["episode"])
                    if ep_obj:
                        st.markdown(f"**Episode {s['episode']} [{s['start']} → {s['end']}]**")
                        for sc in ep_obj.scenes:
                            for d in sc.dialogue:
                                if d.start_seconds >= s["start_seconds"] and d.end_seconds <= s["end_seconds"]:
                                    st.markdown(f"- **{d.character}** *({d.emotion})*: \"{d.text}\" `[{d.start_ts}]`")
                            for a in sc.actions:
                                if a.type == "ACTION" and a.start_seconds >= s["start_seconds"] and a.end_seconds <= s["end_seconds"]:
                                    st.markdown(f"- *[{a.description}]* `[{a.start_ts}]`")

            st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# TAB 3: AI VIDEO STORYBOARD & SHOT DIRECTOR (No Video $\to$ Visual Pipeline)
# ══════════════════════════════════════════════════════════════════════════

with tab_storyboard:
    st.markdown("""
    ### Screenplay-to-Video Production Bridge
    Because microdramas are filmed in vertical **9:16 aspect ratio** or rendered via generative video pipelines (Runway Gen-3, OpenAI Sora, Kling AI, Luma Dream Machine), 
    raw screenplay text cannot be posted directly.
    
    This director tool bridges that gap: it translates timestamps, camera movement cues, character emotion tags, and sound effects into **second-by-second shot cards** and ready-to-render AI video generation prompts.
    """)

    # Select promo to inspect
    promo_options = [f"Rank #{i+1}: {p.get('marketing_hook_angle') or p.get('promo_type')} ({p.get('total_duration_seconds', 0):.0f}s)" for i, p in enumerate(promos_list[:10])]
    selected_promo_idx = st.selectbox("Select Promo to Direct & Storyboard", range(len(promo_options)), format_func=lambda i: promo_options[i])

    active_promo = promos_list[selected_promo_idx]
    shots = active_promo.get("storyboard_beats", [])

    st.markdown(f"""
    <div style="background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">
                ACTIVE PROMO: {active_promo.get('marketing_hook_angle') or active_promo.get('promo_type')}
            </span>
            <span class="type-pill">9:16 VERTICAL FORMAT</span>
        </div>
        <div style="font-size: 13px; color: #94a3b8; margin-top: 6px;">
            Target Ad Duration: <strong>{active_promo.get('total_duration_seconds', 0):.0f} seconds</strong> · Generated Shot Cards: <strong>{len(shots)} cuts</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not shots:
        st.warning("No shot-by-shot beats generated for this candidate.")
    else:
        for shot in shots:
            col_v1, col_v2 = st.columns([1, 2])
            with col_v1:
                st.markdown(f"""
                <div style="background: #090d16; border: 1px solid #334155; border-radius: 8px; padding: 14px; text-align: center; height: 100%;">
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #818cf8; margin-bottom: 8px;">
                        SHOT {shot.get('shot_index')} · {shot.get('time_range')}
                    </div>
                    <div style="font-size: 13px; font-weight: 600; color: #f8fafc;">
                        {shot.get('character')}
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; font-style: italic; margin-top: 2px;">
                        "{shot.get('emotion')}"
                    </div>
                    <div style="border-top: 1px dashed #1e293b; margin: 10px 0; padding-top: 8px; font-size: 12px; color: #38bdf8;">
                        Camera: {shot.get('camera_framing')}
                    </div>
                    <div style="font-size: 11px; color: #64748b;">
                        Audio: {shot.get('audio_cue')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_v2:
                st.markdown(f"**Dialogue Subtitle:** {shot.get('dialogue_subtitle')}")
                st.markdown(f"**Visual Staging:** {shot.get('action_description')}")
                st.markdown("**Runway Gen-3 / Sora AI Video Prompt:**")
                st.code(shot.get("ai_video_prompt"), language="text")

            st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════
# TAB 4: QUALITY AUDIT & FAILURE MODES (Honest Limitations)
# ══════════════════════════════════════════════════════════════════════════

with tab_quality:
    st.markdown("""
    ### Honest Quality Audit: Where Does the Tool Pick Badly?
    As required by the assignment brief, a production-grade system must clearly articulate its edge cases and where human editorial judgment remains essential.
    """)

    qa_col1, qa_col2 = st.columns(2)

    with qa_col1:
        st.markdown("""
        #### 1. Crowd Scene Visual Clutter
        - **Problem:** Scenes in ballroom, grand hall, or church wedding environments feature high dialogue velocity between 5–7 minor lords and ladies.
        - **Why Heuristics Fail:** Raw emotion scoring rewards this high-density back-and-forth, but on a 9:16 mobile phone screen, rapid cutting across 6 characters disorients viewers who cannot tell who the protagonist is.
        - **Our Guardrail:** We implemented a character density penalty: clips with $>4$ speaking characters receive a negative score adjustment, prioritizing high-stakes 2-character intimate confrontations.

        #### 2. Pronoun & Context Ambiguity
        - **Problem:** Dialogue lines like *"He warned you about this!"* or *"Take her away!"* provide strong cliffhanger signals but leave a cold TikTok viewer confused without character names.
        - **Editorial Requirement:** Editors must add on-screen burnt-in character labels (e.g. `LADY JULIANA · THE DISOWNED DAUGHTER`) within the first 1.5 seconds.
        """)

    with qa_col2:
        st.markdown("""
        #### 3. Mid-Monologue Cuts & Syntactic Truncation
        - **Problem:** Fixed sliding windows (e.g. strictly cutting at 30.0s) can chop an actor's speech in half mid-sentence.
        - **Our Guardrail:** The algorithm snaps start and end points strictly to the `end_seconds` of a dialogue beat or action block, ensuring complete sentences.

        #### 4. Multi-Segment Transition Pacing
        - **Problem:** When stitching Episode 41 (Cathedral blast) with Episode 1 (Altar betrayal), the sudden jump in wardrobe (soot-stained chains $\to$ white bridal gown) can confuse viewers.
        - **Editorial Requirement:** A flash-forward title card (e.g. *"72 Hours Earlier"*) or a whoosh/shutter audio transition is required between segments.
        """)

    st.markdown("---")
    st.markdown("#### Quality Tiers Across Ingested Show")
    
    tier_high = sum(1 for p in promos_list if p.get("scores", {}).get("overall", 0) >= 35)
    tier_mid = sum(1 for p in promos_list if 20 <= p.get("scores", {}).get("overall", 0) < 35)
    tier_low = sum(1 for p in promos_list if p.get("scores", {}).get("overall", 0) < 20)

    tc1, tc2, tc3 = st.columns(3)
    tc1.metric("Tier 1: Direct-to-Edit (High Confidence)", tier_high, "Ready for ad rendering")
    tc2.metric("Tier 2: Needs Minor Editorial Polish", tier_mid, "Add title card / sound fx")
    tc3.metric("Tier 3: Weak Context / Filtered Out", tier_low, "Discarded from top rank")


# ══════════════════════════════════════════════════════════════════════════
# TAB 5: SCREENPLAY BROWSER (Episodes 1–50)
# ══════════════════════════════════════════════════════════════════════════

with tab_scripts:
    st.markdown("### Screenplay Browser Across All 50 Episodes")
    
    if not episodes_list:
        st.info("No screenplays loaded in memory.")
    else:
        ep_selector = st.selectbox(
            "Select Episode to Read",
            range(1, len(episodes_list) + 1),
            format_func=lambda num: f"Episode {num}: {ep_map[num].logline[:80]}..." if num in ep_map and ep_map[num].logline else f"Episode {num}"
        )

        chosen_ep = ep_map.get(ep_selector)
        if chosen_ep:
            ep_col1, ep_col2, ep_col3 = st.columns(3)
            ep_col1.metric("Runtime", f"{chosen_ep.total_duration:.1f}s")
            ep_col2.metric("Scenes", len(chosen_ep.scenes))
            ep_col3.metric("Dialogue Lines", len(chosen_ep.all_dialogue))

            st.markdown(f"**Logline:** *{chosen_ep.logline}*")
            st.markdown("---")

            for scene_idx, scene in enumerate(chosen_ep.scenes, 1):
                st.markdown(f"#### Scene {scene_idx}: {scene.heading} `[{scene.start_ts} → {scene.end_ts}]`")
                
                # Interleave actions and dialogue by timestamp
                events = []
                for a in scene.actions:
                    events.append(('action', a.start_seconds, a))
                for d in scene.dialogue:
                    events.append(('dialogue', d.start_seconds, d))
                events.sort(key=lambda x: x[1])

                for ev_type, t, obj in events:
                    if ev_type == 'action':
                        if obj.type == 'CAMERA':
                            st.caption(f"🎥 *Camera:* {obj.description} `[{obj.start_ts}]`")
                        elif obj.type == 'SOUND FX':
                            st.caption(f"🔊 *Sound:* {obj.description} `[{obj.start_ts}]`")
                        else:
                            st.markdown(f"*{obj.description}* `[{obj.start_ts}]`")
                    elif ev_type == 'dialogue':
                        st.markdown(f"**{obj.character}** *({obj.emotion})*: \"{obj.text}\" `[{obj.start_ts}]`")

                st.markdown("")
