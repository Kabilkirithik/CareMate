import os
import uuid
import requests
import logging
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple, List, Dict
from sarvamai import SarvamAI
from langdetect import detect
from dotenv import load_dotenv
from performance_optimizer import optimizer

load_dotenv()
logger = logging.getLogger(__name__)

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

class CareMateSpeech:
    """
    High-performance Speech Layer using Sarvam AI with caching and parallel processing.
    """
    def __init__(self):
        self.api_key = SARVAM_API_KEY
        if not self.api_key:
            logger.error("SARVAM_API_KEY not found in .env")
        
        self.client = SarvamAI(api_subscription_key=self.api_key)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.audio_output_dir = os.path.join(self.base_dir, "generated_audio")
        os.makedirs(self.audio_output_dir, exist_ok=True)
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        })

    def stt(self, audio_file_path: str) -> dict:
        """
        STT with parallel translate + transcribe calls to halve latency.
        Returns: { 'english': str, 'language': str }
        """
        logger.info(f"Processing Voice Input: {audio_file_path}")

        def _translate():
            with open(audio_file_path, "rb") as f:
                return self.client.speech_to_text.translate(file=f, model="saaras:v3")

        def _transcribe():
            with open(audio_file_path, "rb") as f:
                return self.client.speech_to_text.transcribe(file=f, model="saaras:v3")

        try:
            # Run both API calls in parallel instead of sequentially
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=2) as pool:
                future_translate  = pool.submit(_translate)
                future_transcribe = pool.submit(_transcribe)

                en_res     = future_translate.result(timeout=20)
                native_res = future_transcribe.result(timeout=20)

            english_text  = en_res.transcript
            detected_lang = self._extract_language_from_response(native_res)

            logger.info(f"STT Results -> Lang: {detected_lang}, Text: {english_text[:50]}...")
            return {"english": english_text, "language": detected_lang}

        except Exception as e:
            logger.error(f"STT Pipeline Error: {e}")
            return {"error": str(e)}
    
    def _extract_language_from_response(self, native_res):
        """Extract language from Sarvam STT response"""
        native_text = native_res.transcript
        detected_lang = "en"
        
        # Try to get language metadata from Sarvam response
        native_lang_meta = None
        for key in ("language", "language_code", "lang_code"):
            try:
                native_lang_meta = getattr(native_res, key, None)
            except Exception:
                native_lang_meta = None
            if native_lang_meta:
                break
        
        if not native_lang_meta:
            try:
                native_lang_meta = native_res.get("language") or native_res.get("language_code")
            except Exception:
                native_lang_meta = None

        # Normalize any meta code (e.g. "ta-IN" -> "ta")
        if isinstance(native_lang_meta, str) and native_lang_meta.strip():
            meta_prefix = native_lang_meta.split("-")[0].strip().lower()
            lang_map = {
                "en": "en", "hi": "hi", "bn": "bn", "mr": "mr", "gu": "gu",
                "pa": "pa", "ta": "ta", "te": "te", "kn": "kn", "ml": "ml",
                "or": "od", "od": "od",
            }
            detected_lang = lang_map.get(meta_prefix, "en")
        else:
            # Fallback to langdetect
            try:
                from langdetect import detect
                lang_code = detect(native_text)
                lang_map = {
                    "en": "en", "hi": "hi", "bn": "bn", "mr": "mr", "gu": "gu",
                    "pa": "pa", "ta": "ta", "te": "te", "kn": "kn", "ml": "ml",
                    "or": "od", "od": "od",
                }
                detected_lang = lang_map.get(lang_code, "en")
            except Exception:
                detected_lang = "en"
        
        return detected_lang

    def translate_text(self, text: str, target_lang: str) -> str:
        """Translates AI response back to the patient's language with caching."""
        # Accept either "en" or "en-IN" (or other "xx-IN") as input.
        target_prefix = target_lang.split("-")[0].strip().lower()
        if target_prefix == "en":
            return text
        
        # Check cache first
        cached_translation = optimizer.get_cached_translation(text, target_lang)
        if cached_translation:
            logger.info(f"Using cached translation for {target_lang}")
            return cached_translation
            
        api_url = "https://api.sarvam.ai/translate"
        
        # Format lang for Sarvam (e.g. hi-IN, bn-IN)
        target_code = f"{target_prefix}-IN"

        payload = {
            "input": text,
            "source_language_code": "en-IN",
            "target_language_code": target_code,
            "speaker_json": "{}"
        }

        try:
            # Use session for connection reuse
            response = self.session.post(api_url, json=payload, timeout=8)  # Reduced timeout
            
            if response.status_code == 200:
                translated_text = response.json()["translated_text"]
                # Cache the translation
                optimizer.cache_translation(text, target_lang, translated_text)
                return translated_text
            else:
                logger.error(f"Translation API Error {response.status_code}: {response.text}")
                # Return original text if translation fails
                return text
                
        except Exception as e:
            logger.error(f"Translation Error: {e}")
            return text

    def tts(self, text: str, target_lang_code: str = "en-IN") -> Optional[str]:
        """
        Generates natural speech audio using Sarvam AI Bulbul:v3 with caching.
        """
        if not text or len(text.strip()) < 1:
            logger.warning("TTS skipped: Empty text input.")
            return None

        # Check cache first
        cached_audio = optimizer.get_cached_tts(text, target_lang_code)
        if cached_audio:
            logger.info(f"Using cached TTS for {target_lang_code}")
            return cached_audio

        # Standardize language codes
        SUPPORTED_TTS = ["hi-IN", "bn-IN", "kn-IN", "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN", "en-IN", "gu-IN"]
        if "-IN" not in target_lang_code:
            target_lang_code = f"{target_lang_code}-IN"
        
        if target_lang_code not in SUPPORTED_TTS:
            logger.warning(f"Unsupported TTS language {target_lang_code}. Defaulting to en-IN.")
            target_lang_code = "en-IN"

        logger.info(f"Generating TTS audio (Lang: {target_lang_code}, Text: {text[:30]}...)")
        api_url = "https://api.sarvam.ai/text-to-speech/stream"
        
        # Updated speaker mapping based on Sarvam API error message
        speaker_map = {
            "hi": "gokul",      # Hindi
            "en": "gokul",      # English  
            "ta": "kavitha",    # Tamil - use kavitha instead of valli_m
            "te": "shreya",     # Telugu
            "kn": "vidya",      # Kannada
            "ml": "priya",      # Malayalam
            "mr": "manisha",    # Marathi
            "gu": "anushka",    # Gujarati
            "bn": "ritu",       # Bengali
            "pa": "simran",     # Punjabi
            "od": "neha",       # Odia
        }
        
        lang_prefix = target_lang_code.split("-")[0].lower()
        default_speaker = speaker_map.get(lang_prefix, "gokul")
        
        attempts = [
            (target_lang_code, default_speaker),
            (target_lang_code, "gokul"),  # Fallback to gokul
            ("en-IN", "gokul"),           # Final fallback to English
        ]

        for lang_code, speaker in attempts:
            filename = f"resp_{uuid.uuid4()}.opus"
            file_path = os.path.join(self.audio_output_dir, filename)

            payload = {
                "text": text,
                "target_language_code": lang_code,
                "model": "bulbul:v3",
                "pace": 0.85,  # Slightly faster pace for quicker delivery
                "speech_sample_rate": 24000,
                "output_audio_codec": "opus",
                "enable_preprocessing": True,
            }
            if speaker:
                payload["speaker"] = speaker

            try:
                # Use session for connection reuse and reduced timeout
                with self.session.post(api_url, json=payload, stream=True, timeout=20) as response:
                    if response.status_code != 200:
                        logger.error(
                            f"Sarvam TTS API Error ({lang_code}, speaker={speaker}): "
                            f"{response.status_code} - {response.text}"
                        )
                        continue

                    with open(file_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                logger.info(f"TTS successful. Audio saved to: {file_path} (lang={lang_code}, speaker={speaker})")
                
                # Cache the result
                optimizer.cache_tts(text, target_lang_code, file_path)
                
                return file_path
            except Exception as e:
                logger.error(f"TTS Exception ({lang_code}, speaker={speaker}): {e}")
                continue

        logger.error("TTS failed after all fallback attempts.")
        return None
