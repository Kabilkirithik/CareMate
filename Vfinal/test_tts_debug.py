#!/usr/bin/env python3
"""
Debug TTS issues and test different language configurations.
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

def test_tts_configurations():
    """Test different TTS configurations to find what works."""
    
    print("🔊 Testing TTS Configurations")
    print("=" * 50)
    
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Test different language and speaker combinations
    test_configs = [
        {
            "name": "English with gokul",
            "text": "Hello, this is a test message",
            "target_language_code": "en-IN",
            "speaker": "gokul"
        },
        {
            "name": "Hindi with gokul", 
            "text": "नमस्ते, यह एक परीक्षण संदेश है",
            "target_language_code": "hi-IN",
            "speaker": "gokul"
        },
        {
            "name": "Tamil with valli_m",
            "text": "வணக்கம், இது ஒரு சோதனை செய்தி",
            "target_language_code": "ta-IN",
            "speaker": "valli_m"
        },
        {
            "name": "Bengali with valli_m",
            "text": "নমস্কার, এটি একটি পরীক্ষার বার্তা",
            "target_language_code": "bn-IN", 
            "speaker": "valli_m"
        },
        {
            "name": "Tamil with gokul (test speaker)",
            "text": "வணக்கம், இது ஒரு சோதனை செய்தி",
            "target_language_code": "ta-IN",
            "speaker": "gokul"
        }
    ]
    
    for config in test_configs:
        print(f"\n🎵 Testing {config['name']}")
        print("-" * 30)
        
        payload = {
            "text": config["text"],
            "target_language_code": config["target_language_code"],
            "speaker": config["speaker"],
            "model": "bulbul:v3",
            "pace": 1.0,
            "speech_sample_rate": 22050,
            "output_audio_codec": "mp3",
            "enable_preprocessing": True
        }
        
        try:
            response = requests.post(
                "https://api.sarvam.ai/text-to-speech/stream",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ SUCCESS - Audio: {len(response.content)} bytes")
            else:
                print("❌ FAILED")
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    # Test available speakers
    print(f"\n🎭 Testing Available Speakers")
    print("-" * 30)
    
    speakers_to_test = ["gokul", "valli_m", "meera", "arjun", "kavya"]
    
    for speaker in speakers_to_test:
        payload = {
            "text": "Hello, this is a test",
            "target_language_code": "en-IN",
            "speaker": speaker,
            "model": "bulbul:v3",
            "pace": 1.0,
            "speech_sample_rate": 22050,
            "output_audio_codec": "mp3",
            "enable_preprocessing": True
        }
        
        try:
            response = requests.post(
                "https://api.sarvam.ai/text-to-speech/stream",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            status = "✅" if response.status_code == 200 else "❌"
            print(f"   {speaker}: {response.status_code} {status}")
            
        except Exception as e:
            print(f"   {speaker}: ERROR - {e}")

if __name__ == "__main__":
    test_tts_configurations()