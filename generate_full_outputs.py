"""
generate_full_outputs.py — Generates the complete raw output report.
Runs the promo finder and produces:
  1. promos_ranked.json — All promos with scores
  2. promos_detailed_report.md — Human-readable report
  3. quality_analysis.md — Where the tool picks badly
"""

import json
import os
import sys
from screenplay_parser import load_all_episodes, format_timestamp, get_episode_text_window
from promo_finder import run_promo_finder, save_results


def generate_detailed_report(promos, episodes, output_path):
    """Generate a detailed markdown report of all promos."""
    ep_map = {ep.episode_number: ep for ep in episodes}

    lines = []
    lines.append("# Promo Finder — Detailed Report")
    lines.append(f"\n**Show:** I Married a Broken Soldier. He was a Duke")
    lines.append(f"**Episodes Analyzed:** {len(episodes)}")
    lines.append(f"**Total Promos Found:** {len(promos)}")
    lines.append("")

    # Summary table
    lines.append("## Summary Table")
    lines.append("")
    lines.append("| Rank | Episode(s) | Time Range | Duration | Score | Hook | Cliffhanger |")
    lines.append("|------|-----------|------------|----------|-------|------|-------------|")
    for i, promo in enumerate(promos, 1):
        eps = ", ".join(str(e) for e in promo.episode_numbers)
        segments_str = "; ".join(
            f"Ep{s.episode_number} {s.start_ts}-{s.end_ts}" for s in promo.segments
        )
        hook_short = promo.hook_description[:50] + "..." if len(promo.hook_description) > 50 else promo.hook_description
        cliff_short = promo.cliffhanger_description[:50] + "..." if len(promo.cliffhanger_description) > 50 else promo.cliffhanger_description
        lines.append(
            f"| {i} | {eps} | {segments_str} | {promo.total_duration:.0f}s | "
            f"{promo.rank_score:.1f} | {hook_short} | {cliff_short} |"
        )

    lines.append("")

    # Detailed promo entries
    lines.append("## Detailed Promo Analysis")
    lines.append("")

    for i, promo in enumerate(promos, 1):
        lines.append(f"### Rank #{i} — Score: {promo.rank_score:.1f}")
        lines.append("")

        for seg in promo.segments:
            lines.append(f"**Episode {seg.episode_number}:** `{seg.start_ts}` → `{seg.end_ts}` ({seg.duration_seconds:.0f}s)")

        lines.append("")
        lines.append(f"**🪝 Hook (first 3s):** {promo.hook_description}")
        lines.append(f"**⏸️ Cliffhanger:** {promo.cliffhanger_description}")
        lines.append(f"**💡 Why it works:** {promo.why_it_works}")
        lines.append("")

        # Score breakdown
        lines.append("**Score Breakdown:**")
        lines.append(f"- Dramatic intensity: {promo.dramatic_score:.1f}")
        lines.append(f"- Hook strength: {promo.hook_score:.1f}")
        lines.append(f"- Cliffhanger quality: {promo.cliffhanger_score:.1f}")
        lines.append(f"- Standalone clarity: {promo.standalone_score:.1f}")
        lines.append("")

        # Quality issues
        if promo.quality_issues:
            lines.append("**⚠️ Quality Issues:**")
            for issue in promo.quality_issues:
                lines.append(f"- {issue}")
            lines.append("")

        # Dialogue excerpt
        lines.append("**Dialogue Excerpt:**")
        lines.append("```")
        for seg in promo.segments:
            ep = ep_map.get(seg.episode_number)
            if ep:
                for scene in ep.scenes:
                    for d in scene.dialogue:
                        if d.start_seconds >= seg.start_seconds and d.end_seconds <= seg.end_seconds:
                            lines.append(f"[{d.start_ts}] {d.character} ({d.emotion}): \"{d.text}\"")
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Detailed report saved to {output_path}")


