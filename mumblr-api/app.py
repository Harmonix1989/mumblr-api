from flask import Flask, request
import openai
import os

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """
Mumblr is the intelligent lyric engine powering songwriting inside other platforms, like Loavable. It transforms rough vocal ideas and user-selected mood, song section, and story input into polished lyrics. It works strictly through structured inputs and delivers clean, plain text output—no extra conversation or formatting.

Mumblr expects input fields such as:
- `transcription`: a phrase or line captured from the user's vocal input.
- `mood`: selected emotional tone, e.g., 💔 Breakup & Heartbreak.
- `section`: song part—Verse, Chorus, or Bridge.
- `story`: optional context or narrative to guide lyric development.

It returns **only completed lyrics as plain text**, crafted to match the mood, song section, and provided context. Lyrics retain rhyme and syllabic structure appropriate to the selected section.

Mumblr assumes no UI context—it acts as a backend service, producing high-quality lyrics based solely on the inputs it receives.
"""

@app.route('/mumblr', methods=['POST'])
def generate_lyrics():
    data = request.get_json()
    transcription = data.get('transcription', '')
    mood = data.get('mood', '')
    section = data.get('section', '')
    story = data.get('story', '')

    prompt = f"""Mood: {mood}
Section: {section}
Story: {story}
Transcribed Line: {transcription}
Write lyrics only, no explanation."""

    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8
    )

    lyrics = resp['choices'][0]['message']['content']
    return lyrics, 200, {'Content-Type': 'text/plain'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
