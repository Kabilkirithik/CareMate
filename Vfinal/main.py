import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from intent_router import IntentRouter
from speech_layer import CareMateSpeech
from openrouter_client import generate_openrouter_response
from pymongo import MongoClient
from dotenv import load_dotenv
from performance_optimizer import optimizer

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class CareMateBackend:
    def __init__(self):
        logger.info("Initializing CareMate AI Backend...")
        self.router = IntentRouter()
        self.speech = CareMateSpeech()
        
        # Database Connection
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client["caremate_db"]
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=6)

    async def process_voice_input_async(self, audio_file_path: str, patient_id: str):
        """Async version of voice processing with parallel execution"""
        loop = asyncio.get_event_loop()
        
        # 1. Speech to Text (Any language to English for AI)
        stt_result = await loop.run_in_executor(self.executor, self.speech.stt, audio_file_path)
        if "error" in stt_result:
            return {"error": f"STT failed: {stt_result['error']}"}
        
        text_input = stt_result['english']
        original_lang = stt_result['language']
        
        # 2. Check for instant responses first (ultra-fast path)
        instant_response = optimizer.get_instant_response(text_input, "")
        if instant_response:
            logger.info("Using instant response - ultra-fast path")
            
            # Start translation and TTS in parallel if needed
            if original_lang != "en":
                translation_task = loop.run_in_executor(
                    self.executor, self.speech.translate_text, instant_response, original_lang
                )
                result_final = await translation_task
                audio_task = loop.run_in_executor(
                    self.executor, self.speech.tts, result_final, original_lang
                )
                audio_response_path = await audio_task
            else:
                result_final = instant_response
                audio_response_path = await loop.run_in_executor(
                    self.executor, self.speech.tts, result_final, "en"
                )
            
            return {
                "transcript": text_input,
                "response_text": result_final,
                "response_audio": audio_response_path,
                "language": original_lang
            }
        
        # 3. Process via AI logic with caching
        result_en = await loop.run_in_executor(
            self.executor, self.process_input, text_input, patient_id, original_lang
        )
        
        # Guard: ensure result_en is always a valid string
        if not result_en or not isinstance(result_en, str):
            logger.error(f"process_input returned None or invalid for: '{text_input}'")
            result_en = "I received your message and will ensure the appropriate team is notified."
        
        # 4. Handle Multi-lingual Response via Speech Layer (parallel)
        if original_lang != "en":
            logger.info(f"Translating response to {original_lang}...")
            
            translation_task = loop.run_in_executor(
                self.executor, self.speech.translate_text, result_en, original_lang
            )
            result_final = await translation_task
            
            # Guard: ensure translation returned a valid string
            if not result_final or not isinstance(result_final, str):
                result_final = result_en
            
            audio_task = loop.run_in_executor(
                self.executor, self.speech.tts, result_final, original_lang
            )
            audio_response_path = await audio_task
        else:
            result_final = result_en
            audio_response_path = await loop.run_in_executor(
                self.executor, self.speech.tts, result_final, "en"
            )
        
        if not audio_response_path:
            logger.error("Voice response generated text but no audio file could be produced.")
        
        return {
            "transcript": text_input,
            "response_text": result_final,
            "response_audio": audio_response_path,
            "language": original_lang
        }

    def process_voice_input(self, audio_file_path: str, patient_id: str):
        """Synchronous wrapper for voice processing"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.process_voice_input_async(audio_file_path, patient_id))
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            return {"error": str(e)}
        finally:
            loop.close()

    def process_input(self, user_input: str, patient_id: str, original_lang: str = "en"):
        """Processes text input with multi-model routing and optimizations."""
        logger.info(f"Processing Query: '{user_input}' (Inferred Lang: {original_lang})")
        
        # 1. Intent Classification (SVM Model)
        classification = self.router.classify(user_input)
        intent = classification['intent']
        confidence = classification['confidence']
        
        logger.info(f"Routed Intent: {intent.upper()} (Confidence: {confidence:.2f})")

        # Check cache first for non-emergency intents
        if intent != "emergency":
            cached_response = optimizer.get_cached_response(user_input, intent)
            if cached_response:
                logger.info("Using cached response")
                return cached_response

        from hospital_tools import WorkflowActionTool

        # --- PATH 1: EMERGENCY (INSTANT) ---
        if intent == "emergency":
            logger.info("CRITICAL: EMERGENCY DETECTED.")
            try:
                wf_tool = WorkflowActionTool()
                wf_tool._run(patient_id=patient_id, request_type="EMERGENCY", request_text=user_input, category="CRITICAL")
                msg = "EMERGENCY ALERT TRIGGERED! Help is on the way. Please stay calm."
                return msg # Voice loop will translate if needed
            except Exception as e:
                logger.error(f"Emergency Error: {e}")
                return "EMERGENCY ALERT TRIGGERED!"

        # --- PATH 2: FAST PATH (CONVERSATIONAL via Meditron) ---
        if intent == "general_conversation":
            logger.info("Decision: Handling via Meditron Fast Path...")
            try:
                from meditron_client import MeditronClient
                m_client = MeditronClient()
                
                user_lower = user_input.lower()
                
                # Build a very strict, structured prompt for Meditron
                prompt = (
                    "You are CareMate, a hospital bedside assistant. "
                    "A patient said: \"{input}\". "
                    "Respond with ONE short, kind sentence (max 12 words). "
                    "Do NOT ask questions about staff or hospital operations. "
                    "Only respond to the patient's emotional or comfort needs.\n"
                    "CareMate response:"
                ).format(input=user_input)
                
                response = m_client.generate_response(prompt, max_tokens=40, temperature=0.2)
                
                # Extract only the part after "CareMate response:"
                clean_response = response.strip()
                if "CareMate response:" in clean_response:
                    clean_response = clean_response.split("CareMate response:")[-1].strip()
                
                # ✅ KEY FIX: Take only the FIRST sentence — Meditron always hallucinates after it
                import re
                # Split on sentence endings OR newlines OR scenario markers
                first_sentence = re.split(r'(?<=[.!?])["\s]|\n|###|##|\*\*', clean_response)[0]
                clean_response = first_sentence.strip().strip('"').strip("'").strip()
                
                # Remove markdown artifacts like "###", "**", "##"
                clean_response = re.sub(r'[#*]+', '', clean_response).strip()
                
                # Validate: reject if it still looks like hallucination
                hallucination_signals = [
                    "how long did you work",
                    "hospital before becoming",
                    "patient said",
                    "caremate said",
                    "you are caremate",
                    "respond with",
                    "do not ask",
                    "max 12 words",
                    "scenario",
                    "assistant introduces",
                ]
                
                is_hallucination = (
                    len(clean_response) < 4
                    or clean_response.lower() == user_input.lower()
                    or any(signal in clean_response.lower() for signal in hallucination_signals)
                )
                
                if is_hallucination:
                    logger.warning(f"Meditron hallucination detected: '{clean_response}' — using keyword fallback")
                    clean_response = self._get_conversational_fallback(user_lower)
                
                final_response = clean_response.strip()
                optimizer.cache_response(user_input, intent, final_response)
                return final_response
                
            except Exception as e:
                logger.error(f"Fast Path Error: {e}")
                return self._get_conversational_fallback(user_input.lower())

        # --- PATH 3: ZERO-LOOP WORKFLOW (Logistics via Nemotron) ---
        workflow_intents = ["nurse_request", "nutrition_request", "utility_request"]
        if intent in workflow_intents:
            logger.info(f"Decision: Handling {intent} via Nemotron Zero-Loop...")
            try:
                wf_tool = WorkflowActionTool()
                category = "water" if "water" in user_input.lower() else "general"
                wf_tool._run(patient_id=patient_id, request_type=intent, request_text=user_input, category=category)
                
                prompt = f"Patient requested: '{user_input}'. Confirm briefly:"
                response = generate_openrouter_response(prompt, max_tokens=30)
                
                # Guard against None
                if not response or not isinstance(response, str):
                    response = "Your request has been received. The appropriate team will assist you shortly."
                
                optimizer.cache_response(user_input, intent, response)
                return response
            except Exception as e:
                logger.error(f"Workflow Error: {e}")
                return "Your request has been received. The appropriate team will assist you shortly."

        # --- PATH 4: MEDICAL QUERIES → Route to Doctor Dashboard, don't answer ---
        medical_intents = ["status_query", "doctor_query"]
        if intent in medical_intents:
            logger.info(f"Decision: Medical query — routing to doctor dashboard, not answering.")
            
            # Just acknowledge and log — the doctor dashboard will show this
            acknowledgements = {
                "doctor_query": "Your question has been sent to your doctor. They will respond to you shortly.",
                "status_query": "I've forwarded your query to your doctor. They will review your records and get back to you soon.",
            }
            response = acknowledgements.get(intent, "Your query has been sent to the medical team. Please wait for a response.")
            
            optimizer.cache_response(user_input, intent, response)
            return response

        # FALLBACK — should never reach here, but safety net
        fallback_response = "I have received your message and am looking into it. Please wait a moment."
        optimizer.cache_response(user_input, intent, fallback_response)
        return fallback_response

    def _get_conversational_fallback(self, user_lower: str) -> str:
        """Keyword-based fallback for general conversation when Meditron hallucinates."""
        if any(w in user_lower for w in ["bored", "boring"]):
            return "I understand you're feeling bored. I'm here with you — is there anything I can help with?"
        if any(w in user_lower for w in ["sing", "song", "music"]):
            return "I can't sing, but I hope your recovery goes smoothly and you feel better soon!"
        if any(w in user_lower for w in ["tired", "exhausted", "sleepy"]):
            return "Rest is very important for your recovery. I hope you feel better soon."
        if any(w in user_lower for w in ["hello", "hi", "hey"]):
            return "Hello! I'm CareMate, your hospital assistant. How can I help you today?"
        if any(w in user_lower for w in ["thank", "thanks"]):
            return "You're very welcome! I'm always here to help you."
        if any(w in user_lower for w in ["lonely", "alone"]):
            return "I'm here with you. The medical team is also nearby if you need anything."
        if any(w in user_lower for w in ["scared", "afraid", "worried"]):
            return "It's okay to feel that way. The medical team is taking good care of you."
        if any(w in user_lower for w in ["happy", "good", "great", "fine"]):
            return "That's wonderful to hear! Keep up the positive spirit — it helps recovery."
        return "I'm here to support you. Let me know if there's anything you need."

if __name__ == "__main__":
    backend = CareMateBackend()
    print("Backend logic initialized.")
