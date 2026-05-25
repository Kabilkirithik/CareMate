from crewai.tools import BaseTool
from sarvamai import SarvamAI
import os
from dotenv import load_dotenv

# load env variables
load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")


class STTTool(BaseTool):
    name: str = "Speech To Text Tool"
    description: str = "Convert patient speech audio into English text."

    def _run(self, audio_file_path: str) -> str:

        client = SarvamAI(
            api_subscription_key=SARVAM_API_KEY
        )

        with open(audio_file_path, "rb") as audio_file:

            response = client.speech_to_text.translate(
                file=audio_file,
                model="saaras:v3"
            )

        transcript = response.transcript

        return transcript