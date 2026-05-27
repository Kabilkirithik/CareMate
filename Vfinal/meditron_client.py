import requests
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# This URL should be updated whenever the ngrok tunnel changes
SAGEMAKER_URL = os.getenv("SAGEMAKER_URL", "https://stateless-hygroscopically-tristen.ngrok-free.dev")

class MeditronClient:
    """
    Client for interacting with the Meditron model hosted on SageMaker/Colab 
    via the ngrok tunnel.
    """
    def __init__(self, base_url: str = SAGEMAKER_URL):
        self.base_url = base_url.rstrip('/')

    def generate_response(self, prompt: str, max_tokens: int = 250, temperature: float = 0.4):
        logger.info("Sending request to Meditron (SageMaker)...")
        try:
            response = requests.post(
                f"{self.base_url}/chat",
                json={
                    "message": prompt,
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.8
                },
                timeout=180
            )
            response.raise_for_status()
            result = response.json()["response"]
            logger.info(f"Meditron Raw Response: {result[:100]}...")
            return result

        except requests.exceptions.Timeout:
            return "Error: Medical model timed out. Please try again later."
        except requests.exceptions.ConnectionError:
            return "Error: Cannot connect to the medical model server. Ensure the tunnel is active."
        except Exception as e:
            return f"Error connecting to Meditron: {str(e)}"

    def health_check(self):
        try:
            r = requests.get(f"{self.base_url}/health", timeout=10)
            return r.status_code == 200
        except:
            return False

if __name__ == "__main__":
    client = MeditronClient()
    if client.health_check():
        print("Meditron Server is ONLINE")
        print(client.generate_response("What is hypertension?"))
    else:
        print("Meditron Server is OFFLINE")
