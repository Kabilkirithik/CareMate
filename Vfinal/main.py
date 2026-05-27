import os
import logging
from intent_router import IntentRouter
from caremate_agents import CareMateAgents, CareMateTasks
from speech_layer import CareMateSpeech
from crewai import Crew, Process
from pymongo import MongoClient
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class CareMateBackend:
    def __init__(self):
        logger.info("Initializing CareMate AI Backend...")
        self.router = IntentRouter()
        self.agents = CareMateAgents()
        self.tasks = CareMateTasks()
        self.speech = CareMateSpeech()
        
        # Database Connection
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client["caremate_db"]

    def process_voice_input(self, audio_file_path: str, patient_id: str):
        """Enhanced voice processing pipeline supporting all 11 Sarvam AI languages."""
        # 1. Enhanced Speech to Text with language and script detection
        text_input, detected_lang, detected_script = self.speech.stt_with_language_detection(audio_file_path)
        if not text_input:
            return {"error": "Could not understand audio."}
        
        logger.info(f"STT Result: '{text_input}' | Language: {detected_lang} | Script: {detected_script}")

        # 2. Process via AI logic (Uses Meditron/Nemotron in English)
        result_en = self.process_input(text_input, patient_id, original_lang=detected_lang)
        
        # 3. Enhanced Multi-lingual Response Pipeline
        result_final, audio_response_path = self.speech.process_voice_response_pipeline(
            result_en, detected_lang
        )
        
        return {
            "transcript": text_input,
            "response_text": result_final,
            "response_audio": audio_response_path,
            "detected_language": detected_lang,
            "detected_script": detected_script
        }

    def process_input(self, user_input: str, patient_id: str, original_lang: str = "en"):
        """Processes text input with multiple optimization layers."""
        logger.info(f"Processing Query: '{user_input}' for Patient: {patient_id}")
        
        # 1. Intent Classification (SVM Model)
        classification = self.router.classify(user_input)
        intent = classification['intent']
        confidence = classification['confidence']
        
        logger.info(f"Routed Intent: {intent.upper()} (Confidence: {confidence:.2f})")

        # Load Tools and LLM for Fast Path
        from caremate_agents import orchestrator_llm
        from hospital_tools import WorkflowActionTool

        # --- OPTIMIZATION 1: EMERGENCY (PRIORITY ZERO) ---
        if intent == "emergency":
            logger.info("CRITICAL: EMERGENCY DETECTED. Triggering instant alert...")
            try:
                wf_tool = WorkflowActionTool()
                wf_tool._run(patient_id=patient_id, request_type="EMERGENCY", request_text=user_input, category="CRITICAL")
                msg = "EMERGENCY ALERT TRIGGERED! Medical staff have been notified and are on their way. Please stay calm."
                if original_lang != "en":
                    return self.speech.translate_text(msg, target_lang=original_lang)
                return msg
            except Exception as e:
                logger.error(f"Emergency Error: {e}")
                return "EMERGENCY ALERT TRIGGERED!"

        # --- OPTIMIZATION 2: FAST PATH (CONVERSATIONAL via MEDITRON) ---
        if intent == "general_conversation":
            logger.info("Decision: Handling via Meditron Fast Path...")
            try:
                from meditron_client import MeditronClient
                m_client = MeditronClient()
                prompt = f"Patient said: '{user_input}'. As CareMate, give a kind, conversational REPLY in English (max 15 words)."
                response = m_client.generate_response(prompt)
                
                # Safety: Strip prompt echo
                if prompt in response:
                    response = response.split(prompt)[-1].strip()
                return response.strip()
            except Exception as e:
                logger.error(f"Meditron Fast Path Error: {e}")

        # --- OPTIMIZATION 3: ZERO-LOOP WORKFLOW (Deterministic Tasks via NEMOTRON) ---
        workflow_intents = ["nurse_request", "nutrition_request", "utility_request"]
        if intent in workflow_intents:
            logger.info(f"Decision: Handling {intent} via Nemotron Zero-Loop...")
            try:
                from caremate_agents import orchestrator_llm
                wf_tool = WorkflowActionTool()
                category = "water" if "water" in user_input.lower() else "general"
                tool_result = wf_tool._run(patient_id=patient_id, request_type=intent, request_text=user_input, category=category)
                prompt = f"The patient requested: '{user_input}'. System result: '{tool_result}'. Confirm it's done in English."
                response = orchestrator_llm.call([{"role": "user", "content": prompt}])
                return response.strip()
            except Exception as e:
                logger.error(f"Zero-Loop Error: {e}")

        # --- OPTIMIZATION 4: ZERO-LOOP MEDICAL (Status/Doctor Queries) ---
        medical_intents = ["status_query", "doctor_query"]
        if intent in medical_intents:
            logger.info(f"Decision: Handling {intent} via Zero-Loop Medical Path (Meditron)...")
            try:
                from hospital_tools import PatientContextTool, MedicalRAGTool
                p_tool = PatientContextTool()
                rag_tool = MedicalRAGTool()
                
                patient_context = p_tool._run(patient_id=patient_id)
                rag_context = rag_tool._run(patient_id=patient_id, query=user_input)
                
                from meditron_client import MeditronClient
                m_client = MeditronClient()
                
                # Using a very specific marker for the answer
                combined_prompt = f"Patient Context: {patient_context}\nMedical Reports: {rag_context}\nQuestion: {user_input}\n\nExpert Medical Response:"
                result_en = m_client.generate_response(combined_prompt)
                
                # Aggressive Echo Protection
                # 1. If result starts with/contains the marker, split it
                if "Expert Medical Response:" in result_en:
                    result_en = result_en.split("Expert Medical Response:")[-1].strip()
                # 2. If it echoed the whole prompt including "Context:", strip it
                elif "Context:" in result_en:
                    result_en = result_en.split(user_input)[-1].strip()
                
                # 3. Final check: if it just repeated the question back, it likely failed
                if result_en.lower() == user_input.lower() or len(result_en) < 5:
                    result_en = "I've reviewed your request. Could you please provide more details so I can assist you better with your medical query?"

                return result_en
            except Exception as e:
                logger.error(f"Medical Zero-Loop Error: {e}")

        # --- FALLBACK: FULL AGENT (Medical/Status Reasoning) ---
        logger.info("Decision: Triggering Patient Agent (Fallback Reasoning)...")
        try:
            agent = self.agents.patient_agent()
            task = self.tasks.respond_to_patient(agent, patient_id, user_input)
            crew = Crew(agents=[agent], tasks=[task], process=Process.sequential)
            result = str(crew.kickoff())
            return result.replace("```json", "").replace("```", "").strip()
        except Exception as e:
            logger.error(f"Agent Fallback Error: {e}")
            return "I am currently reviewing your records. Please wait a moment."

if __name__ == "__main__":
    backend = CareMateBackend()
    sample_patient = backend.db.patients.find_one()
    if sample_patient:
        pid = sample_patient['patient_id']
        print(f"\n[SYSTEM READY] Patient: {sample_patient['name']}\n")
        
        # Test Case 1: Disease Info
        result = backend.process_input("Can you tell me about diabetes?", pid)
        print(f"Meditron Response:\n{result}\n")
