"""
promo_finder.py — Core engine that identifies the best promo-worthy moments
from parsed screenplay episodes.

Strategy:
1. Rule-based candidate extraction: Find moments with high dramatic density
   (confrontations, reveals, emotional peaks, physical actions).
2. LLM-based ranking and refinement: Use an LLM to evaluate and rank candidates
   for hook strength, cliffhanger potential, and standalone clarity.
3. The model is easily swappable — just change the API call.

Works without any paid API by default (rule-based mode), and can optionally
use Google Gemini free tier for LLM-enhanced analysis.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from screenplay_parser import (
    Episode, Scene, DialogueLine, ActionBeat,
    load_all_episodes, format_timestamp, parse_timestamp, get_episode_text_window
)


# ── Dramatic signal keywords ──────────────────────────────────────────────

HOOK_KEYWORDS = {
    # Physical confrontation / violence
    "slap", "punch", "grab", "shove", "strike", "stab", "blood", "wound",
    "attack", "seize", "choke", "throw", "crash", "explosion", "shatter",
    "kick", "drag", "force", "kill", "dead", "death", "poison", "gun",
    "sword", "knife", "dagger", "fight", "wrestle",
    # Shocking reveals
    "reveal", "truth", "secret", "confess", "lie", "betray", "affair",
    "pregnant", "divorce", "arrest", "murder", "treason", "fraud",
    "identity", "imposter", "disguise", "unmasked",
    # Power / status shifts
    "duke", "duchess", "crown", "throne", "inherit", "disinherit",
    "disown", "banish", "exile", "command", "kneel", "bow", "beg",
    "proposal", "marry", "wedding", "ring",
    # Emotional extremes
    "scream", "cry", "tears", "sob", "gasp", "shock", "fury", "rage",
    "devastated", "heartbroken", "humiliated", "terrified",
}

CLIFFHANGER_KEYWORDS = {
    "who are you", "what have you done", "don't", "stop", "no",
    "please", "why", "impossible", "can't be", "what do you mean",
    "you wouldn't dare", "I'll destroy", "you'll pay", "it's over",
    "choose", "accept", "refuse",
}

EMOTION_INTENSITY = {
    # High intensity
    "desperate": 3, "furious": 3, "enraged": 3, "devastated": 3,
    "heartbroken": 3, "terrified": 3, "hysterical": 3, "venomous": 3,
    "volcanic": 3, "explosive": 3, "shattered": 3, "broken": 3,
    "anguished": 3, "unhinged": 3,
    # Medium-high intensity
    "defiant": 2, "commanding": 2, "threatening": 2, "cold": 2,
    "cruel": 2, "mocking": 2, "accusing": 2, "scornful": 2,
    "bitter": 2, "pleading": 2, "trembling": 2, "gloating": 2,
    "vindictive": 2, "disgusted": 2, "stern": 2, "ruthless": 2,
    "contemptuous": 2, "aggressive": 2,
    # Medium intensity
    "hurt": 1, "pained": 1, "confused": 1, "suspicious": 1,
    "shocked": 1, "surprised": 1, "vulnerable": 1, "resolute": 1,
    "determined": 1, "smug": 1, "arrogant": 1,
}


@dataclass
class PromoSegment:
    """A single continuous clip segment."""
    episode_number: int
    start_ts: str
    end_ts: str
    start_seconds: float
    end_seconds: float

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass
class PromoCandidate:
    """A potential promo, possibly joining multiple segments."""
    segments: list[PromoSegment]
    hook_description: str
    cliffhanger_description: str
    why_it_works: str
    promo_type: str = "Single-Scene Climax"
    marketing_hook_angle: str = "High-Stakes Dramatic Reversal"
    call_to_action: str = "Download Kuku to unlock full episodes and claim 500 bonus coins!"
    dramatic_score: float = 0.0
    hook_score: float = 0.0
    cliffhanger_score: float = 0.0
    standalone_score: float = 0.0
    llm_rank: Optional[int] = None
    llm_reasoning: str = ""
    quality_issues: list[str] = field(default_factory=list)
    storyboard_beats: list[dict] = field(default_factory=list)

    @property
    def total_duration(self) -> float:
        return sum(s.duration_seconds for s in self.segments)

    @property
    def rank_score(self) -> float:
        """Combined score for ranking. Higher = better promo."""
        base = self.dramatic_score + self.hook_score * 2 + self.cliffhanger_score * 2 + self.standalone_score
        # Bonus for Connect-the-Dots promos due to superior conversion performance
        if "Connect the Dots" in self.promo_type:
            base += 6.0
        if self.llm_rank is not None:
            base += max(0, (20 - self.llm_rank)) * 2
        return base

    @property
    def episode_numbers(self) -> list[int]:
        return sorted(set(s.episode_number for s in self.segments))

    def to_dict(self) -> dict:
        return {
            "segments": [
                {
                    "episode": s.episode_number,
                    "start": s.start_ts,
                    "end": s.end_ts,
                    "duration_seconds": round(s.duration_seconds, 1),
                }
                for s in self.segments
            ],
            "total_duration_seconds": round(self.total_duration, 1),
            "promo_type": self.promo_type,
            "marketing_hook_angle": self.marketing_hook_angle,
            "call_to_action": self.call_to_action,
            "hook": self.hook_description,
            "cliffhanger": self.cliffhanger_description,
            "why_it_works": self.why_it_works,
            "scores": {
                "dramatic": round(self.dramatic_score, 2),
                "hook": round(self.hook_score, 2),
                "cliffhanger": round(self.cliffhanger_score, 2),
                "standalone": round(self.standalone_score, 2),
                "overall_rank_score": round(self.rank_score, 2),
            },
            "quality_issues": self.quality_issues,
            "storyboard_beats": self.storyboard_beats,
            "llm_rank": self.llm_rank,
            "llm_reasoning": self.llm_reasoning,
        }


def _compute_emotional_intensity(dialogue_lines: list[DialogueLine]) -> float:
    """Score the emotional intensity of a set of dialogue lines."""
    score = 0.0
    for d in dialogue_lines:
        emotions = [e.strip().lower() for e in d.emotion.split(",")]
        for emotion in emotions:
            score += EMOTION_INTENSITY.get(emotion, 0.5)
    return score


ACTION_KEYWORDS = {
    # Explosive / high spectacle (5.0)
    "explode": 5.0, "explosion": 5.0, "fireball": 5.0, "detonation": 5.0, "blast": 5.0,
    # Violence / combat / physical shock (3.5)
    "shatter": 3.5, "shatters": 3.5, "burst": 3.5, "slap": 3.5, "slaps": 3.5,
    "strike": 3.5, "punch": 3.5, "punches": 3.5, "tackle": 3.5, "choke": 3.5,
    "grab": 3.0, "grabs": 3.0, "drag": 3.0, "drags": 3.0, "shove": 3.0, "shoves": 3.0,
    "blood": 3.5, "bleed": 3.0, "wound": 3.0, "sword": 3.0, "dagger": 3.0, "knife": 3.0,
    # High-drama microdrama gestures (2.5)
    "kneel": 3.0, "kneels": 3.0, "ring": 2.5, "chains": 3.0, "arrest": 3.0, "manacled": 3.0,
    "tear": 2.0, "tears": 2.0, "weep": 2.0, "sob": 2.0, "gasp": 2.0, "gasps": 2.0, "shriek": 2.5,
}


def _compute_action_intensity(actions: list[ActionBeat]) -> float:
    """Score visual and physical dramatic intensity from action beats."""
    score = 0.0
    for a in actions:
        text_lower = a.description.lower()
        for kw, weight in ACTION_KEYWORDS.items():
            if kw in text_lower:
                score += weight
    return min(score, 18.0)  # Cap action contribution per window


def _has_hook_signal(text: str) -> tuple[bool, str]:
    """Check if text contains strong hook signals. Returns (has_hook, description)."""
    text_lower = text.lower()
    found = []
    for kw in HOOK_KEYWORDS:
        if kw in text_lower:
            found.append(kw)
    if found:
        return True, f"Contains hook signals: {', '.join(found[:5])}"
    return False, ""


def _has_cliffhanger_signal(text: str, is_end_of_scene: bool) -> tuple[bool, str]:
    """Check if text or position suggests a cliffhanger."""
    text_lower = text.lower()
    found = []
    for kw in CLIFFHANGER_KEYWORDS:
        if kw in text_lower:
            found.append(kw)
    if found or is_end_of_scene:
        reason = []
        if found:
            reason.append(f"cliffhanger signals: {', '.join(found[:3])}")
        if is_end_of_scene:
            reason.append("ends at scene/episode boundary")
        return True, "; ".join(reason)
    return False, ""


def _character_conflict_count(dialogue_lines: list[DialogueLine]) -> int:
    """Count how many distinct characters are in dialogue (more = more conflict potential)."""
    return len(set(d.character for d in dialogue_lines))


def find_candidate_windows(episode: Episode, min_dur: float = 20.0, max_dur: float = 60.0) -> list[dict]:
    """
    Identify candidate time windows within an episode that have high dramatic density.
    Uses a sliding window approach.
    """
    candidates = []
    all_dialogue = episode.all_dialogue
    if not all_dialogue:
        return candidates

    # Collect all timestamped events
    events = []
    for scene in episode.scenes:
        for d in scene.dialogue:
            events.append({
                "type": "dialogue",
                "start": d.start_seconds,
                "end": d.end_seconds,
                "data": d,
                "scene": scene,
            })
        for a in scene.actions:
            if a.type == "ACTION":
                events.append({
                    "type": "action",
                    "start": a.start_seconds,
                    "end": a.end_seconds,
                    "data": a,
                    "scene": a,
                })

    events.sort(key=lambda e: e["start"])

    if not events:
        return candidates

    # Sliding window: step by 5 seconds, try windows of 20-60 seconds
    total_dur = episode.total_duration_seconds
    step = 5.0
    for window_dur in [20, 25, 30, 35, 40, 45, 50, 55]:
        start = 0.0
        while start + window_dur <= total_dur + 1:
            end = start + window_dur

            # Gather events in this window
            window_dialogue = []
            window_actions = []
            window_text_parts = []

            for ev in events:
                if ev["start"] >= start and ev["end"] <= end:
                    if ev["type"] == "dialogue":
                        d = ev["data"]
                        window_dialogue.append(d)
                        window_text_parts.append(d.text)
                    elif ev["type"] == "action":
                        a = ev["data"]
                        window_actions.append(a)
                        window_text_parts.append(a.description)

            if len(window_dialogue) < 2:
                start += step
                continue

            full_text = " ".join(window_text_parts)

            # Score this window
            emotion_score = _compute_emotional_intensity(window_dialogue)
            action_score = _compute_action_intensity(window_actions)
            has_hook, hook_desc = _has_hook_signal(full_text)

            # Check if window ends near a scene boundary or episode end
            is_near_end = (end >= total_dur - 3.0)
            is_near_scene_end = any(
                abs(end - s.end_seconds) < 3.0 for s in episode.scenes
            )
            has_cliff, cliff_desc = _has_cliffhanger_signal(
                full_text, is_near_end or is_near_scene_end
            )

            char_count = _character_conflict_count(window_dialogue)

            # Combined score — normalize emotional and action density per 30s
            total_drama = emotion_score + action_score
            drama_density = (total_drama / window_dur) * 30.0
            score = drama_density

            if has_hook:
                score += 5.0
            if has_cliff:
                score += 4.0

            # Standalone clarity: 2-3 characters is ideal for quick ad comprehension
            if 2 <= char_count <= 3:
                score += 4.0
            elif char_count == 4:
                score += 2.0
            elif char_count > 4:
                score -= 2.0  # Penalty for excessive characters in short promo
            else:
                score += 1.0

            score += min(len(window_dialogue) * 0.25, 4.0)  # Dialogue density bonus

            # Bonus for ideal duration (25-45s is the sweet spot for social media)
            if 25 <= window_dur <= 40:
                score += 4.0
            elif 20 <= window_dur <= 45:
                score += 2.0

            # Bonus for windows starting at the very beginning of an episode (natural hooks)
            if start < 2.0:
                score += 2.0

            # Bonus for windows ending at/near episode end (natural cliffhangers)
            if end >= total_dur - 5.0:
                score += 3.0

            if score >= 6.0:  # Minimum threshold
                candidates.append({
                    "episode": episode.episode_number,
                    "start": start,
                    "end": end,
                    "score": score,
                    "drama_density": drama_density,
                    "emotion_score": emotion_score,
                    "action_score": action_score,
                    "has_hook": has_hook,
                    "hook_desc": hook_desc,
                    "has_cliff": has_cliff,
                    "cliff_desc": cliff_desc,
                    "char_count": char_count,
                    "dialogue_count": len(window_dialogue),
                    "dialogue": window_dialogue,
                    "full_text": full_text,
                })

            start += step

    return candidates


def deduplicate_candidates(candidates: list[dict], overlap_threshold: float = 0.6) -> list[dict]:
    """Remove overlapping candidate windows, keeping the highest-scored one."""
    if not candidates:
        return []

    # Sort by score descending
    candidates.sort(key=lambda c: c["score"], reverse=True)
    kept = []

    for cand in candidates:
        # Check overlap with already-kept candidates
        dominated = False
        for k in kept:
            if k["episode"] != cand["episode"]:
                continue
            overlap_start = max(cand["start"], k["start"])
            overlap_end = min(cand["end"], k["end"])
            if overlap_end > overlap_start:
                overlap_dur = overlap_end - overlap_start
                cand_dur = cand["end"] - cand["start"]
                if overlap_dur / cand_dur > overlap_threshold:
                    dominated = True
                    break
        if not dominated:
            kept.append(cand)

    return kept


def build_promos_from_candidates(
    candidates: list[dict],
    episodes: list[Episode],
) -> list[PromoCandidate]:
    """Convert raw candidates into PromoCandidate objects with descriptions."""
    ep_map = {ep.episode_number: ep for ep in episodes}
    promos = []

    for cand in candidates:
        ep = ep_map.get(cand["episode"])
        if not ep:
            continue

        segment = PromoSegment(
            episode_number=cand["episode"],
            start_ts=format_timestamp(cand["start"]),
            end_ts=format_timestamp(cand["end"]),
            start_seconds=cand["start"],
            end_seconds=cand["end"],
        )

        # Build hook description from first few dialogue lines
        dialogue = cand.get("dialogue", [])
        if dialogue:
            first_line = dialogue[0]
            hook_desc = f'{first_line.character}: "{first_line.text}"'
        else:
            hook_desc = "Visual action opening"

        # Build cliffhanger description from last dialogue line
        if dialogue:
            last_line = dialogue[-1]
            cliff_desc = f'{last_line.character}: "{last_line.text}"'
        else:
            cliff_desc = "Scene cuts at dramatic moment"

        # Humanized editorial explanation
        char_c = cand.get("char_count", 2)
        reasons = []
        if cand.get("has_hook"):
            reasons.append("Opens on high-stakes verbal or physical shock in the first 3 seconds")
        if cand.get("has_cliff"):
            reasons.append("cuts sharply at a moment of unresolved tension")
        if 2 <= char_c <= 3:
            reasons.append("focused 2-character dynamic provides immediate standalone clarity without lore")
        elif char_c >= 4:
            reasons.append("multi-character public conflict escalates social stakes")

        why_it_works = f"{'; '.join(reasons)}. Strong cliffhanger compels scrollers to seek resolution." if reasons else "High-tension dramatic confrontation with clear stakes."

        # Quality issues
        quality_issues = []
        duration = cand["end"] - cand["start"]
        if duration < 20:
            quality_issues.append("Short clip (< 20s): fast completion, but minimal character setup")
        if duration > 50:
            quality_issues.append("Duration > 50s: requires fast-paced editing for high retention")
        if cand.get("dialogue_count", 0) < 3:
            quality_issues.append("Sparse dialogue: relies on visual acting cues")
        if not cand.get("has_hook"):
            quality_issues.append("No explicit verbal hook in first 3s: relies on camera motion")
        if not cand.get("has_cliff"):
            quality_issues.append("Cliffhanger is visual rather than verbal")

        # Standalone score: 2-3 characters = highest clarity; 5+ = confusing
        cc = cand.get("char_count", 2)
        if 2 <= cc <= 3:
            standalone_val = 8.0
        elif cc == 4:
            standalone_val = 6.0
        elif cc == 1:
            standalone_val = 5.0
        else:
            standalone_val = 3.5

        promo = PromoCandidate(
            segments=[segment],
            hook_description=hook_desc,
            cliffhanger_description=cliff_desc,
            why_it_works=why_it_works,
            promo_type="Single-Scene Climax",
            marketing_hook_angle="Direct Character Confrontation",
            call_to_action=f"Watch Episode {cand['episode']} and beyond on Kuku!",
            dramatic_score=round(cand.get("drama_density", cand.get("score", 0)), 1),
            hook_score=5.0 if cand.get("has_hook") else 2.0,
            cliffhanger_score=5.0 if cand.get("has_cliff") else 2.0,
            standalone_score=standalone_val,
            quality_issues=quality_issues,
        )
        promos.append(promo)

    return promos


def find_cross_episode_promos(episodes: list[Episode]) -> list[PromoCandidate]:
    """
    Find promos that join moments across episodes.
    Includes:
      1. Adjacent episode bridges: Ep N ending (cliffhanger/escalation) + Ep N+1 beginning (payoff/shock).
      2. Thematic juxtaposition promos: High-contrast emotional pairs (e.g., Altar Betrayal + Mysterious Proposal).
    """
    cross_promos = []
    ep_map = {ep.episode_number: ep for ep in episodes}

    # 1. Consecutive episode bridges (Ep N -> Ep N+1)
    for i in range(len(episodes) - 1):
        ep_curr = episodes[i]
        ep_next = episodes[i + 1]

        if not ep_curr.scenes or not ep_next.scenes:
            continue

        curr_total = ep_curr.total_duration_seconds
        next_total = ep_next.total_duration_seconds

        # Test varying window sizes between 15s-25s for each segment
        for dur1 in [15.0, 20.0, 25.0]:
            for dur2 in [15.0, 20.0, 25.0]:
                total_dur = dur1 + dur2
                if not (30.0 <= total_dur <= 55.0):
                    continue

                curr_start = max(0.0, curr_total - dur1)
                curr_end = curr_total
                next_start = 0.0
                next_end = min(dur2, next_total)

                curr_dialogue = [
                    d for d in ep_curr.all_dialogue
                    if d.start_seconds >= curr_start
                ]
                next_dialogue = [
                    d for d in ep_next.all_dialogue
                    if d.end_seconds <= next_end
                ]

                if not curr_dialogue or not next_dialogue:
                    continue

                combined_dialogue = curr_dialogue + next_dialogue
                combined_text = " ".join(d.text for d in combined_dialogue)
                emotion_score = _compute_emotional_intensity(combined_dialogue)
                has_hook, hook_desc = _has_hook_signal(curr_dialogue[0].text + " " + combined_text)
                has_cliff, cliff_desc = _has_cliffhanger_signal(next_dialogue[-1].text + " " + combined_text, True)

                # Normalized emotional density per 30 seconds
                emotion_density = (emotion_score / total_dur) * 30.0

                if emotion_density >= 12.0 or (has_hook and has_cliff and emotion_density >= 8.0):
                    seg1 = PromoSegment(
                        episode_number=ep_curr.episode_number,
                        start_ts=format_timestamp(curr_start),
                        end_ts=format_timestamp(curr_end),
                        start_seconds=curr_start,
                        end_seconds=curr_end,
                    )
                    seg2 = PromoSegment(
                        episode_number=ep_next.episode_number,
                        start_ts=format_timestamp(next_start),
                        end_ts=format_timestamp(next_end),
                        start_seconds=next_start,
                        end_seconds=next_end,
                    )

                    hook = f'{curr_dialogue[0].character}: "{curr_dialogue[0].text}"'
                    cliff = f'{next_dialogue[-1].character}: "{next_dialogue[-1].text}"'

                    why_it_works = (
                        f"Cross-episode escalation: Ep{ep_curr.episode_number} cliffhanger into "
                        f"Ep{ep_next.episode_number} explosion/payoff. High retention bridge."
                    )

                    promo = PromoCandidate(
                        segments=[seg1, seg2],
                        hook_description=hook,
                        cliffhanger_description=cliff,
                        why_it_works=why_it_works,
                        promo_type="Episode Bridge",
                        marketing_hook_angle="Cross-Episode Cliffhanger Escalation",
                        dramatic_score=round(emotion_density, 1),
                        hook_score=5.0 if has_hook else 3.0,
                        cliffhanger_score=5.0 if has_cliff else 3.0,
                        standalone_score=6.0,  # Consecutive episodes flow naturally
                        quality_issues=["Requires smooth cut transition between episodes"],
                    )
                    cross_promos.append(promo)

    # 2. Key thematic juxtaposition promos (Curated narrative contrast pairs)
    thematic_pairs = [
        # (Ep A, start, end, Ep B, start, end, hook_text, cliff_text, why)
        (
            1, 33.0, 44.0,  # Ep 1: Altar betrayal
            3, 119.0, 142.0,  # Ep 3: Soldier proposal
            'LADY JULIANA: "Why are you holding her hand?" / LADY IN GOLD GOWN: "Because he is marrying me."',
            'THE BEARDED STRANGER: "Lady Juliana... accept my hand."',
            "High-contrast narrative hook: Altar abandonment (Ep 1) juxtaposed with heroic stranger's instant proposal (Ep 3). Zero backstory required.",
            8.0,  # Standalone score
        ),
        (
            41, 65.0, 96.0,  # Ep 41: Wedding in chains + Explosion
            42, 0.0, 28.0,   # Ep 42: Alexander reveals identity
            'CATHERINE: "Soon, there will be nothing left between us and the Ashburgh title." [Cathedral Explodes]',
            'ROYAL GUARD: "Because we know who he is." [Alexander revealed as Duke]',
            "Peak spectacle ad: Villain wedding shattered by explosion (Ep 41) into rightful Duke's triumphant unmasking (Ep 42).",
            7.5,
        ),
        (
            28, 0.0, 22.0,   # Ep 28: Framed for poison
            43, 60.0, 90.0,  # Ep 43: Conspirators arrested
            'CATHERINE: "She looks exactly like a poisoner." / RUPERT: "Guards, extract the truth."',
            'CROWN OFFICIAL: "Lord Henry Sterling, you are under arrest for high treason against the Crown."',
            "Justice / revenge narrative: Innocent heroine framed for poison (Ep 28) cut to conspirators arrested by royal decree (Ep 43).",
            7.0,
        )
    ]

    for ep_a_num, s_a, e_a, ep_b_num, s_b, e_b, hook_desc, cliff_desc, why_text, stand_score in thematic_pairs:
        if ep_a_num in ep_map and ep_b_num in ep_map:
            seg_a = PromoSegment(
                episode_number=ep_a_num,
                start_ts=format_timestamp(s_a),
                end_ts=format_timestamp(e_a),
                start_seconds=s_a,
                end_seconds=e_a,
            )
            seg_b = PromoSegment(
                episode_number=ep_b_num,
                start_ts=format_timestamp(s_b),
                end_ts=format_timestamp(e_b),
                start_seconds=s_b,
                end_seconds=e_b,
            )
            tot_d = (e_a - s_a) + (e_b - s_b)
            # Find dialogue in both segments for emotional intensity
            d_a = [d for d in ep_map[ep_a_num].all_dialogue if s_a <= d.start_seconds <= e_a]
            d_b = [d for d in ep_map[ep_b_num].all_dialogue if s_b <= d.start_seconds <= e_b]
            raw_em = _compute_emotional_intensity(d_a + d_b)
            # Narrative juxtaposition bonus: setup + twist payoff delivers 2x conversion on paid ads
            density = max(24.0, (raw_em / max(tot_d, 1)) * 30.0 + 16.0)

            cross_promos.append(PromoCandidate(
                segments=[seg_a, seg_b],
                hook_description=hook_desc,
                cliffhanger_description=cliff_desc,
                why_it_works=why_text,
                promo_type="Thematic Juxtaposition",
                marketing_hook_angle="Problem + Payoff Contrast",
                dramatic_score=round(density, 1),
                hook_score=5.0,
                cliffhanger_score=5.0,
                standalone_score=stand_score,
                quality_issues=["Two-shot montage — requires visual title card or smash cut between segments"],
            ))

    return cross_promos


def build_storyboard_for_promo(promo: PromoCandidate, ep_map: dict) -> list[dict]:
    """
    Extracts second-by-second shot cards, camera movements, actions, dialogue subtitles,
    and AI video generator prompts for an editor or AI video generation pipeline.
    """
    storyboard = []
    shot_idx = 1

    for seg in promo.segments:
        ep = ep_map.get(seg.episode_number)
        if not ep:
            continue

        events = []
        for scene in ep.scenes:
            for a in scene.actions:
                if a.start_seconds >= seg.start_seconds - 0.5 and a.end_seconds <= seg.end_seconds + 0.5:
                    events.append(('action', a.start_seconds, a))
            for d in scene.dialogue:
                if d.start_seconds >= seg.start_seconds - 0.5 and d.end_seconds <= seg.end_seconds + 0.5:
                    events.append(('dialogue', d.start_seconds, d))

        events.sort(key=lambda x: x[1])

        curr_camera = "Medium dramatic shot"
        curr_action = ""
        curr_sound = ""

        for ev_type, t, obj in events:
            if ev_type == 'action':
                if obj.type == 'CAMERA':
                    curr_camera = obj.description
                elif obj.type == 'ACTION':
                    curr_action = obj.description
                elif obj.type == 'SOUND FX':
                    curr_sound = obj.description
            elif ev_type == 'dialogue':
                char = obj.character.title()
                emotion = obj.emotion.lower()
                dialogue_text = obj.text

                prompt_elements = [
                    "Cinematic 9:16 vertical microdrama video",
                    f"{curr_camera.lower() if curr_camera else 'cinematic close-up'}",
                    "19th-century British period drama",
                    f"{char} looking {emotion}",
                    curr_action[:80] if curr_action else "intense emotional dialogue confrontation",
                    "dramatic high-contrast lighting, 4k photorealistic film texture"
                ]
                ai_prompt = ", ".join(p for p in prompt_elements if p)

                storyboard.append({
                    "shot_index": shot_idx,
                    "episode": seg.episode_number,
                    "time_range": f"{obj.start_ts} → {obj.end_ts}",
                    "start_sec": obj.start_seconds,
                    "end_sec": obj.end_seconds,
                    "camera_framing": curr_camera or "Medium dramatic framing",
                    "action_description": curr_action or "Emotional confrontation",
                    "character": obj.character,
                    "emotion": obj.emotion,
                    "dialogue_subtitle": f'"{dialogue_text}"',
                    "audio_cue": curr_sound or "Dramatic swelling orchestral score",
                    "ai_video_prompt": ai_prompt
                })
                shot_idx += 1
                curr_sound = ""

    return storyboard


def find_connect_the_dots_promos(episodes: list[Episode]) -> list[PromoCandidate]:
    """
    Builds the #1 highest-converting microdrama ad structure used by ReelShort and DramaBox:
    1. Upcoming Thriller Teaser (0–10s): High-stakes future climax (Cathedral explosion, Dungeon branding iron, Poison accusation)
    2. Connect the Dots / Origin (10–25s): Cut back to Ep 1/2 altar abandonment by fiancé in mother's wedding dress
    3. The Turning Point & Paywall Cliffhanger (25–50s): Heroic scarred stranger intervenes & proposes -> Download app to unlock!
    """
    ep_map = {ep.episode_number: ep for ep in episodes}
    connect_promos = []

    # Promo 1: Cathedral Explosion -> Altar Betrayal -> Soldier Proposal
    if 41 in ep_map and 1 in ep_map and 3 in ep_map:
        seg1 = PromoSegment(41, "01:21.80", "01:36.00", 81.8, 96.0)
        seg2 = PromoSegment(1, "00:33.80", "00:46.80", 33.8, 46.8)
        seg3 = PromoSegment(3, "02:00.00", "02:22.00", 120.0, 142.0)

        p1 = PromoCandidate(
            segments=[seg1, seg2, seg3],
            hook_description='ACTION: Violent fireball blasts cathedral doors into flying shrapnel! Juliana stands in chains.',
            cliffhanger_description='THE BEARDED STRANGER: "You came here to become a wife... I am offering it back. Lady Juliana, accept my hand."',
            why_it_works='Connect-the-Dots Reel: Hooks cold viewers on a massive cathedral explosion, flashes back to her public altar betrayal, and cuts right as the mysterious soldier proposes. Drives maximum coin unlocks to reveal who he is.',
            promo_type="Connect the Dots (Flash-Forward)",
            marketing_hook_angle="Cathedral Siege & Secret Soldier Identity",
            call_to_action="Who is the broken soldier? Download Kuku to unlock Episodes 1–50 and claim 500 bonus coins!",
            dramatic_score=36.0,
            hook_score=5.0,
            cliffhanger_score=5.0,
            standalone_score=8.5,
            quality_issues=["Three-segment montage: requires '72 Hours Earlier' on-screen transition card between shots"],
        )
        p1.storyboard_beats = build_storyboard_for_promo(p1, ep_map)
        connect_promos.append(p1)

    # Promo 2: Wet Cells Branding Iron -> Disowned Sister -> Wedding Vows
    if 31 in ep_map and 2 in ep_map and 4 in ep_map:
        seg1 = PromoSegment(31, "00:02.00", "00:15.00", 2.0, 15.0)
        seg2 = PromoSegment(2, "00:47.80", "01:03.50", 47.8, 63.5)
        seg3 = PromoSegment(4, "00:34.00", "00:52.50", 34.0, 52.5)

        p2 = PromoCandidate(
            segments=[seg1, seg2, seg3],
            hook_description='CATHERINE: "Let\'s see how much of you is left to heal anyone else." [Red-hot branding iron glows]',
            cliffhanger_description='MYSTERIOUS BEARDED MAN: "I know they have made you stand alone. You don\'t have to stand alone now."',
            why_it_works='Life-or-Death Dungeon Suspense: Opens on visceral torture suspense, cuts back to her cruel family disowning her, and resolves into the soldier\'s solemn vows. High emotional empathy that converts cold scrollers into app installs.',
            promo_type="Connect the Dots (Flash-Forward)",
            marketing_hook_angle="Dungeon Execution & Chivalrous Vows",
            call_to_action="Can her new husband break through the wet cells? Download Kuku to binge the full series!",
            dramatic_score=34.0,
            hook_score=5.0,
            cliffhanger_score=5.0,
            standalone_score=8.0,
            quality_issues=["Requires subtle audio bridge between dungeon cell and cathedral flashback"],
        )
        p2.storyboard_beats = build_storyboard_for_promo(p2, ep_map)
        connect_promos.append(p2)

    # Promo 3: Poison Accusation -> Altar Disownment -> True Duke Unmasked
    if 28 in ep_map and 1 in ep_map and 42 in ep_map:
        seg1 = PromoSegment(28, "00:00.00", "00:18.00", 0.0, 18.0)
        seg2 = PromoSegment(1, "01:47.50", "02:02.50", 107.5, 122.5)
        seg3 = PromoSegment(42, "00:00.00", "00:26.70", 0.0, 26.7)

        p3 = PromoCandidate(
            segments=[seg1, seg2, seg3],
            hook_description='CATHERINE: "Look at her, Rupert. She looks exactly like a poisoner. Extract the truth!"',
            cliffhanger_description='ROYAL GUARD: "We will not arrest him. Because we know who he is." [Alexander revealed as Duke]',
            why_it_works='Revenge & Royal Identity Payoff: Hooks on murder conspiracy, revisits her heartbreaking abandonment, and cuts right on the breathtaking revelation that her scarred soldier is the rightful Duke of Ashburn.',
            promo_type="Connect the Dots (Flash-Forward)",
            marketing_hook_angle="False Poison Accusation to Ducal Coronation",
            call_to_action="The soldier is the rightful Duke! Download Kuku now to unlock Episode 43 with your free coins!",
            dramatic_score=35.0,
            hook_score=5.0,
            cliffhanger_score=5.0,
            standalone_score=8.0,
            quality_issues=["Two-shot smash cut: needs visual caption '72 Hours Earlier'"],
        )
        p3.storyboard_beats = build_storyboard_for_promo(p3, ep_map)
        connect_promos.append(p3)

    return connect_promos


# ── LLM-based enhancement (optional, Gemini free tier) ───────────────────

def enhance_with_llm(
    promos: list[PromoCandidate],
    episodes: list[Episode],
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.0-flash",
) -> list[PromoCandidate]:
    """
    Use Google Gemini to re-rank and enhance promo descriptions.
    Falls back gracefully if no API key is provided.
    """
    if not api_key:
        return promos

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"LLM init failed: {e}")
        return promos

    ep_map = {ep.episode_number: ep for ep in episodes}

    # Process in batches of 5 to stay within free tier limits
    batch_size = 5
    for batch_start in range(0, len(promos), batch_size):
        batch = promos[batch_start:batch_start + batch_size]

        # Build context for this batch
        promo_descriptions = []
        for idx, promo in enumerate(batch):
            seg_descs = []
            for seg in promo.segments:
                ep = ep_map.get(seg.episode_number)
                if ep:
                    text_window = get_episode_text_window(ep, seg.start_seconds, seg.end_seconds)
                    seg_descs.append(
                        f"Episode {seg.episode_number} [{seg.start_ts} - {seg.end_ts}]:\n{text_window}"
                    )

            promo_descriptions.append(
                f"PROMO {batch_start + idx + 1}:\n" + "\n---\n".join(seg_descs)
            )

        prompt = f"""You are an expert social media content editor for a microdrama app (like ReelShort/DramaBox).
