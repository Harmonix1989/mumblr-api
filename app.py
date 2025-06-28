# ───────────────────────────── app.py ──────────────────────────────
"""
Mumblr backend (Flask + openai-python ≥ 1.4)

• CORS enabled – any front-end can call it
• Optional deterministic SEED (set SEED in Render env)
• Health-check at “/”
"""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI, OpenAIError

# ── configuration ────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # set in Render → Environment
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
SEED = int(os.getenv("SEED")) if os.getenv("SEED") else None

SYSTEM_PROMPT = """
Mumblr expects JSON with keys:
  • transcription – line captured from the user’s vocal take
  • mood          – Breakup & Heartbreak, Party & Celebration, etc.
  • section       – Verse, Chorus, or Bridge
  • story         – OPTIONAL extra context

Return **lyrics only** (plain text).  Keep rhyme & syllable flow.
"""

# ── OpenAI client ────────────────────────────────────────────────
client = OpenAI(api_key=OPENAI_API_KEY)

# ── Flask app ────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # allow any Origin (*) by default


@app.get("/")
def home() -> tuple[str, int]:
    """Render health check."""
    return "Mumblr API is live!", 200


@app.post("/mumblr")
def generate_lyrics() -> tuple[Any, int, dict[str, str]]:
    """
    POST JSON:
        {
          "transcription": "hey sugar what did you do",
          "mood": "Struggle",
          "section": "Verse",
          "story": "...",
          "recordings": ["line1", "line2", ...]   # ← optional list
        }
    """
    try:
        data = request.get_json(force=True) or {}

        transcription = str(data.get("transcription", "")).strip()
        mood = str(data.get("mood", "")).strip()
        section = str(data.get("section", "")).strip()
        story = str(data.get("story", "")).strip()

        # ---------- build prompt (inside the function!) -------------
        recordings = data.get("recordings", [])

        if isinstance(recordings, list) and recordings:
            raw_lines = [str(x).strip() for x in recordings if x]
            mumble_block = "\n".join(f"- {l}" for l in raw_lines)
        else:  # fallback for single-line calls
            raw_lines = [transcription]
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
        # ---------- end prompt build --------------------------------

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
            seed=SEED,  # None → natural randomness
        )

        lyrics = response.choices[0].message.content
        return lyrics, 200, {"Content-Type": "text/plain"}

    except OpenAIError as oe:
        return jsonify(error=str(oe)), 500
    except Exception as e:  # any other failure
        return jsonify(error=str(e)), 500


# ─────────────────── run locally (ignored by Gunicorn) ───────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
