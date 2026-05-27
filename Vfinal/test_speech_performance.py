#!/usr/bin/env python3
"""
Performance test script for the optimized CareMate Speech Layer.
Tests speed improvements and functionality of the enhanced speech processing.
"""

import time
import logging
from speech_layer import CareMateSpeech
from main import CareMateBackend
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def test_speech_performance():
    """Comprehensive performance test for the optimized speech layer."""
    print("🚀 CareMate Speech Layer Performance Test")
    print("=" * 50)
    
    # Initialize components
    speech = CareMateSpeech()
    
    # Test data
    test_responses = [
        "Your blood pressure is normal. Please continue taking your medication as prescribed.",
        "I have notified the nurse. They will be with you shortly to assist with your request.",
        "Based on your recent lab results, everything looks good. Your doctor will discuss the details during the next visit.",
        "Emergency alert has been triggered. Medical staff are on their way to your room immediately."
    ]
    
    test_languages = ["en", "hi", "ta", "te"]
    
    print("\n1. Testing Translation Performance")
    print("-" * 30)
    
    translation_times = []
    for i, response in enumerate(test_responses):
        for lang in test_languages[1:]:  # Skip English
            start_time = time.time()
            translated = speech.translate_text_fast(response, lang)
            end_time = time.time()
            
            duration = end_time - start_time
            translation_times.append(duration)
            
            print(f"   {lang.upper()}: {duration:.2f}s - {translated[:50]}...")
    
    avg_translation_time = sum(translation_times) / len(translation_times)
    print(f"\n   Average Translation Time: {avg_translation_time:.2f}s")
    
    print("\n2. Testing TTS Performance")
    print("-" * 30)
    
    tts_times = []
    for i, response in enumerate(test_responses[:2]):  # Test first 2 responses
        for lang in ["en-IN", "hi-IN"]:
            start_time = time.time()
            audio_path = speech.tts_optimized(response, lang)
            end_time = time.time()
            
            duration = end_time - start_time
            tts_times.append(duration)
            
            status = "✅" if audio_path else "❌"
            print(f"   {lang}: {duration:.2f}s {status}")
    
    avg_tts_time = sum(tts_times) / len(tts_times)
    print(f"\n   Average TTS Time: {avg_tts_time:.2f}s")
    
    print("\n3. Testing Full Voice Response Pipeline")
    print("-" * 30)
    
    pipeline_times = []
    for response in test_responses[:2]:
        for lang in ["en", "hi"]:
            start_time = time.time()
            final_text, audio_path = speech.process_voice_response_pipeline(response, lang)
            end_time = time.time()
            
            duration = end_time - start_time
            pipeline_times.append(duration)
            
            status = "✅" if audio_path else "❌"
            print(f"   {lang.upper()} Pipeline: {duration:.2f}s {status}")
    
    avg_pipeline_time = sum(pipeline_times) / len(pipeline_times)
    print(f"\n   Average Pipeline Time: {avg_pipeline_time:.2f}s")
    
    print("\n4. Testing Language Detection Performance")
    print("-" * 30)
    
    test_phrases = [
        ("Hello, I need help with my medication", "en"),
        ("Namaste, mujhe paani chahiye", "hi"),
        ("Vanakkam, enakku doctor-ai paakanum", "ta"),
        ("Namaskar, nurse-ni pilavaali", "te"),
        ("I am having chest pain", "en")
    ]
    
    detection_times = []
    correct_detections = 0
    
    for phrase, expected_lang in test_phrases:
        start_time = time.time()
        detected_lang = speech.detect_language_fast(phrase)
        end_time = time.time()
        
        duration = end_time - start_time
        detection_times.append(duration)
        
        is_correct = detected_lang == expected_lang
        if is_correct:
            correct_detections += 1
            
        status = "✅" if is_correct else "❌"
        print(f"   '{phrase[:30]}...' -> {detected_lang} ({duration:.3f}s) {status}")
    
    avg_detection_time = sum(detection_times) / len(detection_times)
    accuracy = (correct_detections / len(test_phrases)) * 100
    
    print(f"\n   Average Detection Time: {avg_detection_time:.3f}s")
    print(f"   Detection Accuracy: {accuracy:.1f}%")
    
    print("\n5. Performance Summary")
    print("-" * 30)
    print(f"   Translation Speed: {avg_translation_time:.2f}s avg")
    print(f"   TTS Speed: {avg_tts_time:.2f}s avg")
    print(f"   Full Pipeline Speed: {avg_pipeline_time:.2f}s avg")
    print(f"   Language Detection: {avg_detection_time:.3f}s avg")
    print(f"   Overall Performance: {'🚀 EXCELLENT' if avg_pipeline_time < 5 else '⚡ GOOD' if avg_pipeline_time < 10 else '🐌 NEEDS IMPROVEMENT'}")
    
    return {
        "translation_time": avg_translation_time,
        "tts_time": avg_tts_time,
        "pipeline_time": avg_pipeline_time,
        "detection_time": avg_detection_time,
        "detection_accuracy": accuracy
    }

def test_full_system_integration():
    """Test the full system integration with a sample patient."""
    print("\n🏥 Full System Integration Test")
    print("=" * 50)
    
    try:
        backend = CareMateBackend()
        client = MongoClient(os.getenv("MONGO_URI"))
        db = client["caremate_db"]
        
        # Get a sample patient
        patient = db.patients.find_one()
        if not patient:
            print("❌ No patients found in database. Skipping integration test.")
            return
        
        pid = patient['patient_id']
        print(f"Testing with Patient: {patient['name']} (ID: {pid})")
        
        # Test different types of queries
        test_queries = [
            ("Can you bring me some water?", "utility_request"),
            ("What were my test results?", "status_query"),
            ("I need to see a doctor", "doctor_query"),
            ("Hello, how are you?", "general_conversation")
        ]
        
        total_time = 0
        successful_tests = 0
        
        for query, expected_intent in test_queries:
            print(f"\nTesting: '{query}'")
            start_time = time.time()
            
            try:
                # Test text processing
                result = backend.process_input(query, pid)
                end_time = time.time()
                
                duration = end_time - start_time
                total_time += duration
                successful_tests += 1
                
                print(f"   ✅ Processed in {duration:.2f}s")
                print(f"   Response: {result[:100]}...")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        avg_processing_time = total_time / successful_tests if successful_tests > 0 else 0
        print(f"\nIntegration Test Summary:")
        print(f"   Successful Tests: {successful_tests}/{len(test_queries)}")
        print(f"   Average Processing Time: {avg_processing_time:.2f}s")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")

if __name__ == "__main__":
    # Run performance tests
    performance_results = test_speech_performance()
    
    # Run integration test
    test_full_system_integration()
    
    print("\n🎉 All tests completed!")
    print("=" * 50)