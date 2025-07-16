# app.py  – Mumblr backend (creative toggle + tighter syllables/rhyme)

from __future__ import annotations
import os
from typing import Any
from flask import Flask, request
from flask_cors import CORS
from openai import OpenAI

# ── config via env ────────────────────────────────────────────────────────
client           = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL            = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE_SAFE = float(os.getenv("TEMPERATURE", "0.4"))
TEMPERATURE_FREE = 0.7                     # when CREATIVE_MODE == "1"
CREATIVE_MODE    = os.getenv("CREATIVE_MODE") == "1"
SEED             = int(os.getenv("SEED")) if os.getenv("SEED") else None

# ── Flask app ─────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

@app.get("/")
def health() -> tuple[str, int]:
    return "Mumblr API live", 200


@app.post("/mumblr")
def mumblr() -> tuple[Any, int, dict[str, str]]:
    try:
        data          = request.get_json(force=True) or {}
        recordings    = data.get("recordings") or []

        transcription = str(data.get("transcription", "")).strip()
        mood          = str(data.get("mood", "")).strip()
        section       = str(data.get("section", "")).strip()
        story         = str(data.get("story", "")).strip()

        # ── build the raw‑takes block ────────────────────────────────────
        if isinstance(recordings, list) and recordings:
            raw_lines = [str(x).strip() for x in recordings if x]
        else:
            raw_lines = [transcription]

        mumble_block = "\n".join(f"- {l}" for l in raw_lines)
        endings      = ", ".join([l.split()[-1] for l in raw_lines])

        prompt = f"""
You are **Mumblr**, an AI lyric‑finisher.

### Raw takes
{mumble_block}

### Requirements
1. Keep the **core meaning** of every raw line.
2. **Syllable count** for each finished line must match the raw line (±1 syllable).
3. End every line with a word that **rhymes with the last word** of the corresponding raw line
   (target end‑words: {endings}).
4. Return **exactly {len(raw_lines)} numbered lines**, no commentary.

### Context
Mood   : {mood or '(none)'}
Section: {section or '(none)'}
Story  : {story or '(none)'}
"""

        temperature = TEMPERATURE_FREE if CREATIVE_MODE else TEMPERATURE_SAFE

        resp = client.chat.completions.create(
            model       = MODEL,
            temperature = temperature,
            seed        = SEED,
            messages=[
                {"role": "system", "content": "You are a professional lyricist."},
                {"role": "user",    "content": prompt}
            ],
        )

        lyrics = resp.choices[0].message.content
        return lyrics, 200, {"Content-Type": "text/plain"}

    except Exception as exc:
        return {"error": str(exc)}, 500
