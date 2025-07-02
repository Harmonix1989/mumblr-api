# ─────────────────────────────────── app.py ────────────────────────────────────
"""
Mumblr backend  –  Flask  +  openai-python ≥ 1.4

▸ Accepts POST /mumblr with JSON:
      {
        transcription : str      (ignored if "recordings" array supplied)
        mood          : str      ("Breakup & Heartbreak", …)
        section       : str      ("Verse", "Chorus", …)
        story         : str      (optional free-text context)
        recordings    : list[str]  ← array of raw phrases from Lovable
      }

▸ Returns **plain-text lyrics** – exactly one polished line for each raw line.

▸ CORS enabled so any origin (Lovable preview, local dev, etc.) can call it.

Set these in Render ► **Environment** (add new key / value rows):
    OPENAI_API_KEY=<your key>
    TEMPERATURE=0.7          # optional, default 0.7
    OPENAI_MODEL=gpt-4o-mini # or gpt-4o, gpt-4-turbo, etc.
    SEED=42                  # optional, for deterministic output
"""

from __future__ import annotations

import os
from typing import Any, List

from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI, OpenAIError

# ── configuration ──────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE    = float(os.getenv("TEMPERATURE", "0.7"))
SEED_STR       = os.getenv("SEED")
SEED           = int(SEED_STR) if SEED_STR else None

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in environment")

# ── system prompt ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are Mumblr — an AI lyric-finisher for songwriters.

When you receive JSON you will be given:
  • “recordings” – an array of raw sung or spoken phrases   (list[str])
  • “mood”       – e.g. Breakup & Heartbreak, Party & Celebration, …
  • “section”    – Verse, Chorus, Bridge, etc.
  • “story”      – OPTIONAL extra context

Your task:
1. Produce **exactly one polished lyric line PER recording** – same order.
2. Preserve each line’s core nouns & verbs (recognisable to the singer).
3. Improve rhyme, rhythm, and grammar.  Small fillers allowed (“oh”, “yeah”).
4. Do **NOT** merge two source lines together or split one apart.
5. Output MUST be plain text, numbered **1. … 2. …** with no other commentary.

Return nothing else.
"""

# ── OpenAI client ─────────────────────────────────────────────────────────
client = OpenAI(api_key=OPENAI_API_KEY)

# ── Flask app ─────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)   # allow all origins


@app.get("/")
def health() -> tuple[str, int]:
    """Simple health-check route so Render shows ‘Healthy’."""
    return "Mumblr API is live!", 200


@app.post("/mumblr")
def mumblr() -> tuple[Any, int, dict[str, str]]:
    """Generate lyric lines from raw ‘recordings’ (or single transcription)."""
    try:
        data = request.get_json(force=True) or {}

        # 1️⃣ Gather raw lines -------------------------------------------------
        recordings: List[str] = [
            str(x).strip() for x in data.get("recordings", []) if str(x).strip()
        ]
        transcription = str(data.get("transcription", "")).strip()
        if not recordings and transcription:
            recordings = [transcription]

        if not recordings:
            return (
                jsonify({"error": "No recordings / transcription provided."}),
                400,
                {"Content-Type": "application/json"},
            )

        mumble_block = "\n".join(f"- {line}" for line in recordings)

        # 2️⃣ Build user prompt ----------------------------------------------
        mood    = str(data.get("mood", "")).strip()
        section = str(data.get("section", "")).strip()
        story   = str(data.get("story", "")).strip() or "(none)"

        user_prompt = f"""
### Raw takes
{mumble_block}

### Context
Mood:    {mood}
Section: {section}
Story:   {story}

### Instructions
Finish each raw take into a polished lyric line following the Requirements.
Return exactly {len(recordings)} numbered lines, nothing else.
""".strip()

        # 3️⃣ Call OpenAI -----------------------------------------------------
        chat_args = dict(
            model        = OPENAI_MODEL,
            temperature  = TEMPERATURE,
            messages     = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
        )
        if SEED is not None:
            chat_args["seed"] = SEED  # deterministic

        resp = client.chat.completions.create(**chat_args)
        lyrics = resp.choices[0].message.content.strip()

        return lyrics, 200, {"Content-Type": "text/plain"}

    except OpenAIError as oe:
        return (
            jsonify({"error": f"OpenAI API error: {oe}"}),
            502,
            {"Content-Type": "application/json"},
        )
    except Exception as e:
        return (
            jsonify({"error": f"Server error: {e}"}),
            500,
            {"Content-Type": "application/json"},
        )


# ── run locally (Render uses gunicorn, so this block is ignored there) ────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
