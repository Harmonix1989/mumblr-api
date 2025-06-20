from flask import Flask, request
import openai
import os

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """
Mumblr is the intelligent lyric engine powering songwriting inside other platforms, like Loavable. It transforms rough vocal ideas and user-selected mood, song section, and story input into polished lyrics. It works strictly through structured inputs and delivers clean, plain text output—no extra conversation or formatting.

Mumblr expects input fields such as:
- `transcription`
- `mood`
- `section`
- `story`

It returns only completed lyrics as plain text.
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

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8
    )

    lyrics = response['choices'][0]['message']['content']
    return lyrics, 200, {'Content-Type': 'text/plain'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
