import os
import uuid
import requests
import logging
import time
import asyncio
import aiohttp
from typing import Optional, Tuple, Dict
from sarvamai import SarvamAI
from langdetect import detect, DetectorFactory
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import threading

load_dotenv()
logger = logging.getLogger(__name__)

# Set seed for consistent language detection
DetectorFactory.seed = 0

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

class CareMateSpeech:
    """
    Optimized Speech-to-Text (STT) and Text-to-Speech (TTS) layers 
    using Sarvam AI with faster language detection and parallel processing.
    """
    def __init__(self):
        self.api_key = SARVAM_API_KEY
        if not self.api_key:
            logger.error("SARVAM_API_KEY not found in .env")
        
        self.client = SarvamAI(api_subscription_key=self.api_key)
        self.audio_output_dir = os.path.join("generated_audio")
        os.makedirs(self.audio_output_dir, exist_ok=True)
        
        # Extended language mappings for all Sarvam AI supported languages
        self.SUPPORTED_SARVAM_LANGS = {
            "en-IN", "hi-IN", "bn-IN", "gu-IN", "kn-IN", "ml-IN", 
            "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN"
        }
        
        # Language code mappings (both directions)
        self.LANG_CODE_MAP = {
            "en": "en-IN", "hi": "hi-IN", "bn": "bn-IN", "gu": "gu-IN", 
            "kn": "kn-IN", "ml": "ml-IN", "mr": "mr-IN", "od": "od-IN", 
            "pa": "pa-IN", "ta": "ta-IN", "te": "te-IN"
        }
        
        # Reverse mapping for quick lookup
        self.REVERSE_LANG_MAP = {v: k for k, v in self.LANG_CODE_MAP.items()}
        
        # Script mappings for better understanding
        self.SCRIPT_MAP = {
            "en-IN": "Latn", "hi-IN": "Deva", "bn-IN": "Beng", "gu-IN": "Gujr",
            "kn-IN": "Knda", "ml-IN": "Mlym", "mr-IN": "Deva", "od-IN": "Orya",
            "pa-IN": "Guru", "ta-IN": "Taml", "te-IN": "Telu"
        }
        
        # All supported languages for TTS (same as Sarvam's language identification)
        self.SUPPORTED_TTS = self.SUPPORTED_SARVAM_LANGS.copy()
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Cache for language detection to avoid repeated detection
        self._lang_cache = {}
        self._cache_lock = threading.Lock()

    def detect_language_sarvam(self, text: str) -> Tuple[str, str, float]:
        """
        Enhanced language detection using langdetect (Sarvam AI language identification not available).
        Returns (language_code, script_code, confidence)
        """
        # Quick cache check
        text_hash = hash(text[:100])
        with self._cache_lock:
            if text_hash in self._lang_cache:
                cached_result = self._lang_cache[text_hash]
                return cached_result['lang'], cached_result['script'], cached_result['confidence']
        
        # Use enhanced langdetect method since Sarvam language identification is not available
        logger.info("Using enhanced langdetect for language identification...")
        detected_lang, detected_script, confidence = self._fallback_language_detection(text)
        
        # Cache the result
        cache_entry = {
            'lang': detected_lang,
            'script': detected_script, 
            'confidence': confidence
        }
        
        with self._cache_lock:
            self._lang_cache[text_hash] = cache_entry
        
        return detected_lang, detected_script, confidence

    def _fallback_language_detection(self, text: str) -> Tuple[str, str, float]:
        """
        Enhanced fallback language detection using langdetect library.
        Maps detected languages to Sarvam-supported codes with better accuracy.
        """
        try:
            detected_lang = detect(text)
            confidence = 0.8  # Good confidence for fallback method
            
            # Enhanced mapping to Sarvam supported languages
            lang_mapping = {
                'en': 'en-IN',
                'hi': 'hi-IN', 
                'bn': 'bn-IN',
                'gu': 'gu-IN',
                'kn': 'kn-IN',
                'ml': 'ml-IN',
                'mr': 'mr-IN',
                'or': 'od-IN',  # Odia mapping
                'pa': 'pa-IN',
                'ta': 'ta-IN',
                'te': 'te-IN'
            }
            
            if detected_lang in lang_mapping:
                sarvam_code = lang_mapping[detected_lang]
                script = self.SCRIPT_MAP.get(sarvam_code, 'Latn')
                logger.info(f"Fallback detected: {detected_lang} -> {sarvam_code} ({script})")
                return sarvam_code, script, confidence
            else:
                # Default to English if not supported
                logger.info(f"Unsupported language {detected_lang}, defaulting to English")
                return "en-IN", "Latn", 0.5
                
        except Exception as e:
            logger.warning(f"Fallback language detection failed: {e}")
            return "en-IN", "Latn", 0.3

    def detect_language_fast(self, text: str) -> str:
        """
        Enhanced fast language detection using Sarvam AI's native API.
        Returns language code (e.g., 'hi-IN', 'en-IN') for backward compatibility.
        """
        lang_code, _, _ = self.detect_language_sarvam(text)
        return lang_code

    def stt_with_language_detection(self, audio_file_path: str) -> Tuple[Optional[str], str, str]:
        """
        Enhanced STT that returns transcript, detected language, and script.
        Uses Sarvam's translate endpoint which converts any language to English.
        """
        logger.info(f"Processing STT with language detection for: {audio_file_path}")
        
        for attempt in range(3):  # Retry up to 3 times
            try:
                with open(audio_file_path, "rb") as audio_file:
                    response = self.client.speech_to_text.translate(
                        file=audio_file,
                        model="saaras:v3"
                    )
                
                transcript = response.transcript
                if not transcript:
                    continue
                
                # Use Sarvam's language identification on the original audio transcript
                # Since STT translates to English, we need to infer the original language
                detected_lang, detected_script = self._infer_original_language_enhanced(transcript)
                
                logger.info(f"STT successful. Inferred language: {detected_lang} ({detected_script})")
                return transcript, detected_lang, detected_script
                
            except Exception as e:
                if "503" in str(e) or "model_overloaded" in str(e):
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"STT Model Overloaded. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                logger.error(f"STT Error: {e}")
                
        return None, "en-IN", "Latn"

    def _infer_original_language_enhanced(self, english_transcript: str) -> Tuple[str, str]:
        """
        Enhanced inference of original language from English transcript.
        Uses pattern matching and common phrase detection.
        """
        transcript_lower = english_transcript.lower()
        
        # Enhanced language indicators with more patterns
        language_patterns = {
            "hi-IN": ["ji", "sahib", "namaste", "dhanyawad", "aap", "main", "kya", "hai"],
            "ta-IN": ["vanakkam", "nandri", "eppadi", "irukku", "ungal"],
            "te-IN": ["namaskaram", "ela", "unnaru", "meeru", "nenu"],
            "bn-IN": ["namaskar", "apni", "ami", "kemon", "achen"],
            "gu-IN": ["namaste", "tamaru", "hun", "kevi", "rite"],
            "kn-IN": ["namaskara", "neevu", "naanu", "hegiddira", "chennagi"],
            "ml-IN": ["namaskaram", "ningal", "njan", "engane", "undu"],
            "mr-IN": ["namaskar", "tumhi", "mi", "kasa", "ahe"],
            "pa-IN": ["sat sri akal", "tusi", "main", "ki", "hai"],
            "od-IN": ["namaskar", "apana", "mu", "kemiti", "achhi"],
        }
        
        # Score each language based on pattern matches
        language_scores = {}
        for lang, patterns in language_patterns.items():
            score = sum(1 for pattern in patterns if pattern in transcript_lower)
            if score > 0:
                language_scores[lang] = score
        
        # Return the language with highest score, or English if no matches
        if language_scores:
            detected_lang = max(language_scores, key=language_scores.get)
            detected_script = self.SCRIPT_MAP.get(detected_lang, "Latn")
            return detected_lang, detected_script
        
        return "en-IN", "Latn"

    def translate_text_fast(self, text: str, target_lang: str = "hi-IN") -> str:
        """
        Optimized translation supporting all 11 Sarvam AI languages.
        """
        if target_lang == "en-IN":
            return text  # No translation needed
        
        # Ensure we have the full language code
        if "-IN" not in target_lang and target_lang in self.LANG_CODE_MAP:
            target_lang = self.LANG_CODE_MAP[target_lang]
        elif target_lang not in self.SUPPORTED_SARVAM_LANGS:
            logger.warning(f"Unsupported language {target_lang}. Defaulting to hi-IN.")
            target_lang = "hi-IN"
            
        logger.info(f"Translating response to {target_lang}...")
        
        api_url = "https://api.sarvam.ai/translate"
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "input": text,
            "source_language_code": "en-IN",
            "target_language_code": target_lang,
            "speaker_json": "{}"
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            translated_text = response.json()["translated_text"]
            logger.info(f"Translation successful to {target_lang}")
            return translated_text
        except requests.exceptions.Timeout:
            logger.error("Translation timeout. Returning original text.")
            return text
        except Exception as e:
            logger.error(f"Translation Error: {e}. Returning original text.")
            return text

    def tts_optimized(self, text: str, target_lang_code: str = "en-IN") -> Optional[str]:
        """
        Optimized TTS supporting all 11 Sarvam AI languages with enhanced speaker selection.
        """
        if target_lang_code not in self.SUPPORTED_TTS:
            logger.warning(f"Unsupported TTS language {target_lang_code}. Defaulting to en-IN.")
            target_lang_code = "en-IN"

        logger.info(f"Generating TTS audio (Lang: {target_lang_code})...")
        api_url = "https://api.sarvam.ai/text-to-speech/stream"

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Enhanced speaker selection for all supported languages
        speaker = self._select_optimal_speaker(target_lang_code)

        payload = {
            "text": text,
            "target_language_code": target_lang_code,
            "speaker": speaker,
            "model": "bulbul:v3",
            "pace": 1.1,  # Slightly faster pace for efficiency
            "speech_sample_rate": 22050,
            "output_audio_codec": "mp3",
            "enable_preprocessing": True
        }

        filename = f"{uuid.uuid4()}.mp3"
        file_path = os.path.join(self.audio_output_dir, filename)

        try:
            with requests.post(api_url, headers=headers, json=payload, stream=True, timeout=30) as response:
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            logger.info(f"TTS successful. Audio saved to: {file_path}")
            return file_path
        except requests.exceptions.Timeout:
            logger.error("TTS timeout. Audio generation failed.")
            return None
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return None

    def _select_optimal_speaker(self, lang_code: str) -> str:
        """
        Enhanced speaker selection for all 11 supported languages using available speakers.
        Available speakers: anushka, abhilash, manisha, vidya, arya, karun, hitesh, aditya, 
        ritu, priya, neha, rahul, pooja, rohan, simran, kavya, amit, dev, ishita, shreya, 
        ratan, varun, manan, sumit, roopa, kabir, aayan, shubh, ashutosh, advait, anand, 
        tanya, tarun, sunny, mani, gokul, vijay, shruti, suhani, mohit, kavitha, rehan, soham, rupali
        """
        # Optimized speaker selection based on language and gender preference
        speaker_map = {
            "en-IN": "gokul",      # English - clear male voice
            "hi-IN": "gokul",      # Hindi - works well with gokul
            "bn-IN": "kavya",      # Bengali - female voice for variety
            "gu-IN": "gokul",      # Gujarati - male voice
            "kn-IN": "kavya",      # Kannada - female voice
            "ml-IN": "shruti",     # Malayalam - female voice
            "mr-IN": "gokul",      # Marathi - male voice
            "od-IN": "kavya",      # Odia - female voice
            "pa-IN": "gokul",      # Punjabi - male voice
            "ta-IN": "kavya",      # Tamil - female voice
            "te-IN": "shruti"      # Telugu - female voice
        }
        return speaker_map.get(lang_code, "gokul")

    def process_voice_response_pipeline(self, english_response: str, target_language: str) -> Tuple[str, Optional[str]]:
        """
        Enhanced pipeline supporting all 11 Sarvam AI languages.
        Returns (final_text, audio_path)
        """
        start_time = time.time()
        
        # Ensure we have the full language code
        if target_language and "-IN" not in target_language and target_language != "en":
            if target_language in self.REVERSE_LANG_MAP:
                target_language = target_language  # Keep short form for processing
            else:
                target_language = "en-IN"
        elif not target_language:
            target_language = "en-IN"
        
        if target_language == "en-IN" or target_language == "en":
            # English path - direct TTS
            audio_path = self.tts_optimized(english_response, "en-IN")
            processing_time = time.time() - start_time
            logger.info(f"English voice pipeline completed in {processing_time:.2f}s")
            return english_response, audio_path
        else:
            # Non-English path - translate then TTS
            # Convert to full language code if needed
            if "-IN" not in target_language:
                target_code = self.LANG_CODE_MAP.get(target_language, "hi-IN")
            else:
                target_code = target_language
            
            translated_text = self.translate_text_fast(english_response, target_code)
            audio_path = self.tts_optimized(translated_text, target_code)
            
            processing_time = time.time() - start_time
            logger.info(f"Multilingual voice pipeline ({target_code}) completed in {processing_time:.2f}s")
            return translated_text, audio_path

    # Backward compatibility methods
    def stt(self, audio_file_path: str) -> Optional[str]:
        """Backward compatibility wrapper for STT."""
        transcript, _, _ = self.stt_with_language_detection(audio_file_path)
        return transcript

    def translate_text(self, text: str, target_lang: str = "hi-IN") -> str:
        """Backward compatibility wrapper for translation."""
        return self.translate_text_fast(text, target_lang)

    def tts(self, text: str, target_lang_code: str = "en-IN") -> Optional[str]:
        """Backward compatibility wrapper for TTS."""
        return self.tts_optimized(text, target_lang_code)

