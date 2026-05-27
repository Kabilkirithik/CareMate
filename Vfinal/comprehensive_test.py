import os
import logging
from main import CareMateBackend
from pymongo import MongoClient
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def run_comprehensive_test():
    backend = CareMateBackend()
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client["caremate_db"]

    # 1. Get a sample patient
    patient = db.patients.find_one()
    if not patient:
        print("❌ Error: No patients found in MongoDB. Run the data generator first.")
        return
    
    pid = patient['patient_id']
    pname = patient['name']
    print(f"\n" + "="*50)
    print(f"🚀 STARTING COMPREHENSIVE TEST FOR: {pname}")
    print(f"Patient ID: {pid}")
    print("="*50 + "\n")

    # --- TEST 1: WORKFLOW TEST (Nemotron + SVM) ---
    print("TEST 1: Workflow Execution (Utility Request)")
    print("Query: 'Can someone please bring me a bottle of water?'")
    try:
        wf_result = backend.process_input("Can someone please bring me a bottle of water?", pid)
        print(f"✅ Workflow Result:\n{wf_result}\n")
    except Exception as e:
        print(f"❌ Workflow Test Failed: {e}\n")

    # --- TEST 2: MEDICAL RAG TEST (Meditron + ChromaDB) ---
    # Note: Requires Meditron SageMaker/Colab tunnel to be active
    print("TEST 2: Medical Retrieval (RAG)")
    print("Query: 'What were the findings in my recent medical report?'")
    try:
        rag_result = backend.process_input("What were the findings in my recent medical report?", pid)
        print(f"✅ Medical RAG Result:\n{rag_result}\n")
    except Exception as e:
        print(f"❌ Medical RAG Test Failed (Is Meditron online?): {e}\n")

    # --- TEST 3: VOICE PIPELINE TEST (Sarvam AI STT/TTS) ---
    print("TEST 3: Full Voice Pipeline Loop")
    print("Process: Text -> Audio -> AI Processing -> Voice Response")
    
    # Simulate a patient speaking (Generate a test audio file first)
    test_voice_text = "Can a nurse come here?"
    print(f"Simulating Voice Input: '{test_voice_text}'")
    
    try:
        # Create temporary audio for testing STT
        temp_audio_path = backend.speech.tts(test_voice_text)
        print(f"Generated test audio at: {temp_audio_path}")

        # Now process that audio file through the full backend
        voice_response = backend.process_voice_input(temp_audio_path, pid)
        
        print(f"\n--- VOICE PIPELINE RESULTS ---")
        print(f"STT Transcript: {voice_response['transcript']}")
        print(f"AI Text Reply: {voice_response['response_text']}")
        print(f"Final Voice MP3: {voice_response['response_audio']}")
        print(f"✅ Voice Pipeline Test Successful!")
        
        # Cleanup test audio
        # os.remove(temp_audio_path)
        
    except Exception as e:
        print(f"❌ Voice Pipeline Test Failed: {e}")

    print("\n" + "="*50)
    print("🏁 COMPREHENSIVE TEST COMPLETE")
    print("="*50)

if __name__ == "__main__":
    run_comprehensive_test()
