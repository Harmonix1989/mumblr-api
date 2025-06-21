from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os

# Set up the OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the Flask app and enable CORS
app = Flask(__name__)
CORS(app)  # Enables CORS for all routes

# System prompt that guides GPT's behavior
SYSTEM_PROMPT = """
Mumblr expects input fields such as:
- ‘transcription’: a phrase or line captured from the user’s vocal input.
- ‘mood’: selected emotional tone, e.g., ❤️ Breakup & Heartbreak.
- ‘section’: song part–Verse, Chorus, or Bridge.
- ‘story’: optional context or narrative to guide lyric development.

It returns **only completed lyrics as plain text**, crafted to match the mood, song section, and provided context. Lyrics retain rhyme and syllabic structure appropriate to the selected section.

Mumblr assumes no UI context—it acts as a backend service, producing high-quality lyrics based solely on the inputs it receives.
"""

# Define the root endpoint to verify the service is running
@app.route("/")
def home():
    return "Mumblr API is live!"

# Define the POST endpoint for lyric generation
@app.route("/mumblr", methods=["POST"])
def generate_lyrics():
    data = request.get_json()
    transcription = data.get("transcription", "")
    mood = data.get("mood", "")
    section = data.get("section", "")
    story = data.get("story", "")

    # Construct the user prompt based on inputs
    prompt = f"""🧠Mood: {mood}
Section: {section}
Story: {story}
Transcribed Line: {transcription}
Write lyrics only, no explanation."""

    # Generate lyrics using OpenAI's ChatCompletion
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8
    )

    lyrics = response["choices"][0]["message"]["content"]

    # Return the result as JSON
    return jsonify({"lyrics": lyrics}), 200

# Run the Flask app locally
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
