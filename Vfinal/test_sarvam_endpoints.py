#!/usr/bin/env python3
"""
Test script to verify Sarvam AI endpoints and find the correct API URLs.
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

def test_sarvam_endpoints():
    """Test various Sarvam AI endpoints to find what's available."""
    
    print("🔍 Testing Sarvam AI Endpoints")
    print("=" * 50)
    print(f"API Key: {SARVAM_API_KEY[:20]}...")
    
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Test endpoints
    endpoints_to_test = [
        {
            "name": "Language Identification",
            "url": "https://api.sarvam.ai/language-identification",
            "payload": {"input": "नमस्ते, मुझे मदद चाहिए"}
        },
        {
            "name": "Translation",
            "url": "https://api.sarvam.ai/translate",
            "payload": {
                "input": "Hello, I need help",
                "source_language_code": "en-IN",
                "target_language_code": "hi-IN",
                "speaker_json": "{}"
            }
        },
        {
            "name": "Text-to-Speech",
            "url": "https://api.sarvam.ai/text-to-speech/stream",
            "payload": {
                "text": "Hello, this is a test",
                "target_language_code": "en-IN",
                "speaker": "gokul",
                "model": "bulbul:v3",
                "pace": 1.0,
                "speech_sample_rate": 22050,
                "output_audio_codec": "mp3",
                "enable_preprocessing": True
            }
        }
    ]
    
    for endpoint in endpoints_to_test:
        print(f"\n📡 Testing {endpoint['name']}")
        print("-" * 30)
        
        try:
            response = requests.post(
                endpoint['url'], 
                headers=headers, 
                json=endpoint['payload'],
                timeout=10
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCCESS")
                if endpoint['name'] != "Text-to-Speech":  # Don't print binary data
                    result = response.json()
                    print(f"Response: {result}")
                else:
                    print(f"Audio data received: {len(response.content)} bytes")
            else:
                print("❌ FAILED")
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    # Test alternative endpoints
    print(f"\n🔄 Testing Alternative Endpoints")
    print("-" * 30)
    
    alternative_endpoints = [
        "https://api.sarvam.ai/language-detect",
        "https://api.sarvam.ai/v1/language-identification",
        "https://api.sarvam.ai/v1/translate",
        "https://api.sarvam.ai/speech-to-text/translate"
    ]
    
    for url in alternative_endpoints:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            print(f"{url}: {response.status_code}")
        except Exception as e:
            print(f"{url}: ERROR - {e}")

if __name__ == "__main__":
    if not SARVAM_API_KEY:
        print("❌ SARVAM_API_KEY not found in environment")
    else:
        test_sarvam_endpoints()