# ─────────────────────────── app.py (FULL FILE) ────────────────────────────
"""
Mumblr backend — Flask  +  openai-python ≥ 1.4

✓ Uses the new OpenAI client (openai.ChatCompletion is deprecated).
✓ CORS enabled so any front-end (Lovable, local dev, etc.) can call it.
✓ Optional deterministic seed – set SEED=42 (or any int) in Render “Environment”.
✓ Health-check route at “/” so Render shows the service as “Healthy”.
"""

from __future__ import annotations

import os
from typing import Any, List

from flask import Flask, request
from flask_cors import CORS
from openai import OpenAI, OpenAIError

# ── configuration ──────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")           # set in Render → Environment
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE    = float(os.getenv("TEMPERATURE", "0.7"))
SEED           = int(os.getenv("SEED", "0")) if os.getenv("SEED") else None

SYSTEM_PROMPT = """
Mumblr expects JSON with these keys:
  • recordings    – list[str] of raw sung / spoken lines            (preferred)
      OR
    transcription – single line fallback when only one line exists
  • mood          – Breakup & Heartbreak, Party & Celebration, etc.
  • section       – Verse, Chorus, or Bridge
  • story         – OPTIONAL extra context

Response must be **lyrics only**, plain text, no commentary.
Keep each line’s core words, improve rhyme & rhythm, same syllabic flow.
Return exactly the same number of lines you receive.
"""

# ── OpenAI client ──────────────────────────────────────────────────────────
client = OpenAI(api_key=OPENAI_API_KEY)

# ── Flask app ──────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)                       # allow any Origin (*) by default


@app.get("/")
def home() -> tuple[str, int]:
    """Health-check route so Render marks service healthy."""
    return "Mumblr API is live!", 200


@app.post("/mumblr")
def generate_lyrics() -> tuple[Any, int, dict[str, str]]:
    """Finish the raw ‘mumbles’ into polished lyrics."""
    try:
        data = request.get_json(force=True) or {}

        # 1️⃣  Prefer the array of lines; fall back to a single string
        recordings: List[str] = data.get("recordings") or []
        if not recordings:                             # legacy / single-line clients
            single = str(data.get("transcription", "")).strip()
            if single:
                recordings = [single]

        mood    = str(data.get("mood", "")).strip()
        section = str(data.get("section", "")).strip()
        story   = str(data.get("story", "")).strip()

        # ── build prompt ────────────────────────────────────────────────
        mumble_block = "\n".join(f"- {line.strip()}" for line in recordings)

        prompt = f"""
You are Mumblr, an AI lyric-finisher.

### Raw takes
{mumble_block}

### Requirements
1. Keep **each line’s core words**.
2. Improve rhyme & rhythm; you may adjust tense or add small fillers
   (“oh”, “yeah”) **but don’t drop or replace the key nouns/verbs**.
3. Return **exactly** {len(recordings)} numbered lines, nothing else.

### Context
Mood:  {mood or '(none)'}
Part:  {section or '(none)'}
Story: {story or '(none)'}
""".strip()

        # ── call ChatGPT ────────────────────────────────────────────────
        chat_args = dict(
            model       = OPENAI_MODEL,
            messages    = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature = TEMPERATURE,
        )
        if SEED is not None:                     # deterministic option
            chat_args["seed"] = SEED

        resp   = client.chat.completions.create(**chat_args)
        lyrics = resp.choices[0].message.content.strip()

        return lyrics, 200, {"Content-Type": "text/plain"}

    # ── error handling ──────────────────────────────────────────────────
    except OpenAIError as oe:
        return {"error": f"OpenAI error: {oe}"}, 500
    except Exception as e:
        return {"error": f"Server error: {e}"}, 500


# ──── run locally (Render uses gunicorn via startCommand) ──────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
