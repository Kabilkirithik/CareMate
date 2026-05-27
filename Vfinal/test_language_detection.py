#!/usr/bin/env python3
"""
Test script to check what languages can be detected by langdetect library
and explore options for expanding language support beyond the current 9 languages.
"""

from langdetect import detect, detect_langs
from langdetect.lang_detect_exception import LangDetectException
import requests

def test_language_detection_capabilities():
    """Test the full range of languages that langdetect can handle."""
    
    print("🌍 Language Detection Capability Test")
    print("=" * 50)
    
    # Test phrases in various languages
    test_phrases = {
        # Current supported languages
        "en": "Hello, I need medical assistance",
        "hi": "नमस्ते, मुझे चिकित्सा सहायता चाहिए",
        "ta": "வணக்கம், எனக்கு மருத்துவ உதவி தேவை",
        "te": "నమస్కారం, నాకు వైద్య సహాయం అవసరం",
        "ml": "നമസ്കാരം, എനിക്ക് വൈദ്യസഹായം വേണം",
        "kn": "ನಮಸ್ಕಾರ, ನನಗೆ ವೈದ್ಯಕೀಯ ಸಹಾಯ ಬೇಕು",
        "gu": "નમસ્તે, મને તબીબી સહાય જોઈએ છે",
        "mr": "नमस्कार, मला वैद्यकीय मदत हवी आहे",
        "bn": "নমস্কার, আমার চিকিৎসা সহায়তা দরকার",
        
        # Additional major languages
        "fr": "Bonjour, j'ai besoin d'aide médicale",
        "es": "Hola, necesito asistencia médica",
        "de": "Hallo, ich brauche medizinische Hilfe",
        "it": "Ciao, ho bisogno di assistenza medica",
        "pt": "Olá, preciso de assistência médica",
        "ru": "Привет, мне нужна медицинская помощь",
        "ja": "こんにちは、医療援助が必要です",
        "ko": "안녕하세요, 의료 지원이 필요합니다",
        "zh": "你好，我需要医疗帮助",
        "ar": "مرحبا، أحتاج إلى مساعدة طبية",
        "th": "สวัสดี ฉันต้องการความช่วยเหลือทางการแพทย์",
        "vi": "Xin chào, tôi cần hỗ trợ y tế",
        "id": "Halo, saya membutuhkan bantuan medis",
        "ms": "Hello, saya memerlukan bantuan perubatan",
        "tl": "Kumusta, kailangan ko ng tulong medikal",
        "ur": "ہیلو، مجھے طبی مدد کی ضرورت ہے",
        "fa": "سلام، من به کمک پزشکی نیاز دارم",
        "tr": "Merhaba, tıbbi yardıma ihtiyacım var",
        "pl": "Cześć, potrzebuję pomocy medycznej",
        "nl": "Hallo, ik heb medische hulp nodig",
        "sv": "Hej, jag behöver medicinsk hjälp",
        "da": "Hej, jeg har brug for lægehjælp",
        "no": "Hei, jeg trenger medisinsk hjelp",
        "fi": "Hei, tarvitsen lääketieteellistä apua"
    }
    
    print("1. Testing Language Detection Accuracy")
    print("-" * 40)
    
    detected_correctly = 0
    total_tests = len(test_phrases)
    detection_results = {}
    
    for expected_lang, phrase in test_phrases.items():
        try:
            detected_lang = detect(phrase)
            is_correct = detected_lang == expected_lang
            
            if is_correct:
                detected_correctly += 1
                status = "✅"
            else:
                status = "❌"
            
            detection_results[expected_lang] = {
                "phrase": phrase[:50] + "..." if len(phrase) > 50 else phrase,
                "detected": detected_lang,
                "correct": is_correct
            }
            
            print(f"   {expected_lang.upper()}: {detected_lang} {status}")
            
        except LangDetectException as e:
            print(f"   {expected_lang.upper()}: ERROR - {e}")
            detection_results[expected_lang] = {
                "phrase": phrase,
                "detected": "ERROR",
                "correct": False
            }
    
    accuracy = (detected_correctly / total_tests) * 100
    print(f"\nDetection Accuracy: {accuracy:.1f}% ({detected_correctly}/{total_tests})")
    
    return detection_results

