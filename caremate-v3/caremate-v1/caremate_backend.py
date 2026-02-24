"""
CareMate Backend - Agentic AI-Powered Hospital Assistant
Complete implementation using CrewAI with two-agent architecture
Integrated with Sarvam AI for speech and Google Gemini for domain intelligence
"""

import os
import json
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

# CrewAI imports
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# LangChain for additional tooling
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI

# MongoDB for data persistence
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# FastAPI for REST API
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as PydanticBaseModel

# Sarvam AI client
import requests


# ============================================================================
# CONFIGURATION & ENVIRONMENT SETUP
# ============================================================================

class Config:
    """Centralized configuration for CareMate"""
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    
    # MongoDB Configuration
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    DATABASE_NAME: str = "caremate_db"
    
    # Sarvam AI Configuration
    SARVAM_BASE_URL: str = "https://api.sarvam.ai"
    SARVAM_STT_MODEL: str = "saarika:v2"  # Speech-to-text model
    SARVAM_TTS_MODEL: str = "bulbul:v2"   # Text-to-speech model
    SARVAM_DEFAULT_VOICE: str = "meera"   # Default speaker
    
    # System Configuration
    DEFAULT_LANGUAGE: str = "hi-IN"  # Hindi as default
    MAX_CONTEXT_HISTORY: int = 10
    EMERGENCY_KEYWORDS: List[str] = [
        "emergency", "help", "urgent", "pain", "breathing", "chest",
        "आपातकाल", "मदद", "तत्काल", "दर्द", "सांस", "छाती"
    ]
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        if not cls.SARVAM_API_KEY:
            raise ValueError("SARVAM_API_KEY environment variable is required")


# ============================================================================
# DATA MODELS
# ============================================================================

class IntentCategory(str, Enum):
    """Patient request intent categories"""
    NON_MEDICAL = "non_medical"
    MEDICAL = "medical"
    EMERGENCY = "emergency"