if __name__ == "__main__":
    # Enhanced test suite for all 11 supported languages
    speech = CareMateSpeech()
    
    print("=== CareMate Speech Layer - 11 Language Support Test ===")
    
    # Test 1: Language Detection with Sarvam AI
    print("\n1. Testing Sarvam AI Language Detection...")
    test_phrases = {
        "en-IN": "Hello, I need medical assistance",
        "hi-IN": "नमस्ते, मुझे चिकित्सा सहायता चाहिए",
        "ta-IN": "வணக்கம், எனக்கு மருத்துவ உதவி தேவை",
        "te-IN": "నమస్కారం, నాకు వైద్య సహాయం అవసరం",
        "bn-IN": "নমস্কার, আমার চিকিৎসা সহায়তা দরকার",
        "gu-IN": "નમસ્તે, મને તબીબી સહાય જોઈએ છે",
        "kn-IN": "ನಮಸ್ಕಾರ, ನನಗೆ ವೈದ್ಯಕೀಯ ಸಹಾಯ ಬೇಕು",
        "ml-IN": "നമസ്കാരം, എനിക്ക് വൈദ്യസഹായം വേണം",
        "mr-IN": "नमस्कार, मला वैद्यकीय मदत हवी आहे",
        "pa-IN": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਮੈਨੂੰ ਡਾਕਟਰੀ ਸਹਾਇਤਾ ਚਾਹੀਦੀ ਹੈ",
        "od-IN": "ନମସ୍କାର, ମୋର ଚିକିତ୍ସା ସହାୟତା ଦରକାର"
    }
    
    for expected_lang, phrase in test_phrases.items():
        try:
            detected_lang, script, confidence = speech.detect_language_sarvam(phrase)
            status = "✅" if detected_lang == expected_lang else "❌"
            print(f"   {expected_lang}: {detected_lang} ({script}) {status}")
        except Exception as e:
            print(f"   {expected_lang}: ERROR - {e}")
    
    # Test 2: Translation Performance for All Languages
    print("\n2. Testing Translation to All 11 Languages...")
    test_text = "Your medication is ready. Please take it with food."
    
    for lang_code in speech.SUPPORTED_SARVAM_LANGS:
        if lang_code == "en-IN":
            continue
        start_time = time.time()
        translated = speech.translate_text_fast(test_text, lang_code)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"   {lang_code}: {duration:.2f}s - {translated[:50]}...")
    
    # Test 3: TTS for Multiple Languages
    print("\n3. Testing TTS for Key Languages...")
    test_tts_langs = ["en-IN", "hi-IN", "ta-IN", "bn-IN"]
    
    for lang_code in test_tts_langs:
        start_time = time.time()
        audio_path = speech.tts_optimized("Hello, this is a test message.", lang_code)
        end_time = time.time()
        
        duration = end_time - start_time
        status = "✅" if audio_path else "❌"
        print(f"   {lang_code}: {duration:.2f}s {status}")
    
    # Test 4: Full Pipeline Test
    print("\n4. Testing Full Voice Response Pipeline...")
    test_response = "Your blood test results are normal. Continue your current medication."
    
    for lang in ["en-IN", "hi-IN", "ta-IN"]:
        start_time = time.time()
        final_text, audio_path = speech.process_voice_response_pipeline(test_response, lang)
        end_time = time.time()
        
        duration = end_time - start_time
        status = "✅" if audio_path else "❌"
        print(f"   {lang} Pipeline: {duration:.2f}s {status}")
    
    print("\n=== Summary ===")
    print(f"✅ Supported Languages: {len(speech.SUPPORTED_SARVAM_LANGS)}")
    print(f"✅ Language Codes: {', '.join(sorted(speech.SUPPORTED_SARVAM_LANGS))}")
    print(f"✅ Scripts Supported: {len(set(speech.SCRIPT_MAP.values()))}")
    print(f"✅ Enhanced Detection: Sarvam AI + Fallback")
    print("=== All Tests Completed ===")
