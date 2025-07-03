# ─────────────────────────── app.py  (drop-in version) ──────────────────────────
"""
Mumblr backend — Flask + openai-python ≥ 1.4

• Works with the new OpenAI client (openai.ChatCompletion deprecated).
• Supports single-line 'transcription' or multi-line 'recordings'.
• Reads model / temperature / seed from env vars.
• CORS enabled so any front-end (Lovable, local dev) can call it.
"""

from __future__ import annotations
import os
from typing import Any, List

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI, OpenAIError

# ── configuration ───────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")            # (required)
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE    = float(os.getenv("TEMPERATURE", "0.4"))
SEED_STR       = os.getenv("SEED")                      # optional
SEED           = int(SEED_STR) if SEED_STR else None

SYSTEM_PROMPT = """
You are Mumblr, an AI lyric-finisher.

When the user sends JSON it will contain:
  • transcription – single raw line from humming/singing          (string)
  • recordings    – an array of raw lines (if provided)           (list[str])
  • mood          – e.g. Breakup & Heartbreak, Party & Celebration
  • section       – Verse, Chorus, Bridge, etc.
  • story         – OPTIONAL extra context or scene

You must:
1. Keep **each raw line’s core words** (don’t lose key nouns/verbs).
2. Improve rhyme & rhythm; you may tweak tense or add small fillers
   (“oh”, “yeah”) **but do NOT merge or drop lines**.
3. Return **exactly** the same number of numbered lines, nothing else,
   each on its own line.

Respond with lyrics **only** (no commentary, no JSON).
"""

# ── OpenAI client ───────────────────────────────────────────────────────────────
client = OpenAI(api_key=OPENAI_API_KEY)

# ── Flask setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)                                   # allow any Origin by default


@app.get("/")
def health() -> tuple[str, int]:
    """Render’s health-check route."""
    return "Mumblr API is live 🎤", 200


@app.post("/mumblr")
def generate_lyrics() -> tuple[Any, int, dict[str, str]]:
    """Generate finished lyrics from raw recordings."""
    try:
        data = request.get_json(force=True) or {}

        # ── pull fields ────────────────────────────────────────────────────────
        recordings: List[str] = data.get("recordings") or []
        transcription = str(data.get("transcription", "")).strip()
        mood          = str(data.get("mood", "")).strip()
        section       = str(data.get("section", "")).strip()
        story         = str(data.get("story", "")).strip()

        # normalise → ensure we always have a list of raw lines
        if isinstance(recordings, list) and recordings:
            raw_lines = [str(x).strip() for x in recordings if x]
        elif transcription:
            raw_lines = [transcription]
        else:
            return jsonify(error="No transcription or recordings supplied"), 400

        mumble_block = "\n".join(f"- {l}" for l in raw_lines)

        prompt = f"""
### Raw takes
{mumble_block}

### Requirements (DO NOT break these)
1. Keep each take’s core words.
2. Fix rhyme & rhythm, add tiny fillers if needed.
3. Return exactly {len(raw_lines)} numbered lines … nothing else.

### Context
Mood   : {mood or '(none)'}
Section: {section or '(none)'}
Story  : {story or '(none)'}
"""

        # ── OpenAI call ────────────────────────────────────────────────────────
        resp = client.chat.completions.create(
            model       = OPENAI_MODEL,
            messages    = [
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {"role": "user",   "content": prompt.strip()},
            ],
            temperature = TEMPERATURE,
            seed        = SEED,
        )

        lyrics = resp.choices[0].message.content.strip()
        return lyrics, 200, {"Content-Type": "text/plain"}

    except OpenAIError as oe:
        app.logger.error("OpenAI error: %s", oe)
        return jsonify(error=str(oe)), 500
    except Exception as e:
        app.logger.exception("Unexpected error")
        return jsonify(error="Server error"), 500


# ── run locally (Render ignores this when using gunicorn) ──────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5000")))