class UrgencyLevel(str, Enum):
    """Request urgency levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PatientContext(BaseModel):
    """Patient context information"""
    hospital_id: str = Field(..., description="Hospital patient ID")
    room_number: str = Field(..., description="Room number")
    bed_number: str = Field(..., description="Bed number")
    name: Optional[str] = None
    age: Optional[int] = None
    diagnosis: Optional[str] = None
    current_medications: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    doctor_assigned: Optional[str] = None
    nurse_assigned: Optional[str] = None
    admission_date: Optional[str] = None


class PatientQuery(BaseModel):
    """Patient query input"""
    audio_base64: str = Field(..., description="Base64 encoded audio")
    hospital_id: str
    room_number: str
    bed_number: str
    timestamp: Optional[str] = None


class IntentAnalysis(BaseModel):
    """Intent analysis result"""
    intent_category: IntentCategory
    urgency_level: UrgencyLevel
    is_emergency: bool = False
    distress_detected: bool = False
    keywords_detected: List[str] = []
    confidence_score: float = Field(ge=0.0, le=1.0)


class ResponseDecision(BaseModel):
    """Response decision from orchestrator"""
    can_respond_directly: bool
    requires_approval: bool
    requires_escalation: bool
    response_text: str
    notification_required: bool
    notification_target: Optional[str] = None  # "nurse" or "doctor"


class InteractionLog(BaseModel):
    """Interaction logging"""
    interaction_id: str
    patient_id: str
    timestamp: str
    query_text: str
    intent_analysis: IntentAnalysis
    response_decision: ResponseDecision
    audio_response_base64: Optional[str] = None
    language_detected: Optional[str] = None


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class DatabaseManager:
    """MongoDB database manager for CareMate"""
    
    def __init__(self):
        self.client = MongoClient(Config.MONGODB_URI)
        self.db = self.client[Config.DATABASE_NAME]
        self._initialize_collections()
    
    def _initialize_collections(self):
        """Initialize required collections"""
        collections = [
            "patients",
            "interactions",
            "escalations",
            "approvals",
            "audit_logs"
        ]
        existing = self.db.list_collection_names()
        for collection in collections:
            if collection not in existing:
                self.db.create_collection(collection)
    
    def get_patient_record(self, hospital_id: str) -> Optional[Dict]:
        """Retrieve patient record"""
        return self.db.patients.find_one({"hospital_id": hospital_id})
    
    def save_interaction(self, interaction: InteractionLog):
        """Save interaction to database"""
        self.db.interactions.insert_one(interaction.dict())
    
    def get_interaction_history(self, patient_id: str, limit: int = 10) -> List[Dict]:
        """Get recent interaction history"""
        return list(self.db.interactions.find(
            {"patient_id": patient_id}
        ).sort("timestamp", -1).limit(limit))
    
    def create_escalation(self, escalation_data: Dict):
        """Create escalation record"""
        escalation_data["created_at"] = datetime.now().isoformat()
        escalation_data["status"] = "pending"
        return self.db.escalations.insert_one(escalation_data)
    
    def log_audit(self, event_type: str, data: Dict):
        """Log audit event"""
        audit_entry = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.db.audit_logs.insert_one(audit_entry)


# ============================================================================
# SARVAM AI CLIENT
# ============================================================================

class SarvamAIClient:
    """Client for Sarvam AI speech services"""
    
    def __init__(self):
        self.base_url = Config.SARVAM_BASE_URL
        self.api_key = Config.SARVAM_API_KEY
        self.headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def speech_to_text_translate(self, audio_base64: str, language_code: str = "unknown") -> Dict:
        """
        Convert speech to English text using Sarvam's STTT API
        
        Args:
            audio_base64: Base64 encoded audio
            language_code: Language code (use "unknown" for auto-detection)
        
        Returns:
            Dictionary with transcript and detected language
        """
        endpoint = f"{self.base_url}/speech-to-text-translate"
        
        payload = {
            "language_code": language_code,
            "model": Config.SARVAM_STT_MODEL,
            "audio": audio_base64
        }
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Sarvam STT API error: {str(e)}")
    
    def text_to_speech(self, text: str, language_code: str = "hi-IN", 
                       speaker: str = None) -> str:
        """
        Convert text to speech using Sarvam's TTS API
        
        Args:
            text: Text to convert
            language_code: Target language
            speaker: Voice speaker (default: meera)
        
        Returns:
            Base64 encoded audio
        """
        endpoint = f"{self.base_url}/text-to-speech"
        
        payload = {
            "inputs": [text],
            "target_language_code": language_code,
            "speaker": speaker or Config.SARVAM_DEFAULT_VOICE,
            "model": Config.SARVAM_TTS_MODEL,
            "enable_preprocessing": True
        }
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["audios"][0]  # Return first audio
        except requests.exceptions.RequestException as e:
            raise Exception(f"Sarvam TTS API error: {str(e)}")


# ============================================================================
# CREWAI CUSTOM TOOLS
# ============================================================================

class PatientRecordRetrievalTool(BaseTool):
    """Tool to retrieve patient medical records"""
    
    name: str = "Patient Record Retrieval"
    description: str = """
    Retrieves patient medical records from the database.
    Input should be a JSON string with 'hospital_id' field.
    Returns patient context including diagnosis, medications, allergies.
    """
    
    def _run(self, hospital_id: str) -> str:
        """Execute the tool"""
        try:
            db = DatabaseManager()
            record = db.get_patient_record(hospital_id)
            
            if not record:
                return json.dumps({"error": "Patient record not found"})
            
            # Remove MongoDB _id field
            record.pop('_id', None)
            return json.dumps(record, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


class ContextSummarizationTool(BaseTool):
    """Tool to summarize patient context"""
    
    name: str = "Context Summarization"
    description: str = """
    Summarizes patient context into a concise, safe format.
    Input should be a JSON string with patient record data.
    Returns a non-diagnostic summary suitable for patient interaction.
    """
    
    def _run(self, patient_data: str) -> str:
        """Execute the tool"""
        try:
            data = json.loads(patient_data)
            
            summary = {
                "patient_name": data.get("name", "Patient"),
                "room_location": f"Room {data.get('room_number', 'N/A')}, Bed {data.get('bed_number', 'N/A')}",
                "doctor": data.get("doctor_assigned", "Not assigned"),
                "admission_info": f"Admitted on {data.get('admission_date', 'N/A')}",
                "has_medications": len(data.get("current_medications", [])) > 0,
                "has_allergies": len(data.get("allergies", [])) > 0
            }
            
            return json.dumps(summary, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


class IntentClassificationTool(BaseTool):
    """Tool to classify patient intent and urgency"""
    
    name: str = "Intent Classification"
    description: str = """
    Classifies patient query into intent category and urgency level.
    Input should be the translated patient query text.
    Returns intent_category (non_medical/medical/emergency) and urgency_level.
    """
    
    def _run(self, query_text: str) -> str:
        """Execute the tool"""
        try:
            query_lower = query_text.lower()
            
            # Emergency detection
            is_emergency = any(keyword in query_lower for keyword in Config.EMERGENCY_KEYWORDS)
            
            # Intent classification (simplified - in production, use ML model)
            medical_keywords = ["medicine", "medication", "doctor", "nurse", "pain", "treatment"]
            non_medical_keywords = ["food", "water", "bathroom", "visitor", "tv", "light"]
            
            if is_emergency:
                intent = IntentCategory.EMERGENCY
                urgency = UrgencyLevel.CRITICAL
            elif any(keyword in query_lower for keyword in medical_keywords):
                intent = IntentCategory.MEDICAL
                urgency = UrgencyLevel.MEDIUM
            elif any(keyword in query_lower for keyword in non_medical_keywords):
                intent = IntentCategory.NON_MEDICAL
                urgency = UrgencyLevel.LOW
            else:
                intent = IntentCategory.NON_MEDICAL
                urgency = UrgencyLevel.LOW
            
            result = IntentAnalysis(
                intent_category=intent,
                urgency_level=urgency,
                is_emergency=is_emergency,
                distress_detected=is_emergency,
                keywords_detected=[kw for kw in Config.EMERGENCY_KEYWORDS if kw in query_lower],
                confidence_score=0.85
            )
            
            return result.json()
        except Exception as e:
            return json.dumps({"error": str(e)})


class DistressDetectionTool(BaseTool):
    """Tool to detect distress or emergency signals"""
    
    name: str = "Distress Detection"
    description: str = """
    Detects distress signals, abnormal phrasing, or urgent patterns.
    Input should be the patient query text.
    Returns distress score and detected patterns.
    """
    
    def _run(self, query_text: str) -> str:
        """Execute the tool"""
        try:
            query_lower = query_text.lower()
            
            distress_indicators = {
                "pain_words": ["pain", "hurt", "ache", "दर्द"],
                "urgency_words": ["urgent", "emergency", "help", "quick", "मदद", "तत्काल"],
                "breathing_words": ["breathe", "breath", "air", "सांस"],
                "repetition": len(query_text.split()) < 10 and len(set(query_text.split())) < 5
            }
            
            distress_score = 0.0
            detected_patterns = []
            
            for category, words in distress_indicators.items():
                if category == "repetition":
                    if words:  # If repetition detected
                        distress_score += 0.3
                        detected_patterns.append("repetitive_speech")
                else:
                    if any(word in query_lower for word in words):
                        distress_score += 0.25
                        detected_patterns.append(category)
            
            result = {
                "distress_score": min(distress_score, 1.0),
                "distress_detected": distress_score > 0.5,
                "patterns": detected_patterns
            }
            
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


class MemoryManagementTool(BaseTool):
    """Tool to manage short-term interaction memory"""
    
    name: str = "Memory Management"
    description: str = """
    Stores and retrieves recent patient interactions.
    Input should be a JSON with 'action' (store/retrieve) and 'patient_id'.
    Maintains conversational continuity.
    """
    
    def _run(self, input_data: str) -> str:
        """Execute the tool"""
        try:
            data = json.loads(input_data)
            action = data.get("action")
            patient_id = data.get("patient_id")
            
            db = DatabaseManager()
            
            if action == "retrieve":
                history = db.get_interaction_history(patient_id, limit=5)
                return json.dumps({"history": history}, indent=2)
            elif action == "store":
                interaction_data = data.get("interaction_data", {})
                db.save_interaction(InteractionLog(**interaction_data))
                return json.dumps({"status": "stored"})
            else:
                return json.dumps({"error": "Invalid action"})
                
        except Exception as e:
            return json.dumps({"error": str(e)})


class PolicyEvaluationTool(BaseTool):
    """Tool to evaluate hospital policies"""
    
    name: str = "Policy Evaluation"
    description: str = """
    Applies hospital rules and safety constraints.
    Input should be intent analysis and patient context.
    Returns policy compliance and action requirements.
    """
    
    def _run(self, input_data: str) -> str:
        """Execute the tool"""
        try:
            data = json.loads(input_data)
            intent = data.get("intent_category")
            
            policies = {
                "no_autonomous_medical_advice": True,
                "medication_requires_approval": True,
                "emergency_immediate_escalation": True,
                "non_medical_can_be_automated": True
            }
            
            result = {
                "can_respond_directly": intent == "non_medical",
                "requires_approval": intent == "medical",
                "requires_escalation": intent == "emergency",
                "applicable_policies": []
            }
            
            if intent == "medical":
                result["applicable_policies"].append("medication_requires_approval")
            if intent == "emergency":
                result["applicable_policies"].append("emergency_immediate_escalation")
            
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


class NotificationTool(BaseTool):
    """Tool to send notifications to staff"""
    
    name: str = "Staff Notification"
    description: str = """
    Sends alerts to nurses or doctors when escalation is required.
    Input should include notification_target (nurse/doctor) and message.
    """
    
    def _run(self, notification_data: str) -> str:
        """Execute the tool"""
        try:
            data = json.loads(notification_data)
            target = data.get("target")
            message = data.get("message")
            priority = data.get("priority", "normal")
            
            # In production, this would integrate with dashboard/messaging system
            notification = {
                "target": target,
                "message": message,
                "priority": priority,
                "timestamp": datetime.now().isoformat(),
                "status": "sent"
            }
            
            # Log to database
            db = DatabaseManager()
            db.log_audit("notification_sent", notification)
            
            return json.dumps({"status": "notification_sent", "details": notification})
        except Exception as e:
            return json.dumps({"error": str(e)})


class AuditLoggingTool(BaseTool):
    """Tool to log decisions and actions"""
    
    name: str = "Audit Logging"
    description: str = """
    Records all decisions, responses, and escalations for transparency.
    Input should be the event type and associated data.
    """
    
    def _run(self, log_data: str) -> str:
        """Execute the tool"""
        try:
            data = json.loads(log_data)
            event_type = data.get("event_type")
            event_data = data.get("data", {})
            
            db = DatabaseManager()
            db.log_audit(event_type, event_data)
            
            return json.dumps({"status": "logged", "event_type": event_type})
        except Exception as e:
            return json.dumps({"error": str(e)})


# ============================================================================
# CREWAI AGENTS
# ============================================================================

def create_patient_intelligence_agent() -> Agent:
    """
    Create the Patient Intelligence Agent
    Responsible for understanding patient context, intent, and urgency
    """
    
    # Initialize Gemini LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=Config.GEMINI_API_KEY,
        temperature=0.3,
        max_tokens=1000
    )
    
    # Agent tools
    tools = [
        PatientRecordRetrievalTool(),
        ContextSummarizationTool(),
        IntentClassificationTool(),
        DistressDetectionTool(),
        MemoryManagementTool()
    ]
    
    agent = Agent(
        role="Patient Intelligence Specialist",
        goal="Understand patient context, intent, and urgency using available data",
        backstory="""You are an expert patient intelligence analyst in a hospital setting.
        Your role is to deeply understand each patient's query by:
        1. Retrieving their medical context from records
        2. Analyzing their intent and emotional state
        3. Detecting urgency and distress signals
        4. Maintaining conversation memory
        
        You never make medical decisions - you only analyze and prepare information
        for the decision-making system. You are thorough, empathetic, and precise.""",
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=True  # Enable agent memory for context retention
    )
    
    return agent


def create_orchestrator_policy_agent() -> Agent:
    """
    Create the Central Orchestrator & Policy Agent
    Responsible for decision-making based on policies and safety constraints
    """
    
    # Initialize Gemini LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=Config.GEMINI_API_KEY,
        temperature=0.5,
        max_tokens=1500
    )
    
    # Agent tools
    tools = [
        PolicyEvaluationTool(),
        NotificationTool(),
        AuditLoggingTool()
    ]
    
    agent = Agent(
        role="Central Decision Orchestrator",
        goal="Make safe, policy-compliant decisions on patient requests",
        backstory="""You are the central decision-making brain of the CareMate system.
        Your responsibility is critical:
        
        STRICT RULES YOU MUST FOLLOW:
        1. NEVER provide autonomous medical advice
        2. ALL medication requests MUST be approved by staff
        3. ALL emergencies MUST be escalated immediately
        4. Non-medical requests can be handled directly
        5. Always log decisions for auditability
        6. Patient safety is the absolute priority
        
        You evaluate inputs from the Patient Intelligence Agent, apply hospital
        policies, and decide the appropriate action. You generate safe, empathetic
        responses and ensure proper escalation when needed.
        
        You are calm, reliable, and unwavering in following safety protocols.""",
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=True
    )
    
    return agent


# ============================================================================
# CREWAI CREW & WORKFLOW
# ============================================================================

class CareMateCrewOrchestrator:
    """Main orchestrator for CareMate two-agent crew"""
    
    def __init__(self):
        self.patient_intelligence_agent = create_patient_intelligence_agent()
        self.orchestrator_agent = create_orchestrator_policy_agent()
        self.sarvam_client = SarvamAIClient()
        self.db = DatabaseManager()
    
    def process_patient_query(self, patient_query: PatientQuery) -> Dict:
        """
        Process a complete patient query through the two-agent system
        
        Args:
            patient_query: PatientQuery object with audio and metadata
        
        Returns:
            Complete response with text and audio
        """
        
        # Step 1: Speech to Text Translation (Sarvam AI)
        print("\\n=== STEP 1: Speech to Text Translation ===")
        stt_result = self.sarvam_client.speech_to_text_translate(
            patient_query.audio_base64,
            language_code="unknown"  # Auto-detect language
        )
        
        query_text_english = stt_result.get("transcript", "")
        detected_language = stt_result.get("language_code", Config.DEFAULT_LANGUAGE)
        
        print(f"Detected Language: {detected_language}")
        print(f"Translated Query: {query_text_english}")
        
        # Step 2: Patient Intelligence Analysis
        print("\\n=== STEP 2: Patient Intelligence Analysis ===")
        
        intelligence_task = Task(
            description=f"""
            Analyze the following patient query and provide comprehensive intelligence:
            
            Patient Information:
            - Hospital ID: {patient_query.hospital_id}
            - Room: {patient_query.room_number}
            - Bed: {patient_query.bed_number}
            
            Patient Query (English): {query_text_english}
            
            Your tasks:
            1. Retrieve patient record using hospital ID
            2. Summarize patient context (non-diagnostic)
            3. Classify the intent (non_medical/medical/emergency)
            4. Detect any distress or urgency
            5. Retrieve recent interaction history
            
            Provide a structured analysis that will be used for decision-making.
            """,
            agent=self.patient_intelligence_agent,
            expected_output="""A comprehensive intelligence report containing:
            - Patient context summary
            - Intent classification
            - Urgency assessment
            - Distress detection results
            - Recent interaction summary"""
        )
        
        intelligence_crew = Crew(
            agents=[self.patient_intelligence_agent],
            tasks=[intelligence_task],
            process=Process.sequential,
            verbose=True
        )
        
        intelligence_result = intelligence_crew.kickoff()
        
        # Step 3: Policy-Based Decision Making
        print("\\n=== STEP 3: Policy-Based Decision Making ===")
        
        decision_task = Task(
            description=f"""
            Based on the patient intelligence analysis, make a safe decision:
            
            Intelligence Report:
            {intelligence_result}
            
            Patient Query: {query_text_english}
            
            Your tasks:
            1. Evaluate applicable hospital policies
            2. Determine if you can respond directly or need approval/escalation
            3. Generate appropriate response text (empathetic, clear, safe)
            4. Send notifications to staff if required
            5. Log all decisions to audit trail
            
            Remember:
            - NEVER give medical advice
            - Medication requests NEED approval
            - Emergencies NEED immediate escalation
            - Be warm and reassuring in your response
            
            Provide the final decision and response.
            """,
            agent=self.orchestrator_agent,
            expected_output="""A complete decision package containing:
            - Policy evaluation results
            - Response decision (direct/approval/escalation)
            - Generated response text for the patient
            - Notification status (if applicable)
            - Audit log confirmation"""
        )
        
        decision_crew = Crew(
            agents=[self.orchestrator_agent],
            tasks=[decision_task],
            process=Process.sequential,
            verbose=True
        )
        
        decision_result = decision_crew.kickoff()
        
        # Step 4: Extract Response Text
        # In production, parse the structured output properly
        response_text = self._extract_response_from_result(str(decision_result))
        
        # Step 5: Text to Speech (Sarvam AI)
        print("\\n=== STEP 4: Text to Speech Conversion ===")
        audio_response = self.sarvam_client.text_to_speech(
            text=response_text,
            language_code=detected_language
        )
        
        # Step 6: Save Interaction
        print("\\n=== STEP 5: Saving Interaction ===")
        interaction_log = InteractionLog(
            interaction_id=f"INT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            patient_id=patient_query.hospital_id,
            timestamp=datetime.now().isoformat(),
            query_text=query_text_english,
            intent_analysis=IntentAnalysis(
                intent_category=IntentCategory.NON_MEDICAL,  # Parse from result
                urgency_level=UrgencyLevel.LOW,  # Parse from result
                is_emergency=False,
                distress_detected=False,
                keywords_detected=[],
                confidence_score=0.85
            ),
            response_decision=ResponseDecision(
                can_respond_directly=True,
                requires_approval=False,
                requires_escalation=False,
                response_text=response_text,
                notification_required=False
            ),
            audio_response_base64=audio_response,
            language_detected=detected_language
        )
        
        self.db.save_interaction(interaction_log)
        
        # Return complete response
        return {
            "interaction_id": interaction_log.interaction_id,
            "query_text_english": query_text_english,
            "detected_language": detected_language,
            "intelligence_analysis": str(intelligence_result),
            "decision_result": str(decision_result),
            "response_text": response_text,
            "audio_response_base64": audio_response,
            "timestamp": interaction_log.timestamp
        }
    
    def _extract_response_from_result(self, result_text: str) -> str:
        """
        Extract the final response text from crew result
        In production, use structured output parsing
        """
        # Simple extraction - in production, use better parsing
        lines = result_text.split('\\n')
        for i, line in enumerate(lines):
            if 'response' in line.lower() and i + 1 < len(lines):
                return lines[i + 1].strip()
        
        # Fallback
        return "I understand your request. A staff member will assist you shortly."


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="CareMate Backend API",
    description="Agentic AI-Powered Hospital Assistant",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = None

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    global orchestrator
    Config.validate()
    orchestrator = CareMateCrewOrchestrator()
    print("\\n✅ CareMate Backend initialized successfully!")


class QueryRequest(PydanticBaseModel):
    """API request model"""
    audio_base64: str
    hospital_id: str
    room_number: str
    bed_number: str


@app.post("/api/v1/query")
async def process_query(request: QueryRequest, background_tasks: BackgroundTasks):
    """
    Process patient query endpoint
    """
    try:
        patient_query = PatientQuery(
            audio_base64=request.audio_base64,
            hospital_id=request.hospital_id,
            room_number=request.room_number,
            bed_number=request.bed_number,
            timestamp=datetime.now().isoformat()
        )
        
        # Process query through the crew
        result = orchestrator.process_patient_query(patient_query)
        
        return {
            "status": "success",
            "data": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.get("/api/v1/patient/{hospital_id}")
async def get_patient_info(hospital_id: str):
    """Get patient information"""
    db = DatabaseManager()
    record = db.get_patient_record(hospital_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    record.pop('_id', None)
    return record


@app.get("/api/v1/interactions/{patient_id}")
async def get_interaction_history(patient_id: str, limit: int = 10):
    """Get patient interaction history"""
    db = DatabaseManager()
    history = db.get_interaction_history(patient_id, limit)
    
    # Remove MongoDB _id fields
    for item in history:
        item.pop('_id', None)
    
    return {"interactions": history}


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║          CareMate Backend - Starting Server              ║
    ║                                                           ║
    ║  Agentic AI-Powered Hospital Assistant                   ║
    ║  Two-Agent CrewAI Architecture                           ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Run FastAPI server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
