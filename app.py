# ───────────────────────────────── app.py ──────────────────────────────────
"""
Mumblr backend — Flask + openai-python ≥ 1.4

✓  Works with the new OpenAI client (openai.ChatCompletion is deprecated).
✓  CORS enabled so any front-end (Lovable, local dev, etc.) can call it.
✓  Optional deterministic seed – set SEED=42 in Render “Environment”.
✓  Health-check route at “/” so Render shows the service as “Healthy”.
"""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI, OpenAIError

# ── configuration ──────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # set in Render → Environment
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")                  # ← change if you own GPT-4 access
TEMPERATURE    = float(os.getenv("TEMPERATURE", "0.7"))
SEED_STR       = os.getenv("SEED")          # leave unset for natural randomness
SEED           = int(SEED_STR) if SEED_STR else None

SYSTEM_PROMPT = """
Mumblr expects JSON with these keys:
  • transcription – line captured from the user’s singing or humming
  • mood          – Breakup & Heartbreak, Party & Celebration, etc.
  • section       – Verse, Chorus, or Bridge
  • story         – OPTIONAL extra context

The response must be **lyrics only**, plain text, no commentary.
Maintain rhyme & syllabic flow appropriate to the chosen song section.
"""

# ── OpenAI client ──────────────────────────────────────────────────────────
client = OpenAI(api_key=OPENAI_API_KEY)

# ── Flask app ──────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)                       # allow any Origin (*) by default


@app.get("/")
def home() -> tuple[str, int]:
    """Health-check / sanity route."""
    return "Mumblr API is live!", 200


@app.post("/mumblr")
def generate_lyrics() -> tuple[Any, int, dict[str, str]]:
    """
    Accepts a POST with JSON body:
        {transcription, mood, section, story}

    Returns:
        Plain-text lyrics (200)  –or–
        {"error": "..."}  (500)
    """
    try:
        data          = request.get_json(force=True) or {}
        transcription = str(data.get("transcription", "")).strip()
        mood          = str(data.get("mood", "")).strip()
        section       = str(data.get("section", "")).strip()
        story         = str(data.get("story", "")).strip()

        # ---- new prompt build ----
recordings = data.get("recordings", [])     # list[str] coming from Lovable

if isinstance(recordings, list) and recordings:
    raw_lines    = [str(x).strip() for x in recordings if x]
    mumble_block = "\n".join(f"- {l}" for l in raw_lines)
else:                                       # fallback for one-line calls
    raw_lines    = [transcription]
    mumble_block = f"- {transcription}"

prompt = f"""
You are Mumblr, an AI lyric-finisher.

### Raw takes
{mumble_block}

### Requirements
1. Keep **each line’s core words**.
2. Improve rhyme & rhythm; you may adjust tense or add small fillers
   (“oh”, “yeah”) **but don’t drop or replace the key nouns/verbs**.
3. Return **exactly** {len(raw_lines)} numbered lines, nothing else.

### Context
Mood:  {mood}
Part:  {section}
Story: {story or '(none)'}
"""
# ---- end new prompt build ----