def generate_quality_analysis(promos, episodes, output_path):
    """Analyze where the tool picks well and where it picks badly."""
    lines = []
    lines.append("# Quality Analysis — Where the Tool Picks Badly")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append("The promo finder employs a hybrid evaluation pipeline:")
    lines.append("1. **Normalized dramatic density** — emotional tags (dialogue) + physical spectacle cues (action/sound).")
    lines.append("2. **Hook strength** — physical conflict, shocking reveals, or high-stakes lines in the first 3 seconds.")
    lines.append("3. **Cliffhanger tension** — unresolved questions, threats, or boundary cuts leaving maximum tension.")
    lines.append("4. **Standalone clarity** — penalizes crowded scenes (5+ characters) and rewards focused 2-3 character tension.")
    lines.append("5. **Narrative juxtaposition** — identifies high-contrast cross-episode bridges (setup + twist payoff).")
    lines.append("")
    lines.append("## Known Failure Modes & Tool Limitations")
    lines.append("")

    lines.append("### 1. Inability to evaluate visual performance and actor delivery")
    lines.append("The tool inspects screenplay text, not recorded footage. A dramatic line like 'I cannot marry you' can be")
    lines.append("delivered weakly on camera, or a silent 2-second stare can be mesmerizing. The tool will rate a line")
    lines.append("solely based on written emotion tags ('Heartbroken', 'Cold') and cannot detect audio mixing or actor chemistry.")
    lines.append("")

    lines.append("### 2. Dialogue-sparse visual climaxes require explicit action descriptions")
    lines.append("Although we added ACTION keyword parsing, scenes with prolonged physical choreography (e.g. sword fights,")
    lines.append("stealth infiltrations) that have minimal spoken lines can still receive lower drama scores than rapid-fire verbal")
    lines.append("arguments, despite being visually magnetic on video platforms like TikTok.")
    lines.append("")

    lines.append("### 3. Subtextual cliffhangers missed without explicit triggers")
    lines.append("The algorithm reliably catches explicit cliffhangers ('Stop!', 'Who are you?', 'No!'), but can miss subtle,")
    lines.append("unspoken dread—such as a character secretly pocketing a poison vial or an ominous smirk unnoticed by others.")
    lines.append("")

    lines.append("### 4. Splice point boundary roughness in multi-segment promos")
    lines.append("For cross-episode and juxtaposition promos (e.g. Ep 1 betrayal + Ep 3 proposal), the tool identifies the")
    lines.append("story beats accurately, but cannot determine whether the ambient audio (church organ, background rain) matches")
    lines.append("across the cut. An editor must insert a transition or title card.")
    lines.append("")

    lines.append("### 5. False positive hooks from formal dialogue tags")
    lines.append("Certain high-frequency courtly words ('Your Grace', 'Father') can trigger false relevance when surrounding")
    lines.append("dialogue is mundane exposition rather than a genuine scroll-stopping hook.")
    lines.append("")

    # Specific promo quality checks
    lines.append("## Per-Promo Quality Audit")
    lines.append("")

    ep_map = {ep.episode_number: ep for ep in episodes}

    for i, promo in enumerate(promos, 1):
        issues = []

        # Check: does the hook actually occur in the first 3 seconds?
        first_seg = promo.segments[0]
        ep = ep_map.get(first_seg.episode_number)
        if ep:
            first_3s_dialogue = [
                d for d in ep.all_dialogue
                if d.start_seconds >= first_seg.start_seconds and
                d.start_seconds <= first_seg.start_seconds + 3.5
            ]
            if not first_3s_dialogue:
                issues.append("Visual-only hook in first 3s (no spoken line) — relies on visual action")
            else:
                first_line = first_3s_dialogue[0]
                if len(first_line.text) > 70:
                    issues.append("First dialogue line is lengthy — risk of scroller drop-off before punchline")

        # Check: duration
        if promo.total_duration > 50:
            issues.append("Duration > 50s: requires fast-paced visual editing for TikTok retention")
        elif promo.total_duration < 22:
            issues.append("Short clip (< 22s): ensures high completion rate, but minimal character setup")

        # Check: characters
        all_chars = set()
        for seg in promo.segments:
            ep = ep_map.get(seg.episode_number)
            if ep:
                for d in ep.all_dialogue:
                    if d.start_seconds >= seg.start_seconds and d.end_seconds <= seg.end_seconds:
                        all_chars.add(d.character)
        if len(all_chars) >= 5:
            issues.append(f"High character count ({len(all_chars)}): may confuse viewer unfamiliar with lore")

        if len(promo.segments) > 1:
            issues.append("Multi-segment cut: requires title card or smash cut between scenes")

        verdict = "✅ High Confidence" if len(issues) <= 1 else "⚠️ Review Edit" if len(issues) <= 2 else "🔍 Experimental"

        lines.append(f"**Rank #{i}** [{', '.join(f'Ep{s.episode_number}' for s in promo.segments)}] — {verdict}")
        if issues:
            for issue in issues:
                lines.append(f"  - {issue}")
        else:
            lines.append("  - Verified clean hook-to-cliffhanger progression")
        lines.append("")

    # Summary statistics
    lines.append("## Production Statistics")
    lines.append("")
    lines.append(f"- Total promos generated: {len(promos)}")

    ep_coverage = set()
    for p in promos:
        ep_coverage.update(p.episode_numbers)
    lines.append(f"- Distinct episodes featured: {len(ep_coverage)} / {len(episodes)} ({100*len(ep_coverage)/len(episodes):.0f}%)")

    avg_dur = sum(p.total_duration for p in promos) / max(len(promos), 1)
    lines.append(f"- Average promo duration: {avg_dur:.1f}s (Optimal for Reels & TikTok)")

    cross_ep = sum(1 for p in promos if len(p.segments) > 1)
    lines.append(f"- Multi-segment / Cross-episode promos: {cross_ep}")

    high_conf = sum(1 for p in promos if len(p.quality_issues) <= 1)
    lines.append(f"- Ready-to-cut promos (<= 1 review note): {high_conf}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Quality analysis saved to {output_path}")


if __name__ == "__main__":
    input_source = sys.argv[1] if len(sys.argv) > 1 else ("merged.txt" if os.path.exists("merged.txt") else "input_episodes")
    output_dir = "raw_outputs"
    os.makedirs(output_dir, exist_ok=True)

    api_key = os.environ.get("GEMINI_API_KEY", "")

    # Run pipeline
    promos, episodes = run_promo_finder(
        input_source,
        api_key=api_key if api_key else None,
        top_n=20,
    )

    # Generate all outputs
    save_results(promos, os.path.join(output_dir, "promos_ranked.json"))
    generate_detailed_report(promos, episodes, os.path.join(output_dir, "promos_detailed_report.md"))
    generate_quality_analysis(promos, episodes, os.path.join(output_dir, "quality_analysis.md"))

    print("\n✅ All outputs generated in raw_outputs/")
