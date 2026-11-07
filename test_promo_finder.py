"""
test_promo_finder.py — Unit tests and validation suite for Kuku Promo Finder.
Run with: pytest or python3 test_promo_finder.py
"""

import unittest
import os
import json
import tempfile
from screenplay_parser import (
    parse_timestamp, format_timestamp, parse_episode, load_all_episodes
)
from promo_finder import (
    PromoSegment, PromoCandidate, find_candidate_windows,
    deduplicate_candidates, build_promos_from_candidates,
    find_cross_episode_promos, run_promo_finder
)

SAMPLE_EPISODE_TEXT = """EPISODE NUMBER: Episode 99
EPISODE LOGLINE: A dramatic confrontation unfolds when Lady Sarah rejects the Duke's advances.
CONTINUITY NOTES: Follows Episode 98 where Sarah received the mysterious poisoned letter.

--- SCRIPT START ---

SCENE 01
Scene heading: INT. BALLROOM – NIGHT
Scene start: 00:00.00
Scene end: 00:45.00

Actions and dialogue:

**CAMERA:**
Start: (00:00.00) | End: (00:02.50)
Close-up on Lady Sarah clutching her wine glass with trembling hands.

**LADY SARAH (Furious, Accusing):**
Start: (00:01.00) | End: (00:03.50)
"You poisoned my family!"

**DUKE EDWARD (Cold, Mocking):**
Start: (00:04.00) | End: (00:07.00)
"You have no proof, Sarah."

**ACTION:**
Start: (00:07.50) | End: (00:09.50)
Lady Sarah slaps the Duke across the face, the sound echoing through the hall.

**LADY SARAH (Desperate, Shivering):**
Start: (00:10.00) | End: (00:13.00)
"The whole kingdom will know your treason!"

**SOUND FX:**
Start: (00:13.00) | End: (00:14.00)
Stunned gasp from the entire ballroom congregation.

--- SCRIPT END ---
"""


class TestScreenplayParser(unittest.TestCase):

    def test_timestamp_conversions(self):
        self.assertAlmostEqual(parse_timestamp("00:00.00"), 0.0)
        self.assertAlmostEqual(parse_timestamp("01:30.00"), 90.0)
        self.assertAlmostEqual(parse_timestamp("02:15.50"), 135.5)
        self.assertEqual(format_timestamp(90.0), "01:30.00")
        self.assertEqual(format_timestamp(0.0), "00:00.00")

    def test_parse_episode(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
            f.write(SAMPLE_EPISODE_TEXT)
            f_path = f.name

        try:
            ep = parse_episode(f_path)
            self.assertEqual(ep.episode_number, 99)
            self.assertIn("confrontation unfolds", ep.logline)
            self.assertEqual(len(ep.scenes), 1)
            self.assertEqual(len(ep.scenes[0].dialogue), 3)
            self.assertEqual(ep.scenes[0].dialogue[0].character, "LADY SARAH")
            self.assertEqual(ep.scenes[0].dialogue[0].text, "You poisoned my family!")
            self.assertEqual(ep.scenes[0].dialogue[0].start_seconds, 1.0)
            self.assertIn("LADY SARAH", ep.all_characters)
            self.assertIn("DUKE EDWARD", ep.all_characters)
        finally:
            os.remove(f_path)


class TestPromoFinder(unittest.TestCase):

    def setUp(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
            f.write(SAMPLE_EPISODE_TEXT)
            self.sample_file = f.name
        self.sample_episode = parse_episode(self.sample_file)

    def tearDown(self):
        if os.path.exists(self.sample_file):
            os.remove(self.sample_file)

    def test_candidate_window_detection(self):
        candidates = find_candidate_windows(self.sample_episode, min_dur=20.0, max_dur=45.0)
        self.assertGreater(len(candidates), 0)
        top = candidates[0]
        self.assertTrue(top["has_hook"])
        self.assertEqual(top["char_count"], 2)

    def test_deduplication(self):
        cand1 = {"episode": 1, "start": 0.0, "end": 30.0, "score": 50.0}
        cand2 = {"episode": 1, "start": 5.0, "end": 35.0, "score": 60.0}
        cand3 = {"episode": 2, "start": 0.0, "end": 30.0, "score": 40.0}
        deduped = deduplicate_candidates([cand1, cand2, cand3], overlap_threshold=0.5)
        self.assertEqual(len(deduped), 2)
        # Should keep cand2 for ep 1 because of higher score
        ep1_cand = next(c for c in deduped if c["episode"] == 1)
        self.assertEqual(ep1_cand["score"], 60.0)

    def test_promo_structure_to_dict(self):
        seg = PromoSegment(
            episode_number=99,
            start_ts="00:01.00",
            end_ts="00:14.00",
            start_seconds=1.0,
            end_seconds=14.0
        )
        promo = PromoCandidate(
            segments=[seg],
            hook_description="You poisoned my family!",
            cliffhanger_description="The whole kingdom will know your treason!",
            why_it_works="Instant physical and emotional stakes",
            dramatic_score=35.0,
            hook_score=5.0,
            cliffhanger_score=5.0,
            standalone_score=8.0,
        )
        d = promo.to_dict()
        self.assertEqual(d["total_duration_seconds"], 13.0)
        self.assertEqual(len(d["segments"]), 1)
        self.assertEqual(d["scores"]["overall_rank_score"], 35.0 + 10.0 + 10.0 + 8.0)

    def test_full_pipeline_on_input_pack(self):
        if os.path.isdir("input_episodes"):
            promos, eps = run_promo_finder("input_episodes", top_n=5)
            self.assertEqual(len(promos), 5)
            self.assertEqual(len(eps), 50)
            for p in promos:
                self.assertGreater(p.total_duration, 15.0)
                self.assertLessEqual(p.total_duration, 65.0)
                self.assertTrue(len(p.hook_description) > 0)
                self.assertTrue(len(p.cliffhanger_description) > 0)


if __name__ == "__main__":
    unittest.main()
