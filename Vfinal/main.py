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
        self.router = IntentRouter()  # loads SentenceTransformer once here
        self.speech = CareMateSpeech()
        
        # Database Connection
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client["caremate_db"]
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=6)
        
        # Pre-warm the crew router singleton so first request is fast
        try:
            from caremate_crew import route_intent as _warm
            _warm("hello")
            logger.info("CrewAI intent router pre-warmed")
        except Exception as e:
            logger.warning(f"Crew pre-warm skipped: {e}")

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
        
        # process_input returns (response_text, intent) tuple or just string
        if isinstance(result_en, tuple):
            result_en, classified_intent = result_en
        else:
            classified_intent = None
        
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
            "language": original_lang,
            "intent": classified_intent,  # pass intent up to api.py for WebSocket routing
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
        """
        Architecture flow per spec:
          1. Emergency Detection  (deterministic, before AI)
          2. Intent Routing       (deterministic SVM, not a tool)
          3. Cache check          (skip crew for repeated queries)
          4. CrewAI pipeline      (Patient Agent → Central Agent)
          5. Fallback             (direct logic if crew fails)
        Returns: tuple (response_text: str, intent: str)
        """
        logger.info(f"Processing: '{user_input}' (lang={original_lang})")

        # ── LAYER 1: Emergency Detection (deterministic, zero AI overhead) ──
        from caremate_crew import detect_emergency, route_intent, run_caremate_crew

        is_emergency = detect_emergency(user_input)
        if is_emergency:
            logger.critical("EMERGENCY DETECTED — triggering immediate alert")
            try:
                from hospital_tools import WorkflowActionTool
                WorkflowActionTool()._run(
                    patient_id=patient_id,
                    request_type="EMERGENCY",
                    request_text=user_input,
                    category="CRITICAL"
                )
            except Exception as e:
                logger.error(f"Emergency workflow error: {e}")
            return ("EMERGENCY ALERT TRIGGERED! Help is on the way. Please stay calm.", "emergency")

        # ── LAYER 2: Intent Routing (deterministic SVM, not a tool) ──
        classification = route_intent(user_input)
        intent = classification["intent"]
        confidence = classification["confidence"]
        logger.info(f"Intent: {intent.upper()} ({confidence:.2f})")

        # ── LAYER 3: Cache check ──
        cached = optimizer.get_cached_response(user_input, intent)
        if cached:
            # Reject cached junk responses (underscores, too short, etc.)
            is_junk = (
                len(cached) < 5
                or all(c in '_ -.\n' for c in cached)
                or cached.count('_') > 5
            )
            if not is_junk:
                logger.info("Cache hit — skipping crew")
                return (cached, intent)
            else:
                logger.warning(f"Stale/junk cache entry for '{user_input[:30]}' — reprocessing")
                # Remove the bad entry
                cache_key = optimizer._get_cache_key(user_input, intent)
                optimizer.response_cache.pop(cache_key, None)

        # ── LAYER 4: CrewAI pipeline ──
        try:
            logger.info(f"[CrewAI] Launching agents (intent={intent})...")
            response = run_caremate_crew(
                patient_query=user_input,
                patient_id=patient_id,
                intent=intent,
                is_emergency=False,
            )
            if response and isinstance(response, str) and len(response) > 4:
                optimizer.cache_response(user_input, intent, response)
                return (response, intent)
            logger.warning("[CrewAI] Empty/invalid response — falling back")
        except Exception as e:
            logger.error(f"[CrewAI] Failed: {e} — falling back")

        # ── LAYER 5: Fallback (direct logic) ──
        return (self._direct_process(user_input, patient_id, intent), intent)

    def _direct_process(self, user_input: str, patient_id: str, intent: str) -> str:
        """Direct processing fallback — keeps system working if CrewAI fails. Returns response string only."""
        from hospital_tools import WorkflowActionTool

        if intent in ["nurse_request", "nutrition_request", "utility_request"]:
            try:
                WorkflowActionTool()._run(
                    patient_id=patient_id, request_type=intent,
                    request_text=user_input, category="general"
                )
                response = generate_openrouter_response(
                    f"Patient requested: '{user_input}'. Confirm briefly:", max_tokens=30
                )
                return response or "Your request has been received. The team will assist you shortly."
            except Exception as e:
                logger.error(f"Workflow fallback error: {e}")
                return "Your request has been received. The appropriate team will assist you shortly."

        if intent in ["doctor_query", "status_query"]:
            try:
                WorkflowActionTool()._run(
                    patient_id=patient_id, request_type="doctor_query",
                    request_text=user_input, category="HIGH"
                )
            except Exception:
                pass
            return "Your question has been sent to your doctor. They will respond to you shortly."

        return self._get_conversational_fallback(user_input.lower())

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