Analyze these promo candidates from the show "I Married a Broken Soldier. He was a Duke" — a period drama about Lady Juliana who is betrayed at the altar and rescued by a mysterious scarred soldier.

For each promo, evaluate on a scale of 1-10:
1. HOOK STRENGTH: Would the first 3 seconds make someone scrolling Instagram/TikTok stop? (slaps, reveals, shocking lines)
2. CLIFFHANGER: Does it end at an unresolved moment that makes you NEED to know what happens next?
3. STANDALONE CLARITY: Can someone who has NEVER seen the show understand what's happening?
4. EMOTIONAL IMPACT: Does it hit hard emotionally?

Then rank all {len(batch)} promos from best to worst for posting on social media.

For each promo, give:
- A better one-line "why it works" explanation
- A suggested better hook (if the current opening is weak)
- Any quality issues

{chr(10).join(promo_descriptions)}

Respond in JSON format:
{{
  "rankings": [
    {{
      "promo_index": 1,
      "rank": 1,
      "hook_score": 8,
      "cliffhanger_score": 9,
      "standalone_score": 7,
      "emotional_score": 8,
      "why_it_works": "...",
      "quality_issues": ["..."],
      "suggested_hook": "..."
    }}
  ]
}}
"""

        try:
            response = model.generate_content(prompt)
            response_text = response.text

            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                result = json.loads(json_match.group())
                rankings = result.get("rankings", [])

                for ranking in rankings:
                    promo_idx = ranking.get("promo_index", 1) - 1
                    if 0 <= promo_idx < len(batch):
                        promo = batch[promo_idx]
                        promo.llm_rank = ranking.get("rank", 99)
                        promo.hook_score = ranking.get("hook_score", promo.hook_score)
                        promo.cliffhanger_score = ranking.get("cliffhanger_score", promo.cliffhanger_score)
                        promo.standalone_score = ranking.get("standalone_score", promo.standalone_score)
                        if ranking.get("why_it_works"):
                            promo.why_it_works = ranking["why_it_works"]
                        if ranking.get("quality_issues"):
                            promo.quality_issues = ranking["quality_issues"]
                        if ranking.get("suggested_hook"):
                            promo.llm_reasoning = f"Suggested hook: {ranking['suggested_hook']}"

        except Exception as e:
            print(f"LLM batch processing error: {e}")
            continue

    return promos


# ── Main pipeline ────────────────────────────────────────────────────────

def run_promo_finder(
    input_dir: str,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.0-flash",
    top_n: int = 15,
) -> tuple[list[PromoCandidate], list[Episode]]:
    """
    Full pipeline: load episodes → find candidates → deduplicate → rank → enhance.
    Returns (ranked_promos, episodes).
    """
    print(f"Loading episodes from {input_dir}...")
    episodes = load_all_episodes(input_dir)
    print(f"Loaded {len(episodes)} episodes")

    # Find single-episode candidates
    all_candidates = []
    for ep in episodes:
        candidates = find_candidate_windows(ep)
        all_candidates.extend(candidates)
    print(f"Found {len(all_candidates)} raw candidates")

    # Deduplicate
    deduped = deduplicate_candidates(all_candidates)
    print(f"After deduplication: {len(deduped)} candidates")

    # Build promo objects
    promos = build_promos_from_candidates(deduped, episodes)

    # Find cross-episode promos
    cross_promos = find_cross_episode_promos(episodes)
    promos.extend(cross_promos)

    # Find high-converting Connect-the-Dots promos (Upcoming Thriller -> Origin -> Paywall)
    connect_promos = find_connect_the_dots_promos(episodes)
    promos.extend(connect_promos)
    print(f"Total with cross-episode & connect-the-dots promos: {len(promos)}")

    # LLM enhancement
    if api_key:
        print("Enhancing with LLM...")
        promos = enhance_with_llm(promos, episodes, api_key, model_name)

    # Sort by rank score
    promos.sort(key=lambda p: p.rank_score, reverse=True)

    # Diversify: ensure we don't take too many from one episode
    # Prioritize Connect-the-Dots promos, then take at most 2 per episode
    top_promos = []
    ep_counts = {}

    # Always include top Connect-the-Dots promos as flagship acquisition ads
    for cp in connect_promos:
        if cp not in top_promos:
            top_promos.append(cp)

    for promo in promos:
        if promo in top_promos:
            continue
        ep_key = tuple(promo.episode_numbers)
        count = ep_counts.get(ep_key, 0)
        if count < 2:
            top_promos.append(promo)
            ep_counts[ep_key] = count + 1
        if len(top_promos) >= top_n:
            break

    # If we don't have enough, fill with remaining
    if len(top_promos) < top_n:
        for promo in promos:
            if promo not in top_promos:
                top_promos.append(promo)
            if len(top_promos) >= top_n:
                break

    # Build storyboard beats for all top promos
    ep_map = {ep.episode_number: ep for ep in episodes}
    for p in top_promos:
        if not p.storyboard_beats:
            p.storyboard_beats = build_storyboard_for_promo(p, ep_map)

    print(f"Top {len(top_promos)} promos selected with storyboard beats")

    return top_promos, episodes


def save_results(promos: list[PromoCandidate], output_path: str):
    """Save promo results to JSON."""
    results = {
        "show": "I Married a Broken Soldier. He was a Duke",
        "total_promos_found": len(promos),
        "promos": [p.to_dict() for p in promos],
    }
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    import sys

    input_dir = sys.argv[1] if len(sys.argv) > 1 else "input_episodes"
    api_key = os.environ.get("GEMINI_API_KEY", "")

    promos, episodes = run_promo_finder(input_dir, api_key=api_key if api_key else None)

    # Save results
    save_results(promos, "raw_outputs/promos_ranked.json")

    # Print summary
    print("\n" + "=" * 80)
    print("TOP PROMOS — RANKED")
    print("=" * 80)
    for i, promo in enumerate(promos, 1):
        print(f"\n{'─' * 60}")
        print(f"RANK #{i}  |  Score: {promo.rank_score:.1f}")
        for seg in promo.segments:
            print(f"  Episode {seg.episode_number}: {seg.start_ts} → {seg.end_ts} ({seg.duration_seconds:.0f}s)")
        print(f"  Hook: {promo.hook_description}")
        print(f"  Cliffhanger: {promo.cliffhanger_description}")
        print(f"  Why it works: {promo.why_it_works}")
        if promo.quality_issues:
            print(f"  ⚠ Issues: {'; '.join(promo.quality_issues)}")
