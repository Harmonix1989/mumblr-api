# ──────────────── app.py  (v3 – creative toggle) ────────────────
from __future__ import annotations
import os
from typing import Any

from flask import Flask, request
from flask_cors import CORS
from openai import OpenAI

# ── config via env ───────────────────────────────────────────────
client             = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL              = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE_SAFE   = float(os.getenv("TEMPERATURE", "0.4"))
TEMPERATURE_FREE   = 0.6                         # when CREATIVE_MODE=1
CREATIVE_MODE      = os.getenv("CREATIVE_MODE") == "1"
SEED               = int(os.getenv("SEED")) if os.getenv("SEED") else None

# ── Flask app ───────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

@app.get("/")
def health() -> tuple[str, int]:
    return "Mumblr API live", 200

@app.post("/mumblr")
def mumblr() -> tuple[Any, int, dict[str, str]]:
    try:
        data          = request.get_json(force=True) or {}
        recordings    = data.get("recordings") or []
        transcription = str(data.get("transcription", "")).strip()
        mood          = str(data.get("mood", "")).strip()
        section       = str(data.get("section", "")).strip()
        story         = str(data.get("story", "")).strip()

        # --- build the raw‑takes block ---------------------------------------
        if isinstance(recordings, list) and recordings:
            raw_lines = [str(x).strip() for x in recordings if x]
        else:
            raw_lines = [transcription] if transcription else []

        mumble_block = "\n".join(f"- {l}" for l in raw_lines) or "- (none)"

        # --- dynamic temperature --------------------------------------------
        temp = TEMPERATURE_FREE if CREATIVE_MODE else TEMPERATURE_SAFE

        # --- prompt ----------------------------------------------------------
        prompt = f"""
You are Mumblr, an AI lyric‑finisher.

### Raw takes
{mumble_block}

### Requirements
1. Preserve each line’s core **consonant/vowel skeleton** so it can
   still be sung over the user’s melody.  
2. **Enhance** word‑choice – vivid imagery, metaphor, internal rhyme.
3. You may change tenses, add small fillers (“oh”, “yeah”), swap
   synonyms **but keep the line length within ±1 syllables**.
4. Return **exactly {len(raw_lines)} numbered lines**, nothing else.

### Context
Mood   : {mood or '(none)'}
Section: {section or '(none)'}
Story  : {story or '(none)'}
"""

        resp = client.chat.completions.create(
            model       = MODEL,
            messages    = [
                {"role": "system", "content": "You output lyrics only."},
                {"role": "user",   "content": prompt},
            ],
            temperature = temp,
            seed        = SEED,
        )

        lyrics = resp.choices[0].message.content.strip()
        return lyrics, 200, {"Content-Type": "text/plain"}

    except Exception as e:
        return {"error": str(e)}, 500
# ────────────────────────────────────────────────────────────────
