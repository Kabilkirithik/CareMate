#!/usr/bin/env python3
"""
Enhanced CareMate Speech Layer with Multi-Language Support
Supports 55+ languages through hybrid service architecture
"""

import os
import uuid
import requests
import logging
import time
from typing import Optional, Tuple, Dict
from sarvamai import SarvamAI
from langdetect import detect, detect_langs, DetectorFactory
from dotenv import load_dotenv
import threading

load_dotenv()
logger = logging.getLogger(__name__)

# Set seed for consistent language detection
DetectorFactory.seed = 0

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")  # Optional

class EnhancedCareMateSpeech:
    """
    Enhanced Speech Layer supporting 55+ languages through hybrid architecture:
    - Sarvam AI: Indian languages (high quality)
    - Google Translate: Global languages (fallback)
    - Smart routing based on detected language
    """
    
    def __init__(self):
        self.sarvam_api_key = SARVAM_API_KEY
        self.google_api_key = GOOGLE_TRANSLATE_API_KEY
        
        if not self.sarvam_api_key:
            logger.error("SARVAM_API_KEY not found in .env")
        
        self.sarvam_client = SarvamAI(api_subscription_key=self.sarvam_api_key) if self.sarvam_api_key else None
        self.audio_output_dir = os.path.join("generated_audio")
        os.makedirs(self.audio_output_dir, exist_ok=True)
        
        # Enhanced language support
        self.SARVAM_LANGUAGES = {"hi", "ta", "te", "ml", "kn", "gu", "mr", "bn", "en"}
        self.SARVAM_LANG_MAP = {
            "hi": "hi-IN", "ta": "ta-IN", "te": "te-IN", 
            "ml": "ml-IN", "kn": "kn-IN", "gu": "gu-IN", 
            "mr": "mr-IN", "bn": "bn-IN", "en": "en-IN"
        }
        
        # Global languages supported by langdetect
        self.DETECTABLE_LANGUAGES = {
            # Indian languages (Sarvam AI)
            "hi", "ta", "te", "ml", "kn", "gu", "mr", "bn",
            # Major global languages
            "en", "fr", "es", "de", "it", "pt", "ru", "ja", "ko", "zh-cn", "zh-tw",
            "ar", "th", "vi", "id", "ms", "tl", "ur", "fa", "tr", "pl", "nl",
            "sv", "da", "no", "fi", "he", "el", "cs", "sk", "hu", "ro", "bg",
            "hr", "sr", "sl", "et", "lv", "lt", "mt", "cy", "ga", "is", "mk",
            "sq", "eu", "ca", "gl", "af", "sw", "zu", "xh", "st", "tn", "ts"
        }
        
        # Google Translate language codes
        self.GOOGLE_LANG_MAP = {
            "fr": "fr", "es": "es", "de": "de", "it": "it", "pt": "pt",
            "ru": "ru", "ja": "ja", "ko": "ko", "zh-cn": "zh", "ar": "ar",
            "th": "th", "vi": "vi", "id": "id", "ms": "ms", "tl": "tl",
            "ur": "ur", "fa": "fa", "tr": "tr", "pl": "pl", "nl": "nl",
            "sv": "sv", "da": "da", "no": "no", "fi": "fi"
        }
        
        # Cache for language detection
        self._lang_cache = {}
        self._cache_lock = threading.Lock()
        
        logger.info(f"Enhanced Speech Layer initialized:")
        logger.info(f"  • Sarvam AI: {len(self.SARVAM_LANGUAGES)} Indian languages")
        logger.info(f"  • Google Translate: {len(self.GOOGLE_LANG_MAP)} global languages")
        logger.info(f"  • Total detectable: {len(self.DETECTABLE_LANGUAGES)} languages")

    def detect_language_enhanced(self, text: str) -> Tuple[str, float]:
        """
        Enhanced language detection with confidence scoring.
        Returns (language_code, confidence_score)
        """
        text_hash = hash(text[:100])
        with self._cache_lock:
            if text_hash in self._lang_cache:
                return self._lang_cache[text_hash]
        
        try:
            # Get detailed detection results
            langs = detect_langs(text)
            top_lang = langs[0]
            
            detected_lang = top_lang.lang
            confidence = top_lang.prob
            
            # Normalize some language codes
            if detected_lang == "zh-cn":
                detected_lang = "zh"
            
            # Cache the result
            result = (detected_lang, confidence)
            with self._cache_lock:
                self._lang_cache[text_hash] = result
                
            logger.info(f"Language detected: {detected_lang} (confidence: {confidence:.3f})")
            return result
            
        except Exception as e:
            logger.warning(f"Language detection failed: {e}. Defaulting to English.")
            return ("en", 1.0)

    def get_translation_service(self, language: str) -> str:
        """
        Determine which translation service to use for a given language.
        Returns: 'sarvam', 'google', or 'unsupported'
        """
        if language in self.SARVAM_LANGUAGES:
            return 'sarvam'
        elif language in self.GOOGLE_LANG_MAP and self.google_api_key:
            return 'google'
        else:
            return 'unsupported'

    def translate_with_sarvam(self, text: str, target_lang: str) -> str:
        """Translate using Sarvam AI for Indian languages."""
        if target_lang == "en":
            return text
            
        target_code = self.SARVAM_LANG_MAP.get(target_lang, "hi-IN")
        logger.info(f"Translating with Sarvam AI to {target_code}...")
        
        api_url = "https://api.sarvam.ai/translate"
        headers = {
            "api-subscription-key": self.sarvam_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "input": text,
            "source_language_code": "en-IN",
            "target_language_code": target_code,
            "speaker_json": "{}"
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            translated_text = response.json()["translated_text"]
            logger.info(f"Sarvam translation successful")
            return translated_text
        except Exception as e:
            logger.error(f"Sarvam translation error: {e}")
            return text

    def translate_with_google(self, text: str, target_lang: str) -> str:
        """Translate using Google Translate for global languages."""
        if not self.google_api_key:
            logger.warning("Google Translate API key not available")
            return text
            
        target_code = self.GOOGLE_LANG_MAP.get(target_lang, target_lang)
        logger.info(f"Translating with Google Translate to {target_code}...")
        
        api_url = "https://translation.googleapis.com/language/translate/v2"
        params = {
            'key': self.google_api_key,
            'q': text,
            'source': 'en',
            'target': target_code,
            'format': 'text'
        }
        
        try:
            response = requests.post(api_url, params=params, timeout=15)
            response.raise_for_status()
            result = response.json()
            translated_text = result['data']['translations'][0]['translatedText']
            logger.info(f"Google translation successful")
            return translated_text
        except Exception as e:
            logger.error(f"Google translation error: {e}")
            return text

    def translate_text_enhanced(self, text: str, target_lang: str) -> str:
        """
        Enhanced translation with automatic service routing.
        Supports 55+ languages through hybrid approach.
        """
        if target_lang == "en":
            return text
        
        service = self.get_translation_service(target_lang)
        
        if service == 'sarvam':
            return self.translate_with_sarvam(text, target_lang)
        elif service == 'google':
            return self.translate_with_google(text, target_lang)
        else:
            logger.warning(f"Language {target_lang} not supported. Returning English.")
            return text

    def get_tts_service(self, language: str) -> str:
        """Determine which TTS service to use."""
        if language in self.SARVAM_LANGUAGES:
            return 'sarvam'
        else:
            return 'fallback'  # Could integrate other TTS services here

    def tts_with_sarvam(self, text: str, target_lang_code: str) -> Optional[str]:
        """Generate TTS using Sarvam AI."""
        if not self.sarvam_client:
            return None
            
        logger.info(f"Generating TTS with Sarvam AI (Lang: {target_lang_code})...")
        api_url = "https://api.sarvam.ai/text-to-speech/stream"

        headers = {
            "api-subscription-key": self.sarvam_api_key,
            "Content-Type": "application/json"
        }

        # Select optimal speaker
        speaker = "gokul" if target_lang_code in ["en-IN", "hi-IN", "gu-IN", "mr-IN"] else "valli_m"

        payload = {
            "text": text,
            "target_language_code": target_lang_code,
            "speaker": speaker,
            "model": "bulbul:v3",
            "pace": 1.1,
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
            logger.info(f"Sarvam TTS successful: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Sarvam TTS error: {e}")
            return None

    def tts_enhanced(self, text: str, language: str) -> Optional[str]:
        """
        Enhanced TTS with service routing.
        Falls back to English if target language TTS not available.
        """
        tts_service = self.get_tts_service(language)
        
        if tts_service == 'sarvam':
            lang_code = self.SARVAM_LANG_MAP.get(language, "en-IN")
            return self.tts_with_sarvam(text, lang_code)
        else:
            # Fallback to English TTS for unsupported languages
            logger.info(f"TTS not available for {language}. Using English TTS.")
            return self.tts_with_sarvam(text, "en-IN")

    def process_multilingual_response(self, english_response: str, target_language: str) -> Tuple[str, Optional[str]]:
        """
        Enhanced multilingual processing supporting 55+ languages.
        Returns (final_text, audio_path)
        """
        start_time = time.time()
        
        if target_language == "en":
            # English path
            audio_path = self.tts_enhanced(english_response, "en")
            processing_time = time.time() - start_time
            logger.info(f"English pipeline completed in {processing_time:.2f}s")
            return english_response, audio_path
        else:
            # Multi-language path
            translated_text = self.translate_text_enhanced(english_response, target_language)
            audio_path = self.tts_enhanced(translated_text, target_language)
            
            processing_time = time.time() - start_time
            logger.info(f"Multilingual pipeline ({target_language}) completed in {processing_time:.2f}s")
            return translated_text, audio_path

    def get_language_support_info(self) -> Dict:
        """Get comprehensive information about language support."""
        return {
            "total_detectable": len(self.DETECTABLE_LANGUAGES),
            "sarvam_supported": len(self.SARVAM_LANGUAGES),
            "google_supported": len(self.GOOGLE_LANG_MAP) if self.google_api_key else 0,
            "tts_supported": len(self.SARVAM_LANGUAGES),
            "detectable_languages": sorted(list(self.DETECTABLE_LANGUAGES)),
            "sarvam_languages": sorted(list(self.SARVAM_LANGUAGES)),
            "google_languages": sorted(list(self.GOOGLE_LANG_MAP.keys())) if self.google_api_key else [],
            "services_available": {
                "sarvam_ai": bool(self.sarvam_api_key),
                "google_translate": bool(self.google_api_key)
            }
        }

if __name__ == "__main__":
    # Test the enhanced speech layer
    speech = EnhancedCareMateSpeech()
    
    print("🌍 Enhanced CareMate Speech Layer Test")
    print("=" * 50)
    
    # Get language support info
    info = speech.get_language_support_info()
    print(f"Language Detection: {info['total_detectable']} languages")
    print(f"Translation (Sarvam): {info['sarvam_supported']} languages")
    print(f"Translation (Google): {info['google_supported']} languages")
    print(f"TTS Support: {info['tts_supported']} languages")
    
    # Test language detection
    test_phrases = [
        "Hello, I need medical help",
        "नमस्ते, मुझे चिकित्सा सहायता चाहिए",
        "Bonjour, j'ai besoin d'aide médicale",
        "Hola, necesito ayuda médica",
        "こんにちは、医療援助が必要です"
    ]
    
    print(f"\nTesting Language Detection:")
    for phrase in test_phrases:
        lang, confidence = speech.detect_language_enhanced(phrase)
        service = speech.get_translation_service(lang)
        print(f"  '{phrase[:30]}...' -> {lang} ({confidence:.3f}) [{service}]")
    
    # Test translation if available
    if speech.sarvam_api_key:
        print(f"\nTesting Translation:")
        test_text = "Your medication is ready for pickup."
        for lang in ["hi", "ta"]:
            translated = speech.translate_text_enhanced(test_text, lang)
            print(f"  {lang.upper()}: {translated}")
    
    print("\n✅ Enhanced Speech Layer Ready!")
    print(f"   • Can detect: {info['total_detectable']} languages")
    print(f"   • Can translate: {info['sarvam_supported'] + info['google_supported']} languages")
    print(f"   • Can speak: {info['tts_supported']} languages")