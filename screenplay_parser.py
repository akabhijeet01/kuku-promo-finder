"""
screenplay_parser.py — Parses Kuku microdrama screenplays into structured data.

Handles the specific format with EPISODE NUMBER, LOGLINE, CONTINUITY NOTES,
and timestamped SCENE/CAMERA/ACTION/DIALOGUE blocks.
"""

import re
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DialogueLine:
    character: str
    emotion: str
    text: str
    start_ts: str  # "MM:SS.FF"
    end_ts: str
    start_seconds: float
    end_seconds: float


@dataclass
class ActionBeat:
    type: str  # "ACTION", "CAMERA", "SOUND FX"
    description: str
    start_ts: str
    end_ts: str
    start_seconds: float
    end_seconds: float


@dataclass
class Scene:
    scene_number: int
    heading: str
    start_ts: str
    end_ts: str
    start_seconds: float
    end_seconds: float
    dialogue: list[DialogueLine] = field(default_factory=list)
    actions: list[ActionBeat] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds

    @property
    def all_dialogue_text(self) -> str:
        return " ".join(d.text for d in self.dialogue)

    @property
    def characters_present(self) -> set[str]:
        return {d.character for d in self.dialogue}


@dataclass
class Episode:
    episode_number: int
    logline: str
    continuity_notes: str
    scenes: list[Scene] = field(default_factory=list)
    filename: str = ""

    @property
    def total_duration_seconds(self) -> float:
        if not self.scenes:
            return 0.0
        return max(s.end_seconds for s in self.scenes)

    @property
    def total_duration(self) -> float:
        return self.total_duration_seconds

    @property
    def all_characters(self) -> set[str]:
        chars = set()
        for s in self.scenes:
            chars.update(s.characters_present)
        return chars

    @property
    def all_dialogue(self) -> list[DialogueLine]:
        result = []
        for s in self.scenes:
            result.extend(s.dialogue)
        return result


def parse_timestamp(ts_str: str) -> float:
    """Convert 'MM:SS.FF' to seconds as float."""
    ts_str = ts_str.strip()
    match = re.match(r"(\d+):(\d+)\.(\d+)", ts_str)
    if match:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        fraction = int(match.group(3))
        # Normalize fraction (e.g., "04.80" -> 4.80 seconds)
        frac_str = match.group(3)
        frac_val = float(f"0.{frac_str}")
        return minutes * 60 + seconds + frac_val
    # Try simpler format
    match = re.match(r"(\d+):(\d+)", ts_str)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    return 0.0


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS.FF format."""
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:05.2f}"


def parse_screenplay_text(text: str, filename: str = "") -> Episode:
    """Parse the raw text of an episode screenplay into an Episode object."""
    # Extract header info
    ep_num_match = re.search(r"EPISODE NUMBER:\s*Episode\s*(\d+)", text)
    logline_match = re.search(r"EPISODE LOGLINE:\s*(.+?)(?:\n|$)", text)
    continuity_match = re.search(r"CONTINUITY NOTES:\s*(.+?)(?:\n|$)", text)

    ep_num = int(ep_num_match.group(1)) if ep_num_match else 0
    if not filename:
        filename = f"episode-{ep_num:03d}.txt" if ep_num else "episode.txt"

    episode = Episode(
        episode_number=ep_num,
        logline=logline_match.group(1).strip() if logline_match else "",
        continuity_notes=continuity_match.group(1).strip() if continuity_match else "",
        filename=filename,
    )

    # Extract script body
    script_match = re.search(r"--- SCRIPT START ---(.+?)--- SCRIPT END ---", text, re.DOTALL)
    if not script_match:
        # Fallback if standard end delimiter is missing or formatted slightly differently
        body_start = text.find("--- SCRIPT START ---")
        if body_start != -1:
            script_body = text[body_start + len("--- SCRIPT START ---"):]
        else:
            script_body = text
    else:
        script_body = script_match.group(1)

    # Split into scenes
    scene_splits = re.split(r"(SCENE\s+\d+)", script_body)

    for i, part in enumerate(scene_splits):
        scene_header_match = re.match(r"SCENE\s+(\d+)", part.strip())
        if scene_header_match:
            scene_num = int(scene_header_match.group(1))
            # The content follows this header
            if i + 1 < len(scene_splits):
                scene_content = scene_splits[i + 1]
            else:
                continue

            # Parse scene metadata
            heading_match = re.search(r"Scene heading:\s*(.+)", scene_content)
            start_match = re.search(r"Scene start:\s*(\S+)", scene_content)
            end_match = re.search(r"Scene end:\s*(\S+)", scene_content)

            scene = Scene(
                scene_number=scene_num,
                heading=heading_match.group(1).strip() if heading_match else "",
                start_ts=start_match.group(1) if start_match else "00:00.00",
                end_ts=end_match.group(1) if end_match else "00:00.00",
                start_seconds=parse_timestamp(start_match.group(1)) if start_match else 0.0,
                end_seconds=parse_timestamp(end_match.group(1)) if end_match else 0.0,
            )

            # Parse dialogue and actions within scene
            _parse_scene_content(scene_content, scene)
            episode.scenes.append(scene)

    return episode


def parse_episode(filepath: str) -> Episode:
    """Parse a single screenplay file into an Episode object."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    return parse_screenplay_text(text, filename=os.path.basename(filepath))


