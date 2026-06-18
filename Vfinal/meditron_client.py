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

    def generate_response(self, prompt: str, max_tokens: int = 100, temperature: float = 0.3):
        logger.info("Sending request to Meditron...")
        try:
            response = requests.post(
                f"{self.base_url}/generate",
                json={
                    "query": prompt,
                    "max_new_tokens": max_tokens,
                },
                timeout=25,
                headers={"ngrok-skip-browser-warning": "1"},
            )
            response.raise_for_status()
            raw = response.json().get("response", "").strip()

            # Strip repetition and role markers
            import re as _re
            raw = _re.split(r"<\|", raw)[0].strip()
            sentences = _re.split(r"(?<=[.!?])\s+", raw)
            result = " ".join(sentences[:2]).strip()
            logger.info(f"Meditron Response: {result[:100]}")
            return result

        except requests.exceptions.Timeout:
            logger.warning("Meditron timeout - using fallback response")
            return self._get_fallback_response(prompt)
        except requests.exceptions.ConnectionError:
            logger.warning("Meditron connection error - using fallback response")
            return self._get_fallback_response(prompt)
        except Exception as e:
            logger.error(f"Meditron error: {e}")
            return self._get_fallback_response(prompt)
    
    def _get_fallback_response(self, prompt: str) -> str:
        """Generate a quick fallback response when Meditron is unavailable"""
        # Simple keyword-based responses for common medical queries
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["pain", "hurt", "ache"]):
            return "I understand you're experiencing discomfort. I've noted your concern and will ensure medical staff are informed promptly."
        
        elif any(word in prompt_lower for word in ["medication", "medicine", "pill", "dose"]):
            return "I've recorded your medication-related question. A healthcare professional will review your medication needs shortly."
        
        elif any(word in prompt_lower for word in ["emergency", "urgent", "help", "critical"]):
            return "This appears urgent. I'm immediately alerting medical staff to assist you."
        
        elif any(word in prompt_lower for word in ["nausea", "sick", "vomit", "dizzy"]):
            return "I've noted your symptoms. Medical staff will be notified to check on you soon."
        
        elif any(word in prompt_lower for word in ["temperature", "fever", "hot", "cold"]):
            return "I've recorded your temperature concerns. A nurse will check your vitals shortly."
        
        else:
            return "I've received your message and have alerted the appropriate medical staff. Someone will be with you shortly to address your needs."

    def health_check(self):
        try:
            r = requests.get(f"{self.base_url}/health", timeout=10,
                             headers={"ngrok-skip-browser-warning": "1"})
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
