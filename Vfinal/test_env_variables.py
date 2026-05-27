#!/usr/bin/env python3
"""
Test script to verify all environment variables are properly loaded from .env file.
"""

import os
from dotenv import load_dotenv

def test_environment_variables():
    """Test that all required environment variables are loaded correctly."""
    
    print("🔐 Environment Variables Test")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Define required environment variables
    required_vars = {
        "MONGO_URI": "MongoDB connection string",
        "SARVAM_API_KEY": "Sarvam AI API key for speech and translation",
        "OPENAI_API_KEY": "OpenAI API key (can be dummy for testing)",
        "OPENROUTER_API_KEY": "OpenRouter API key for Nemotron model",
        "SAGEMAKER_URL": "SageMaker/Meditron endpoint URL"
    }
    
    optional_vars = {
        "GOOGLE_TRANSLATE_API_KEY": "Google Translate API key (optional)"
    }
    
    print("📋 Required Environment Variables:")
    print("-" * 40)
    
    missing_vars = []
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if value:
            # Mask sensitive values for display
            if "API_KEY" in var_name or "URI" in var_name:
                display_value = f"{value[:10]}...{value[-5:]}" if len(value) > 15 else value[:10] + "..."
            else:
                display_value = value
            
            print(f"   ✅ {var_name}: {display_value}")
        else:
            print(f"   ❌ {var_name}: NOT SET")
            missing_vars.append(var_name)
    
    print(f"\n📋 Optional Environment Variables:")
    print("-" * 40)
    
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name)
        if value:
            display_value = f"{value[:10]}...{value[-5:]}" if len(value) > 15 else value[:10] + "..."
            print(f"   ✅ {var_name}: {display_value}")
        else:
            print(f"   ⚠️  {var_name}: NOT SET (optional)")
    
    print(f"\n📊 Summary:")
    print("-" * 40)
    
    if missing_vars:
        print(f"   ❌ Missing required variables: {len(missing_vars)}")
        print(f"   📝 Missing: {', '.join(missing_vars)}")
        print(f"   🔧 Please add these to your .env file")
        return False
    else:
        print(f"   ✅ All required variables are set!")
        print(f"   🎉 Environment configuration is complete")
        return True

def test_api_key_loading_in_modules():
    """Test that modules can properly load API keys from environment."""
    
    print(f"\n🔌 Module API Key Loading Test")
    print("-" * 40)
    
    try:
        # Test speech layer
        from speech_layer import CareMateSpeech
        speech = CareMateSpeech()
        if speech.api_key:
            print("   ✅ Speech Layer: API key loaded successfully")
        else:
            print("   ❌ Speech Layer: API key not loaded")
    except Exception as e:
        print(f"   ❌ Speech Layer: Error - {e}")
    
    try:
        # Test caremate agents
        from caremate_agents import CareMateAgents
        agents = CareMateAgents()
        openai_key = os.getenv("OPENAI_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        if openai_key and openrouter_key:
            print("   ✅ CareMate Agents: API keys loaded successfully")
        else:
            print("   ❌ CareMate Agents: API keys not loaded")
    except Exception as e:
        print(f"   ❌ CareMate Agents: Error - {e}")
    
    try:
        # Test meditron client
        from meditron_client import MeditronClient
        client = MeditronClient()
        if client.base_url:
            print("   ✅ Meditron Client: URL loaded successfully")
        else:
            print("   ❌ Meditron Client: URL not loaded")
    except Exception as e:
        print(f"   ❌ Meditron Client: Error - {e}")

def show_env_file_template():
    """Show the expected .env file template."""
    
    print(f"\n📄 Expected .env File Template:")
    print("-" * 40)
    
    template = """
# MongoDB Connection
MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net/?appName=AppName"

# Sarvam AI API Key
SARVAM_API_KEY=sk_your_sarvam_api_key_here

# OpenAI API Key (can be dummy for testing)
OPENAI_API_KEY=sk-caremate-dummy

# OpenRouter API Key for Nemotron model
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_key_here

# SageMaker/Meditron endpoint URL
SAGEMAKER_URL=https://your-ngrok-url.ngrok-free.dev

# Google Translate API Key (optional)
GOOGLE_TRANSLATE_API_KEY=your_google_api_key_here
"""
    
    print(template)

if __name__ == "__main__":
    print("🔐 CareMate Environment Variables Configuration Test")
    print("=" * 60)
    
    # Test environment variables
    env_ok = test_environment_variables()
    
    # Test module loading
    test_api_key_loading_in_modules()
    
    # Show template if there are issues
    if not env_ok:
        show_env_file_template()
    
    print("\n" + "=" * 60)
    if env_ok:
        print("🎉 Environment configuration is ready for production!")
    else:
        print("⚠️  Please fix the missing environment variables before running the system.")
    print("=" * 60)