def parse_merged_screenplay(file_path_or_text: str) -> list[Episode]:
    """Parse a merged screenplay file or text string containing multiple episodes."""
    if os.path.isfile(file_path_or_text):
        with open(file_path_or_text, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = file_path_or_text

    chunks = [c.strip() for c in re.split(r"(?=EPISODE NUMBER:\s*Episode\s*\d+)", text) if c.strip()]
    episodes = []
    for chunk in chunks:
        if "EPISODE NUMBER:" in chunk:
            ep = parse_screenplay_text(chunk)
            if ep.episode_number > 0 or ep.scenes:
                episodes.append(ep)

    episodes.sort(key=lambda e: e.episode_number)
    return episodes


def _parse_scene_content(content: str, scene: Scene):
    """Parse dialogue lines and action beats from scene content."""
    # Pattern for dialogue: **CHARACTER (Emotion):**
    # Pattern: **CHARACTER (Emotion, Emotion):**  or **CHARACTER (O.S.) (Emotion):**
    dialogue_pattern = re.compile(
        r"\*\*([A-Z][A-Z\s'.\-/]+?)(?:\s*\(O\.S\.\))?\s*\(([^)]+)\):\*\*\s*\n"
        r"Start:\s*\(([^)]+)\)\s*\|\s*End:\s*\(([^)]+)\)\s*\n"
        r"\"([^\"]+)\""
    )

    for match in dialogue_pattern.finditer(content):
        character = match.group(1).strip()
        emotion = match.group(2).strip()
        start_ts = match.group(3).strip()
        end_ts = match.group(4).strip()
        text = match.group(5).strip()

        scene.dialogue.append(DialogueLine(
            character=character,
            emotion=emotion,
            text=text,
            start_ts=start_ts,
            end_ts=end_ts,
            start_seconds=parse_timestamp(start_ts),
            end_seconds=parse_timestamp(end_ts),
        ))

    # Pattern for actions: **ACTION:** or **CAMERA:** or **SOUND FX:**
    action_pattern = re.compile(
        r"\*\*(ACTION|CAMERA|SOUND FX):\*\*\s*\n"
        r"Start:\s*\(([^)]+)\)\s*\|\s*End:\s*\(([^)]+)\)\s*\n"
        r"(.+?)(?=\n\n|\n\*\*|\Z)",
        re.DOTALL
    )

    for match in action_pattern.finditer(content):
        beat_type = match.group(1).strip()
        start_ts = match.group(2).strip()
        end_ts = match.group(3).strip()
        description = match.group(4).strip()

        scene.actions.append(ActionBeat(
            type=beat_type,
            description=description,
            start_ts=start_ts,
            end_ts=end_ts,
            start_seconds=parse_timestamp(start_ts),
            end_seconds=parse_timestamp(end_ts),
        ))


def load_all_episodes(source: str = "merged.txt") -> list[Episode]:
    """
    Load and parse all episode files.
    Accepts:
      - Path to a single merged file (e.g. 'merged.txt')
      - Path to a directory containing episode text files (e.g. 'input_episodes')
    """
    if os.path.isfile(source):
        # Could be a single merged file or a single episode
        with open(source, "r", encoding="utf-8") as f:
            sample = f.read(4096)
        # If it looks like a merged file with episodes or standard format
        if "EPISODE NUMBER:" in sample:
            episodes = parse_merged_screenplay(source)
            if episodes:
                return episodes
        return [parse_episode(source)]

    if os.path.isdir(source):
        episodes = []
        # Check if directory contains a merged.txt first
        candidate_merged = os.path.join(source, "merged.txt")
        if os.path.isfile(candidate_merged):
            return parse_merged_screenplay(candidate_merged)

        files = sorted([
            f for f in os.listdir(source)
            if f.endswith(".txt") and not f.startswith(".")
        ])

        for filename in files:
            filepath = os.path.join(source, filename)
            # Check if this file is a merged file or single episode
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            if len(re.findall(r"EPISODE NUMBER:\s*Episode\s*\d+", content)) > 1:
                episodes.extend(parse_merged_screenplay(content))
            else:
                episodes.append(parse_screenplay_text(content, filename=filename))

        episodes.sort(key=lambda e: e.episode_number)
        return episodes

    # Fallback to local files if path wasn't found directly
    if os.path.isfile("merged.txt"):
        return parse_merged_screenplay("merged.txt")
    if os.path.isdir("input_episodes"):
        return load_all_episodes("input_episodes")

    raise FileNotFoundError(f"Screenplay source not found at: {source}")


def get_episode_text_window(episode: Episode, start_sec: float, end_sec: float) -> str:
    """Extract a text summary of what happens in a given time window of an episode."""
    lines = []
    for scene in episode.scenes:
        for d in scene.dialogue:
            if d.start_seconds >= start_sec and d.end_seconds <= end_sec:
                lines.append(f"{d.character} ({d.emotion}): \"{d.text}\"")
        for a in scene.actions:
            if a.type == "ACTION" and a.start_seconds >= start_sec and a.end_seconds <= end_sec:
                lines.append(f"[{a.description}]")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    directory = sys.argv[1] if len(sys.argv) > 1 else "input_episodes"
    episodes = load_all_episodes(directory)
    print(f"Loaded {len(episodes)} episodes")
    for ep in episodes:
        print(f"  Ep {ep.episode_number}: {len(ep.scenes)} scenes, "
              f"{ep.total_duration_seconds:.1f}s, "
              f"chars: {', '.join(ep.all_characters)}")
        print(f"    Logline: {ep.logline[:80]}...")
