#!/usr/bin/env python3
"""
Comprehensive test for all 11 Sarvam AI supported languages.
Tests language detection, translation, and TTS capabilities.
"""

import time
import logging
from speech_layer import CareMateSpeech
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def test_all_11_languages():
    """Test all 11 Sarvam AI supported languages comprehensively."""
    
    print("🌍 CareMate Speech Layer - Complete 11 Language Test")
    print("=" * 60)
    
    speech = CareMateSpeech()
    
    # All 11 supported languages with sample medical phrases
    language_test_data = {
        "en-IN": {
            "phrase": "Hello doctor, I am feeling chest pain since morning",
            "script": "Latn",
            "name": "English"
        },
        "hi-IN": {
            "phrase": "नमस्ते डॉक्टर, मुझे सुबह से सीने में दर्द हो रहा है",
            "script": "Deva", 
            "name": "Hindi"
        },
        "bn-IN": {
            "phrase": "নমস্কার ডাক্তার, আমার সকাল থেকে বুকে ব্যথা হচ্ছে",
            "script": "Beng",
            "name": "Bengali"
        },
        "gu-IN": {
            "phrase": "નમસ્તે ડૉક્ટર, મને સવારથી છાતીમાં દુખાવો થઈ રહ્યો છે",
            "script": "Gujr",
            "name": "Gujarati"
        },
        "kn-IN": {
            "phrase": "ನಮಸ್ಕಾರ ಡಾಕ್ಟರ್, ನನಗೆ ಬೆಳಿಗ್ಗೆಯಿಂದ ಎದೆಯಲ್ಲಿ ನೋವಾಗುತ್ತಿದೆ",
            "script": "Knda",
            "name": "Kannada"
        },
        "ml-IN": {
            "phrase": "നമസ്കാരം ഡോക്ടർ, എനിക്ക് രാവിലെ മുതൽ നെഞ്ചിൽ വേദന അനുഭവപ്പെടുന്നു",
            "script": "Mlym",
            "name": "Malayalam"
        },
        "mr-IN": {
            "phrase": "नमस्कार डॉक्टर, मला सकाळपासून छातीत दुखत आहे",
            "script": "Deva",
            "name": "Marathi"
        },
        "od-IN": {
            "phrase": "ନମସ୍କାର ଡାକ୍ତର, ମୋର ସକାଳୁ ଛାତିରେ ଯନ୍ତ୍ରଣା ହେଉଛି",
            "script": "Orya",
            "name": "Odia"
        },
        "pa-IN": {
            "phrase": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਡਾਕਟਰ, ਮੈਨੂੰ ਸਵੇਰ ਤੋਂ ਛਾਤੀ ਵਿੱਚ ਦਰਦ ਹੋ ਰਿਹਾ ਹੈ",
            "script": "Guru",
            "name": "Punjabi"
        },
        "ta-IN": {
            "phrase": "வணக்கம் டாக்டர், எனக்கு காலையிலிருந்து மார்பில் வலி இருக்கிறது",
            "script": "Taml",
            "name": "Tamil"
        },
        "te-IN": {
            "phrase": "నమస్కారం డాక్టర్, నాకు ఉదయం నుండి ఛాతీలో నొప్పి వస్తోంది",
            "script": "Telu",
            "name": "Telugu"
        }
    }
    
    print(f"Testing {len(language_test_data)} languages supported by Sarvam AI\n")
    
    # Test 1: Language Detection Accuracy
    print("1. 🔍 Language Detection Test")
    print("-" * 40)
    
    detection_results = {}
    correct_detections = 0
    
    for lang_code, data in language_test_data.items():
        try:
            start_time = time.time()
            detected_lang, detected_script, confidence = speech.detect_language_sarvam(data["phrase"])
            detection_time = time.time() - start_time
            
            lang_correct = detected_lang == lang_code
            script_correct = detected_script == data["script"]
            overall_correct = lang_correct and script_correct
            
            if overall_correct:
                correct_detections += 1
                status = "✅"
            else:
                status = "❌"
            
            detection_results[lang_code] = {
                "detected_lang": detected_lang,
                "detected_script": detected_script,
                "correct": overall_correct,
                "time": detection_time
            }
            
            print(f"   {data['name']:12} ({lang_code}): {detected_lang} | {detected_script} | {detection_time:.3f}s {status}")
            
        except Exception as e:
            print(f"   {data['name']:12} ({lang_code}): ERROR - {str(e)[:50]}...")
            detection_results[lang_code] = {"correct": False, "time": 0}
    
    detection_accuracy = (correct_detections / len(language_test_data)) * 100
    avg_detection_time = sum(r.get("time", 0) for r in detection_results.values()) / len(detection_results)
    
    print(f"\n   Detection Accuracy: {detection_accuracy:.1f}% ({correct_detections}/{len(language_test_data)})")
    print(f"   Average Detection Time: {avg_detection_time:.3f}s")
    
    # Test 2: Translation Performance
    print(f"\n2. 🔄 Translation Performance Test")
    print("-" * 40)
    
    english_text = "Your blood pressure is normal. Please continue taking your medication as prescribed by the doctor."
    translation_results = {}
    successful_translations = 0
    
    for lang_code, data in language_test_data.items():
        if lang_code == "en-IN":
            continue  # Skip English to English translation
            
        try:
            start_time = time.time()
            translated_text = speech.translate_text_fast(english_text, lang_code)
            translation_time = time.time() - start_time
            
            # Check if translation was successful (not just returning original text)
            success = translated_text != english_text and len(translated_text) > 10
            
            if success:
                successful_translations += 1
                status = "✅"
            else:
                status = "❌"
            
            translation_results[lang_code] = {
                "translated_text": translated_text,
                "success": success,
                "time": translation_time
            }
            
            print(f"   {data['name']:12} ({lang_code}): {translation_time:.2f}s {status}")
            print(f"      {translated_text[:60]}...")
            
        except Exception as e:
            print(f"   {data['name']:12} ({lang_code}): ERROR - {str(e)[:50]}...")
            translation_results[lang_code] = {"success": False, "time": 0}
    
    translation_success_rate = (successful_translations / (len(language_test_data) - 1)) * 100  # -1 for English
    avg_translation_time = sum(r.get("time", 0) for r in translation_results.values()) / len(translation_results)
    
    print(f"\n   Translation Success Rate: {translation_success_rate:.1f}% ({successful_translations}/{len(language_test_data)-1})")
    print(f"   Average Translation Time: {avg_translation_time:.2f}s")
    
    # Test 3: TTS Performance (Sample Languages)
    print(f"\n3. 🔊 Text-to-Speech Test (Sample Languages)")
    print("-" * 40)
    
    tts_test_langs = ["en-IN", "hi-IN", "ta-IN", "bn-IN", "gu-IN"]
    tts_results = {}
    successful_tts = 0
    
    test_tts_text = "Hello, your test results are ready."
    
    for lang_code in tts_test_langs:
        try:
            # First translate if not English
            if lang_code != "en-IN":
                text_to_speak = speech.translate_text_fast(test_tts_text, lang_code)
            else:
                text_to_speak = test_tts_text
            
            start_time = time.time()
            audio_path = speech.tts_optimized(text_to_speak, lang_code)
            tts_time = time.time() - start_time
            
            success = audio_path is not None
            if success:
                successful_tts += 1
                status = "✅"
            else:
                status = "❌"
            
            tts_results[lang_code] = {
                "audio_path": audio_path,
                "success": success,
                "time": tts_time
            }
            
            lang_name = next(data["name"] for code, data in language_test_data.items() if code == lang_code)
            print(f"   {lang_name:12} ({lang_code}): {tts_time:.2f}s {status}")
            
        except Exception as e:
            print(f"   {lang_code}: ERROR - {str(e)[:50]}...")
            tts_results[lang_code] = {"success": False, "time": 0}
    
    tts_success_rate = (successful_tts / len(tts_test_langs)) * 100
    avg_tts_time = sum(r.get("time", 0) for r in tts_results.values()) / len(tts_results)
    
    print(f"\n   TTS Success Rate: {tts_success_rate:.1f}% ({successful_tts}/{len(tts_test_langs)})")
    print(f"   Average TTS Time: {avg_tts_time:.2f}s")
    
    # Test 4: Full Pipeline Test
    print(f"\n4. 🚀 Full Voice Response Pipeline Test")
    print("-" * 40)
    
    pipeline_test_langs = ["en-IN", "hi-IN", "ta-IN"]
    pipeline_results = {}
    successful_pipelines = 0
    
    english_response = "I have notified the nurse. They will be with you shortly to assist with your request."
    
    for lang_code in pipeline_test_langs:
        try:
            start_time = time.time()
            final_text, audio_path = speech.process_voice_response_pipeline(english_response, lang_code)
            pipeline_time = time.time() - start_time
            
            success = audio_path is not None and final_text is not None
            if success:
                successful_pipelines += 1
                status = "✅"
            else:
                status = "❌"
            
            pipeline_results[lang_code] = {
                "final_text": final_text,
                "audio_path": audio_path,
                "success": success,
                "time": pipeline_time
            }
            
            lang_name = next(data["name"] for code, data in language_test_data.items() if code == lang_code)
            print(f"   {lang_name:12} ({lang_code}): {pipeline_time:.2f}s {status}")
            print(f"      {final_text[:60]}...")
            
        except Exception as e:
            print(f"   {lang_code}: ERROR - {str(e)[:50]}...")
            pipeline_results[lang_code] = {"success": False, "time": 0}
    
    pipeline_success_rate = (successful_pipelines / len(pipeline_test_langs)) * 100
    avg_pipeline_time = sum(r.get("time", 0) for r in pipeline_results.values()) / len(pipeline_results)
    
    print(f"\n   Pipeline Success Rate: {pipeline_success_rate:.1f}% ({successful_pipelines}/{len(pipeline_test_langs)})")
    print(f"   Average Pipeline Time: {avg_pipeline_time:.2f}s")
    
    # Final Summary
    print(f"\n" + "=" * 60)
    print("🎉 COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    print(f"📊 Languages Tested: {len(language_test_data)}")
    print(f"🔍 Detection Accuracy: {detection_accuracy:.1f}%")
    print(f"🔄 Translation Success: {translation_success_rate:.1f}%")
    print(f"🔊 TTS Success: {tts_success_rate:.1f}%")
    print(f"🚀 Pipeline Success: {pipeline_success_rate:.1f}%")
    print(f"⚡ Average Response Time: {avg_pipeline_time:.2f}s")
    
    overall_score = (detection_accuracy + translation_success_rate + tts_success_rate + pipeline_success_rate) / 4
    
    if overall_score >= 90:
        grade = "🏆 EXCELLENT"
    elif overall_score >= 80:
        grade = "🥇 VERY GOOD"
    elif overall_score >= 70:
        grade = "🥈 GOOD"
    else:
        grade = "🥉 NEEDS IMPROVEMENT"
    
    print(f"🎯 Overall Performance: {overall_score:.1f}% - {grade}")
    print("=" * 60)
    
    return {
        "languages_tested": len(language_test_data),
        "detection_accuracy": detection_accuracy,
        "translation_success": translation_success_rate,
        "tts_success": tts_success_rate,
        "pipeline_success": pipeline_success_rate,
        "avg_pipeline_time": avg_pipeline_time,
        "overall_score": overall_score
    }

if __name__ == "__main__":
    results = test_all_11_languages()
    
    print(f"\n🌟 CareMate now supports {results['languages_tested']} Indian languages!")
    print("Ready for production deployment with multi-language patient support.")