"""
Mumblr backend – Flask + OpenAI (SDK ≥ 1.0)

Make sure your Render service has an environment variable:
    OPENAI_API_KEY = sk-…             # your secret key
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os

# ---------------------------------------------------------------------
# Flask setup
# ---------------------------------------------------------------------
app = Flask(__name__)
CORS(app)  # allow all domains (frontend will work locally or on Netlify, Vercel, etc.)

# ---------------------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------------------
# System prompt the model always sees
# ---------------------------------------------------------------------
SYSTEM_PROMPT = """
Mumblr expects input fields such as:
• transcription – user’s sung or spoken line  
• mood – e.g. “❤️ Breakup & Heartbreak”  
• section – Verse / Chorus / Bridge  
• story – optional narrative context

Return **lyrics only** (no commentary) that match the requested mood, section,
and story.  Keep rhyme and syllable flow appropriate to modern pop songs.
"""

# ---------------------------------------------------------------------
# Health-check / root route
# ---------------------------------------------------------------------
@app.get("/")
def home():
    return "🎵 Mumblr API is live!"

# ---------------------------------------------------------------------
# Main generation route
# ---------------------------------------------------------------------
@app.post("/mumblr")
def generate_lyrics():
    try:
        data = request.get_json(force=True)  # force=True → 400 if not JSON

        transcription = data.get("transcription", "")
        mood          = data.get("mood", "")
        section       = data.get("section", "")
        story         = data.get("story", "")

        # Build the user prompt
        prompt = (
            f"🧠 Mood: {mood}\n"
            f"Section: {section}\n"
            f"Story: {story}\n"
            f"Transcribed line: {transcription}\n\n"
            "Write finished lyrics only, no explanation."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",            # or "gpt-4o" / "gpt-4-turbo"
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.8,
            timeout=60,                     # seconds – optional
        )

        lyrics = response.choices[0].message.content.strip()
        return lyrics, 200, {"Content-Type": "text/plain"}

    except Exception as err:
        # Log the error to Render logs and return JSON so the frontend sees something useful
        app.logger.exception("Error in /mumblr")
        return jsonify(error=str(err)), 500

# ---------------------------------------------------------------------
# Run locally (Render ignores this block, but it’s handy for local testing)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
