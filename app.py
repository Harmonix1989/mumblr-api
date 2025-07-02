# ─────────────────────────────────── app.py ────────────────────────────────────
"""
Mumblr backend – now with syllable-count locking
(Flask  +  openai-python ≥ 1.4)

Environment variables (Render ► Environment):
  OPENAI_API_KEY   = sk-…
  OPENAI_MODEL     = gpt-4o-mini      # or gpt-4o, gpt-4-turbo …
  TEMPERATURE      = 0.7              # optional
  SEED             = 42               # optional deterministic seed
"""
from __future__ import annotations

import os
import re
from typing import Any, List

from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI, OpenAIError

# ── config ──────────────────────────────────────────────────────────────────
API_KEY      = os.getenv("OPENAI_API_KEY", "")
MODEL        = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMP         = float(os.getenv("TEMPERATURE", "0.7"))
SEED_STR     = os.getenv("SEED")
SEED         = int(SEED_STR) if SEED_STR else None
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")

client = OpenAI(api_key=API_KEY)

# ── quick & dirty syllable counter (good enough for pop lyrics) ─────────────
_vowel_re = re.compile(r"[aeiouy]+", re.I)
def count_syllables(text: str) -> int:
    words = re.findall(r"[a-zA-Z]+", text)
    est   = 0
    for w in words:
        vowel_groups = _vowel_re.findall(w)
        if not vowel_groups:
            continue
        est += len(vowel_groups)
        # silent “e” at end of word
        if w.lower().endswith("e") and len(vowel_groups) > 1:
            est -= 1
    return max(est, 1)

# ── prompts ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are Mumblr – an AI lyric-finisher for songwriters.

You always receive:
  • recordings – array of raw sung phrases               (list[str])
  • mood       – e.g. Breakup & Heartbreak, Party…
  • section    – Verse, Chorus, Bridge…
  • story      – optional scene / back-story

Your job (for **each** raw line):
  1. Keep core words (recognisable nouns / verbs).
  2. Improve rhyme, flow, grammar – small fillers allowed (“oh”, “yeah”).
  3. **Match the syllable count shown in parentheses** (± 1 at most).
  4. Output exactly one polished line per raw line, numbered “1. … 2. …”.
  5. No extra commentary.

Return nothing except the numbered lines.
"""

# ── flask app ───────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)                      # allow any Origin


@app.get("/")
def health():
    return "Mumblr API is live!", 200


@app.post("/mumblr")
def mumblr() -> tuple[Any, int, dict[str, str]]:
    try:
        data = request.get_json(force=True) or {}

        # ── collect raw lines ────────────────────────────────────────────
        recordings: List[str] = [
            str(x).strip() for x in data.get("recordings", []) if str(x).strip()
        ]
        if not recordings:
            tx = str(data.get("transcription", "")).strip()
            if tx:
                recordings = [tx]

        if not recordings:
            return jsonify({"error": "No recordings provided."}), 400, {"Content-Type":"application/json"}

        # syllable counts & display block
        counts       = [count_syllables(l) for l in recordings]
        mumble_block = "\n".join(f"- {l}  ({c} syllables)" for l, c in zip(recordings, counts))

        # ── prompt to model ──────────────────────────────────────────────
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

### Remember
• Keep the same syllable counts shown above (± 1).
• Produce {len(recordings)} numbered lines. Only the lines – no extra text.
""".strip()

        chat_args = dict(
            model       = MODEL,
            temperature = TEMP,
            messages    = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
        )
        if SEED is not None:
            chat_args["seed"] = SEED

        resp   = client.chat.completions.create(**chat_args)
        lyrics = resp.choices[0].message.content.strip()

        return lyrics, 200, {"Content-Type": "text/plain"}

    except OpenAIError as oe:
        return jsonify({"error": f"OpenAI API error: {oe}"}), 502, {"Content-Type": "application/json"}
    except Exception as e:
        return jsonify({"error": f"Server error: {e}"}), 500, {"Content-Type": "application/json"}


if __name__ == "__main__":                 # local dev only
    app.run(host="0.0.0.0", port=5000, debug=True)
