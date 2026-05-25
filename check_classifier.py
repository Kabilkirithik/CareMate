
import sys
import os
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent))

try:
    from caremate_v4.classifier.classifier_client import classify_message, is_classifier_available
    print(f"Classifier available: {is_classifier_available()}")
    
    test_messages = [
        "I need a blanket",
        "I can't breathe",
        "When is my next medicine?",
        "I want some water",
        "Hello how are you?"
    ]
    
    for msg in test_messages:
        result = classify_message(msg)
        print(f"Message: '{msg}' -> Category: {result['category']} (Source: {result['source']}, Confidence: {result['confidence']})")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