def test_confidence_levels():
    """Test confidence levels for language detection."""
    print("\n2. Testing Detection Confidence Levels")
    print("-" * 40)
    
    test_phrases = [
        ("Hello, I need help", "en"),
        ("नमस्ते, मुझे मदद चाहिए", "hi"),
        ("Bonjour, j'ai besoin d'aide", "fr"),
        ("Hola, necesito ayuda", "es"),
        ("こんにちは、助けが必要です", "ja")
    ]
    
    for phrase, expected in test_phrases:
        try:
            # Get confidence scores for all detected languages
            langs = detect_langs(phrase)
            top_lang = langs[0]
            
            print(f"   '{phrase[:30]}...'")
            print(f"     Top: {top_lang.lang} ({top_lang.prob:.3f})")
            if len(langs) > 1:
                print(f"     Alt: {langs[1].lang} ({langs[1].prob:.3f})")
            print()
            
        except LangDetectException as e:
            print(f"   ERROR: {e}")

def check_translation_services():
    """Check what translation services are available beyond Sarvam AI."""
    print("\n3. Available Translation Services")
    print("-" * 40)
    
    services = {
        "Sarvam AI": {
            "languages": 9,
            "focus": "Indian languages",
            "supported": ["en-IN", "hi-IN", "ta-IN", "te-IN", "ml-IN", "kn-IN", "gu-IN", "mr-IN", "bn-IN"]
        },
        "Google Translate": {
            "languages": 100,
            "focus": "Global languages",
            "note": "Requires Google Cloud API key"
        },
        "Azure Translator": {
            "languages": 90,
            "focus": "Global languages", 
            "note": "Requires Azure subscription"
        },
        "AWS Translate": {
            "languages": 75,
            "focus": "Global languages",
            "note": "Requires AWS account"
        },
        "LibreTranslate": {
            "languages": 30,
            "focus": "Open source",
            "note": "Self-hosted option available"
        }
    }
    
    for service, info in services.items():
        print(f"   {service}:")
        print(f"     Languages: {info['languages']}")
        print(f"     Focus: {info['focus']}")
        if 'note' in info:
            print(f"     Note: {info['note']}")
        if 'supported' in info:
            print(f"     Current: {', '.join(info['supported'][:5])}...")
        print()

def suggest_expansion_strategy():
    """Suggest how to expand language support."""
    print("\n4. Language Expansion Strategy")
    print("-" * 40)
    
    print("🎯 CURRENT LIMITATIONS:")
    print("   • Sarvam AI: 9 Indian languages only")
    print("   • TTS: Limited to Sarvam's supported voices")
    print("   • Translation: Indian languages + English only")
    
    print("\n🚀 EXPANSION OPTIONS:")
    print("   Option 1: Hybrid Approach")
    print("     • Keep Sarvam AI for Indian languages (best quality)")
    print("     • Add Google Translate for global languages")
    print("     • Use different TTS services per language group")
    
    print("\n   Option 2: Multi-Service Architecture")
    print("     • Sarvam AI: Indian languages")
    print("     • Azure Translator: European languages")
    print("     • AWS Polly: Global TTS")
    print("     • ElevenLabs: High-quality voices")
    
    print("\n   Option 3: Fallback Chain")
    print("     • Primary: Sarvam AI (Indian languages)")
    print("     • Secondary: Google Translate (global)")
    print("     • Tertiary: LibreTranslate (open source)")
    
    print("\n📊 RECOMMENDED APPROACH:")
    print("   1. Detect language with langdetect (55+ languages)")
    print("   2. Route to appropriate service:")
    print("      • Indian languages → Sarvam AI")
    print("      • Global languages → Google Translate")
    print("   3. Use service-specific TTS")
    print("   4. Fallback to English if unsupported")

if __name__ == "__main__":
    # Run all tests
    detection_results = test_language_detection_capabilities()
    test_confidence_levels()
    check_translation_services()
    suggest_expansion_strategy()
    
    print("\n" + "=" * 50)
    print("🌍 SUMMARY: langdetect can detect 55+ languages")
    print("🔧 CURRENT: Limited to 9 languages by Sarvam AI")
    print("🚀 POTENTIAL: Can expand to 100+ with hybrid approach")
    print("=" * 50)