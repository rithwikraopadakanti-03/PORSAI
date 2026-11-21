
import os
from dotenv import load_dotenv
from groq import Groq, APIStatusError

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError("GROQ_API_KEY is missing from .env")

client = Groq(api_key=api_key)

try:
    print("Testing Groq Orpheus TTS...")

    response = client.audio.speech.create(
        model="canopylabs/orpheus-v1-english",
        voice="hannah",
        input="Hello! I am PorsAI, your virtual salon receptionist.",
        response_format="wav"
    )

    response.write_to_file("porsai_test.wav")

    print("SUCCESS: Audio generated!")
    print("File: porsai_test.wav")

except APIStatusError as e:
    print("\nGROQ API ERROR")
    print("Status:", e.status_code)
    print("Message:", e.message)
    print("Response body:", e.response.text)

except Exception as e:
    print("\nERROR:", repr(e))
