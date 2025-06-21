from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os

# Get API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app)  # Allow requests from frontend

# System prompt for the assistant
SYSTEM_PROMPT = """
Mumblr expects input fields such as:
- ‘transcription’: a phrase or line captured from the user’s vocal input.
- ‘mood’: selected emotional tone, e.g., ❤️ Breakup & Heartbreak.
- ‘section’: song part–Verse, Chorus, or Bridge.
- ‘story’: optional context or narrative to guide lyric development.

It returns **only completed lyrics as plain text**, crafted to match the mood, song section, and provided context. Lyrics retain rhyme and syllabic structure appropriate to the selected section.

Mumblr assumes no UI context—it acts as a backend service, producing high-quality lyrics based solely on the inputs it receives.
"""

@app.route("/")
def home():
    return "Mumblr API is live!"

@app.route("/mumblr", methods=["POST"])
def generate_lyrics():
    try:
        data = request.get_json()

        transcription = data.get("transcription", "")
        mood = data.get("mood", "")
        section = data.get("section", "")
        story = data.get("story", "")

        prompt = f"""🧠Mood: {mood}
Section: {section}
Story: {story}
Transcribed Line: {transcription}
Write lyrics only, no explanation."""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8
        )

        lyrics = response["choices"][0]["message"]["content"]
        return jsonify({"lyrics": lyrics})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
