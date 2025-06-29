# ─────────────────────────── app.py (full file) ────────────────────────────
"""
Mumblr backend — Flask  +  openai-python ≥ 1.4

•  Accepts POST /mumblr  {transcription, mood, section, story, recordings?}
•  Locks EACH output line to the same syllable-count as the singer’s line
•  Supports deterministic runs via  SEED=42  env var.
•  CORS enabled so any UI (Lovable, local dev, etc.) can call it.
"""

from __future__ import annotations

import os
import re
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI, OpenAIError

# ─────────────────── configuration ─────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # ← already set in Render
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE    = float(os.getenv("TEMPERATURE", "0.7"))
SEED_STR       = os.getenv("SEED")            # leave unset for randomness
SEED           = int(SEED_STR) if SEED_STR else None

# ─────────────────── helper: syllable counter ─────────────────────────────
_vowels = re.compile(r"[aeiouy]+", re.I)

def syllable_count(line: str) -> int:
    """
    Very lightweight syllable estimate:
    • groups of vowels are one syllable
    • silent-e ('love') ignored unless the only vowel
    """
    chunks = _vowels.findall(line.lower())
    count  = len([c for c in chunks if c != "e" or len(chunks) == 1])
    return max(1, count)

# ─────────────────── OpenAI client ────────────────────────────────────────
client = OpenAI(api_key=OPENAI_API_KEY)

# ─────────────────── Flask app ────────────────────────────────────────────
app = Flask(__name__)
CORS(app)                                         # allow any Origin (*)

@app.get("/")
def health() -> tuple[str, int]:
    """Simple health-check for Render."""
    return "Mumblr API is live!", 200

@app.post("/mumblr")
def generate_lyrics() -> tuple[Any, int, dict[str, str]]:
    """
    POST body (JSON):
        {
          transcription : str    – first rough line (fallback),
          mood          : str,
          section       : str,    – Verse / Chorus / Bridge …
          story         : str,    – optional context
          recordings    : list[str]  – optional full array from Lovable
        }
    Response:
        200  plain-text lyrics
        500  {"error": "..."}
    """
    try:
        # 1) ─ grab & sanitize input ------------------------------------------------
        data          = request.get_json(force=True) or {}
        transcription = str(data.get("transcription", "")).strip()
        mood          = str(data.get("mood", "")).strip()
        section       = str(data.get("section", "")).strip()
        story         = str(data.get("story", "")).strip()
        recordings    = data.get("recordings", [])

        if isinstance(recordings, list) and recordings:
            raw_lines = [str(x).strip() for x in recordings if str(x).strip()]
        else:                                  # fallback: single line
            raw_lines = [transcription] if transcription else []

        if not raw_lines:
            return jsonify(error="No lyric lines provided"), 400

        # 2) ─ build prompt with locked syllable counts ----------------------------
        mumble_block = "\n".join(
            f"- {txt}  ({syllable_count(txt)} syllables)" for txt in raw_lines
        )

        prompt = f"""
You are **Mumblr**, an AI lyric-finisher.

### Raw takes  (with syllable counts)
{mumble_block}

### Requirements
1. **Do NOT drop** the core nouns/verbs of each line.
2. Match the **same syllable count** per line (±1 only if unavoidable).
3. Improve rhyme & rhythm; small fillers (“oh”, “yeah”) are fine.
4. Return **exactly {len(raw_lines)} numbered lines**, nothing else.

### Context
Mood : {mood or '(none)'}
Part : {section or '(none)'}
Story: {story or '(none)'}
"""

        # 3) ─ call OpenAI -----------------------------------------------------------
        chat_kwargs = dict(
            model       = OPENAI_MODEL,
            temperature = TEMPERATURE,
            messages = [
                {"role": "system", "content": "You are a professional lyricist."},
                {"role": "user",   "content": prompt},
            ],
        )
        if SEED is not None:                   # optional deterministic run
            chat_kwargs["seed"] = SEED

        resp   = client.chat.completions.create(**chat_kwargs)
        lyrics = resp.choices[0].message.content.strip()

        return lyrics, 200, {"Content-Type": "text/plain"}

    # ─── error handling ────────────────────────────────────────────────────
    except OpenAIError as e:
        return jsonify(error=f"OpenAI: {e}"), 500
    except Exception as e:  # noqa: BLE001
        return jsonify(error=str(e)), 500
