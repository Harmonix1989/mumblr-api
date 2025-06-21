from flask import Flask, request
from flask_cors import CORS
from openai import OpenAI
import os

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ... rest of your code stays the same until the generate_lyrics function

@app.route('/mumblr', methods=['POST'])
def generate_lyrics():
    try:
        data = request.get_json()
        transcription = data.get('transcription', '')
        mood = data.get('mood', '')
        section = data.get('section', '')
        story = data.get('story', '')

        prompt = f"""🧠Mood: {mood}
Section: {section}
Story: {story}
Transcribed Line: {transcription}
Write lyrics only, no explanation."""

        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8
        )

        lyrics = resp.choices[0].message.content
        return lyrics, 200, {'Content-Type': 'text/plain'}

    except Exception as e:
        return {"error": str(e)}, 500
