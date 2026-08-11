#!/usr/bin/env python3
from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
import re

path = Path("podcast_writing.md")
assert path.is_file() and path.stat().st_size > 0, "podcast_writing.md is missing or empty"
allowed_names = {"transcript.md", "episode_frame.png", "podcast_writing.md", "worker.log"}
unexpected = sorted(p.name for p in Path(".").iterdir() if p.name not in allowed_names)
assert not unexpected, f"worker created out-of-contract files: {unexpected}"
text = path.read_text(encoding="utf-8")
low = text.casefold()

assert "—" not in text, "em dash is not allowed"
for phrase in ("in today's fast-paced world", "game-changer", "revolutionize", "unlock the power", "delve into"):
    assert phrase not in low, f"stock phrase found: {phrase}"

required_headings = (
    "visual read",
    "take a: operator pain first",
    "take b: founder story first",
    "why the takes differ",
)
for heading in required_headings:
    assert re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.I | re.M), f"missing heading: {heading}"

visual_cues = (
    "small to medium businesses",
    "industry: healthcare",
    "growth, profit & scale",
    "host: brad stevens",
    "guest: ankit patel",
)
visual_hits = [cue for cue in visual_cues if cue in low]
assert len(visual_hits) >= 2, f"multimodal grounding weak; found only {visual_hits}"

transcript_cues = (
    "bottleneck you want to remove",
    "finishing charts at 10 p.m.",
    "trigger, the owner, the expected outcome, and the exception",
    "ai should make work more legible",
    "outsourcing should create ownership",
    "automate only the stable part",
)
transcript_hits = [cue for cue in transcript_cues if cue in low]
assert len(transcript_hits) >= 3, f"transcript grounding weak; found only {transcript_hits}"

word_count = len(re.findall(r"\b[\w’'-]+\b", text))
assert 450 <= word_count <= 1400, f"unexpected total length: {word_count} words"

pattern = re.compile(
    r"^##\s+Take\s+([AB]):\s+[^\n]+\n(?P<body>.*?)(?=^##\s+Take\s+[AB]:|^##\s+Why the Takes Differ|\Z)",
    re.I | re.M | re.S,
)
takes = {m.group(1).upper(): m.group("body") for m in pattern.finditer(text)}
assert set(takes) == {"A", "B"}, f"could not parse both takes: {sorted(takes)}"

for label, body in takes.items():
    for sub in ("title", "hook", "episode description", "social 1", "social 2", "social 3"):
        assert re.search(rf"^###\s+{re.escape(sub)}\s*$", body, re.I | re.M), f"Take {label} missing {sub}"
    title_match = re.search(r"^###\s+Title\s*$\n+(.+)", body, re.I | re.M)
    assert title_match, f"Take {label} title missing"
    title = title_match.group(1).strip().strip("#* ")
    assert len(title) <= 70, f"Take {label} title too long: {len(title)} chars"
    desc_match = re.search(r"^###\s+Episode Description\s*$\n+(.*?)(?=^###\s+Social 1\s*$)", body, re.I | re.M | re.S)
    assert desc_match, f"Take {label} description missing"
    desc_words = len(re.findall(r"\b[\w’'-]+\b", desc_match.group(1)))
    assert 120 <= desc_words <= 240, f"Take {label} description length: {desc_words} words"
    for number in (1, 2, 3):
        social_match = re.search(
            rf"^###\s+Social {number}\s*$\n+(.*?)(?=^###\s+Social {number + 1}\s*$|\Z)",
            body, re.I | re.M | re.S,
        ) if number < 3 else re.search(r"^###\s+Social 3\s*$\n+(.*)\Z", body, re.I | re.M | re.S)
        assert social_match, f"Take {label} social {number} missing"
        social = social_match.group(1).strip()
        assert len(social) <= 500, f"Take {label} social {number} too long: {len(social)} chars"

similarity = SequenceMatcher(None, takes["A"].casefold(), takes["B"].casefold()).ratio()
assert similarity < 0.72, f"takes are cosmetic rewrites; similarity={similarity:.3f}"

print(f"GEMINI_PODCAST_WRITING_OK words={word_count} visual_hits={len(visual_hits)} transcript_hits={len(transcript_hits)} take_similarity={similarity:.3f}")
