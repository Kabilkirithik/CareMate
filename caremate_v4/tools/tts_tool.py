import requests
import uuid
import os
from crewai.tools import BaseTool
from langdetect import detect
from dotenv import load_dotenv

# load env variables
load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")


class TTSTool(BaseTool):
    name: str = "Text To Speech Tool"
    description: str = (
        "Converts text into speech using Sarvam AI. "
        "Automatically detects the language of the text and generates audio."
    )

    def _run(self, text: str) -> str:
        api_url = "https://api.sarvam.ai/text-to-speech/stream"

        # Detect language
        try:
            lang = detect(text)
            language_map = {
                "ta": "ta-IN",
                "en": "en-IN",
                "hi": "hi-IN",
                "te": "te-IN",
                "ml": "ml-IN",
                "kn": "kn-IN"
            }
            language_code = language_map.get(lang, "en-IN")
        except:
            language_code = "en-IN"

        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "target_language_code": language_code,
            "speaker": "gokul",
            "model": "bulbul:v3",
            "pace": 1.05,
            "speech_sample_rate": 22050,
            "output_audio_codec": "mp3",
            "enable_preprocessing": True
        }

        os.makedirs("generated_audio", exist_ok=True)

        filename = f"{uuid.uuid4()}.mp3"
        file_path = os.path.join("generated_audio", filename)

        with requests.post(api_url, headers=headers, json=payload, stream=True) as response:
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        return file_path