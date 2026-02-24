"""
Patient Intelligence Agent Tools
Tools for patient context retrieval, intent classification, and distress detection
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

from ..models import (
    PatientRecord,
    DistressSignals,
    ConversationTurn
)


# ============================================================================
# Tool Input Schemas
# ============================================================================

class PatientRecordRetrievalInput(BaseModel):
    """Input schema for patient record retrieval"""
    hospital_id: str = Field(..., description="Patient's hospital ID")
    bed_number: str = Field(..., description="Patient's bed number")


class ContextSummarizationInput(BaseModel):
    """Input schema for context summarization"""
    patient_record: Dict[str, Any] = Field(..., description="Full patient record")
    query: str = Field(..., description="Patient's current query")


class IntentClassificationInput(BaseModel):
    """Input schema for intent classification"""
    query: str = Field(..., description="Patient query to classify")
    patient_context: str = Field(..., description="Patient context information")


class DistressDetectionInput(BaseModel):
    """Input schema for distress detection"""
    query: str = Field(..., description="Patient query to analyze")
    conversation_history: List[str] = Field(
        default_factory=list, description="Recent conversation history"
    )


class MemoryManagementInput(BaseModel):
    """Input schema for memory operations"""
    action: str = Field(..., description="Action: STORE or RETRIEVE")
    patient_id: str = Field(..., description="Patient hospital ID")
    conversation_data: Optional[Dict[str, Any]] = Field(
        None, description="Data to store (for STORE action)"
    )


# ============================================================================
# Custom Tools for Patient Intelligence Agent
# ============================================================================

class PatientRecordRetrievalTool(BaseTool):
    name: str = "Patient Record Retrieval"
    description: str = (
        "Retrieves patient information from the hospital database using hospital_id and bed_number. "
        "Returns essential patient context including medications, allergies, restrictions, and assigned staff. "
        "Use this at the start of every patient interaction to gather context."
    )
    args_schema: type[BaseModel] = PatientRecordRetrievalInput

    def _run(self, hospital_id: str, bed_number: str) -> str:
        """
        Retrieve patient record from database.
        In production, this would query the actual hospital database.
        """
        # TODO: Replace with actual database query
        # For now, return mock data structure
        
        try:
            # Simulated database query
            patient_record = self._fetch_from_database(hospital_id, bed_number)
            
            if not patient_record:
                return json.dumps({
                    "error": "Patient not found",
                    "hospital_id": hospital_id,
                    "bed_number": bed_number
                })
            
            # Return sanitized patient record (excluding sensitive diagnosis details)
            safe_record = {
                "hospital_id": patient_record.get("hospital_id"),
                "bed_number": patient_record.get("bed_number"),
                "name": patient_record.get("name"),
                "age": patient_record.get("age"),
                "primary_diagnosis": patient_record.get("primary_diagnosis"),
                "medications": patient_record.get("medications", []),
                "allergies": patient_record.get("allergies", []),
                "restrictions": patient_record.get("restrictions", []),
                "primary_nurse_id": patient_record.get("primary_nurse_id"),
                "attending_physician_id": patient_record.get("attending_physician_id"),
                "language_preference": patient_record.get("language_preference", "en")
            }
            
            return json.dumps(safe_record, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Database retrieval failed: {str(e)}",
                "hospital_id": hospital_id
            })

    def _fetch_from_database(self, hospital_id: str, bed_number: str) -> Optional[Dict]:
        """
        Simulated database fetch. Replace with actual implementation.
        Example using SQLAlchemy:
        
        from sqlalchemy import create_engine, select
        from .database import patients_table
        
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(
                select(patients_table).where(
                    patients_table.c.hospital_id == hospital_id,
                    patients_table.c.bed_number == bed_number
                )
            ).fetchone()
            return dict(result) if result else None
        """
        # Mock implementation
        return {
            "hospital_id": hospital_id,
            "bed_number": bed_number,
            "name": "Sample Patient",
            "age": 65,
            "primary_diagnosis": "Post-surgical recovery",
            "medications": ["Medication A 50mg", "Medication B 10mg"],
            "allergies": ["Penicillin"],
            "restrictions": ["Low-sodium diet", "Limited mobility"],
            "primary_nurse_id": "NURSE_001",
            "attending_physician_id": "DR_001",
            "language_preference": "en"
        }


class ContextSummarizationTool(BaseTool):
    name: str = "Context Summarization"
    description: str = (
        "Creates a concise 2-3 sentence summary of relevant patient information based on their query. "
        "Focuses only on context needed to understand the current request. "
        "Avoids medical jargon and sensitive details."
    )
    args_schema: type[BaseModel] = ContextSummarizationInput

    def _run(self, patient_record: Dict[str, Any], query: str) -> str:
        """
        Summarize patient context relevant to the query.
        """
        try:
            # Extract key information
            name = patient_record.get("name", "Patient")
            age = patient_record.get("age", "unknown age")
            medications = patient_record.get("medications", [])
            allergies = patient_record.get("allergies", [])
            restrictions = patient_record.get("restrictions", [])
            
            # Build context summary
            summary_parts = [
                f"{name}, age {age}, is currently in bed {patient_record.get('bed_number', 'unknown')}."
            ]
            
            # Add medication info if query mentions medication/pain/symptoms
            query_lower = query.lower()
            if any(word in query_lower for word in ["medication", "medicine", "pill", "pain", "hurt"]):
                if medications:
                    summary_parts.append(f"Currently taking: {', '.join(medications)}.")
                if allergies:
                    summary_parts.append(f"Allergies: {', '.join(allergies)}.")
            
            # Add restrictions if query mentions food/activity
            if any(word in query_lower for word in ["food", "eat", "meal", "walk", "move", "exercise"]):
                if restrictions:
                    summary_parts.append(f"Restrictions: {', '.join(restrictions)}.")
            
            # If query is about staff
            if any(word in query_lower for word in ["nurse", "doctor", "staff"]):
                summary_parts.append(
                    f"Primary nurse: {patient_record.get('primary_nurse_id', 'unassigned')}."
                )
            
            return " ".join(summary_parts)
            
        except Exception as e:
            return f"Error summarizing context: {str(e)}"


class IntentClassificationTool(BaseTool):
    name: str = "Intent Classification"
    description: str = (
        "Classifies patient queries into MEDICAL, NON_MEDICAL, or EMERGENCY categories. "
        "Returns the category, confidence score, and reasoning. "
        "EMERGENCY: life-threatening symptoms. "
        "MEDICAL: health-related requests needing staff. "
        "NON_MEDICAL: comfort, information, environmental requests."
    )
    args_schema: type[BaseModel] = IntentClassificationInput

    def _run(self, query: str, patient_context: str) -> str:
        """
        Classify patient query intent using rule-based + LLM approach.
        """
        query_lower = query.lower()
        
        # Emergency keywords - highest priority
        emergency_keywords = [
            "chest pain", "can't breathe", "can not breathe", "cannot breathe",
            "severe bleeding", "unconscious", "heart attack", "stroke",
            "choking", "severe pain", "dying"
        ]
        
        if any(keyword in query_lower for keyword in emergency_keywords):
            return json.dumps({
                "category": "EMERGENCY",
                "confidence": 0.99,
                "reasoning": "Query contains emergency keywords indicating immediate medical attention needed",
                "keywords_matched": [kw for kw in emergency_keywords if kw in query_lower]
            }, indent=2)
        
        # Medical keywords
        medical_keywords = [
            "pain", "hurt", "medication", "medicine", "pill", "doctor", "nurse",
            "sick", "nausea", "dizzy", "fever", "symptom", "treatment",
            "injection", "iv", "blood pressure", "temperature"
        ]
        
        medical_matches = [kw for kw in medical_keywords if kw in query_lower]
        
        if medical_matches:
            return json.dumps({
                "category": "MEDICAL",
                "confidence": 0.85,
                "reasoning": "Query contains medical-related keywords requiring staff attention",
                "keywords_matched": medical_matches
            }, indent=2)
        
        # Non-medical keywords
        non_medical_keywords = [
            "water", "temperature", "tv", "television", "light", "blanket",
            "pillow", "room", "visitor", "time", "date", "weather",
            "bathroom", "toilet", "window", "curtain"
        ]
        
        non_medical_matches = [kw for kw in non_medical_keywords if kw in query_lower]
        
        if non_medical_matches:
            return json.dumps({
                "category": "NON_MEDICAL",
                "confidence": 0.90,
                "reasoning": "Query is about comfort or environmental controls",
                "keywords_matched": non_medical_matches
            }, indent=2)
        
        # Default to MEDICAL for safety if uncertain
        return json.dumps({
            "category": "MEDICAL",
            "confidence": 0.60,
            "reasoning": "Unable to definitively classify - defaulting to MEDICAL for safety",
            "keywords_matched": []
        }, indent=2)


class DistressDetectionTool(BaseTool):
    name: str = "Distress Detection"
    description: str = (
        "Analyzes patient query and conversation history for signs of distress. "
        "Detects repeated requests, panic words, urgency indicators. "
        "Returns distress level (NONE/LOW/MEDIUM/HIGH) and recommended action."
    )
    args_schema: type[BaseModel] = DistressDetectionInput

    def _run(self, query: str, conversation_history: List[str] = None) -> str:
        """
        Detect patient distress signals.
        """
        if conversation_history is None:
            conversation_history = []
        
        query_lower = query.lower()
        distress_indicators = []
        distress_level = "NONE"
        
        # High distress keywords
        high_distress_words = [
            "help", "please help", "emergency", "urgent", "severe",
            "unbearable", "can't take it", "worse", "getting worse"
        ]
        
        # Medium distress keywords
        medium_distress_words = [
            "uncomfortable", "need", "please", "soon", "waiting",
            "still", "again", "repeatedly"
        ]
        
        # Check for high distress
        high_matches = [word for word in high_distress_words if word in query_lower]
        if high_matches:
            distress_level = "HIGH"
            distress_indicators.extend(high_matches)
        
        # Check for repeated requests (same topic in history)
        if conversation_history and len(conversation_history) >= 2:
            # Simple repetition detection
            recent_topics = [h.lower() for h in conversation_history[-3:]]
            if any(query_lower in topic or topic in query_lower for topic in recent_topics):
                distress_level = "MEDIUM" if distress_level == "NONE" else distress_level
                distress_indicators.append("repeated_request")
        
        # Check for medium distress if not high
        if distress_level == "NONE":
            medium_matches = [word for word in medium_distress_words if word in query_lower]
            if medium_matches:
                distress_level = "LOW"
                distress_indicators.extend(medium_matches)
        
        # Recommend action
        recommended_action = {
            "HIGH": "Escalate to nurse immediately, prioritize response",
            "MEDIUM": "Flag for nurse attention, expedite approval process",
            "LOW": "Note in log, standard processing",
            "NONE": "Standard processing"
        }.get(distress_level, "Standard processing")
        
        return json.dumps({
            "distress_detected": distress_level != "NONE",
            "distress_level": distress_level,
            "indicators": distress_indicators,
            "recommended_action": recommended_action,
            "conversation_history_length": len(conversation_history)
        }, indent=2)


class MemoryManagementTool(BaseTool):
    name: str = "Memory Management"
    description: str = (
        "Stores and retrieves conversation history for patients. "
        "Actions: STORE (save new interaction) or RETRIEVE (get recent history). "
        "Maintains last 10 interactions per patient for context continuity."
    )
    args_schema: type[BaseModel] = MemoryManagementInput

    def _run(
        self,
        action: str,
        patient_id: str,
        conversation_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Manage conversation memory.
        In production, use Redis or similar for fast access.
        """
        # TODO: Replace with Redis implementation
        # For now, simulate memory operations
        
        if action.upper() == "STORE":
            if not conversation_data:
                return json.dumps({"error": "No conversation data provided for STORE action"})
            
            # Simulated store operation
            stored_data = {
                "patient_id": patient_id,
                "timestamp": datetime.utcnow().isoformat(),
                "query": conversation_data.get("query", ""),
                "response": conversation_data.get("response", ""),
                "intent": conversation_data.get("intent", ""),
                "resolved": conversation_data.get("resolved", False)
            }
            
            # In production: store to Redis with TTL
            # redis_client.lpush(f"conversation:{patient_id}", json.dumps(stored_data))
            # redis_client.ltrim(f"conversation:{patient_id}", 0, 9)  # Keep last 10
            
            return json.dumps({
                "action": "STORED",
                "patient_id": patient_id,
                "stored_at": stored_data["timestamp"]
            }, indent=2)
        
        elif action.upper() == "RETRIEVE":
            # Simulated retrieve operation
            # In production: fetch from Redis
            # history = redis_client.lrange(f"conversation:{patient_id}", 0, 9)
            
            # Mock history for demonstration
            mock_history = [
                {"query": "Can I have water?", "response": "I'll let your nurse know.", "timestamp": "2026-02-04T10:00:00"},
                {"query": "Is the doctor coming?", "response": "Your doctor is scheduled for rounds at 2 PM.", "timestamp": "2026-02-04T10:05:00"}
            ]
            
            return json.dumps({
                "action": "RETRIEVED",
                "patient_id": patient_id,
                "history": mock_history,
                "count": len(mock_history)
            }, indent=2)
        
        else:
            return json.dumps({"error": f"Invalid action: {action}. Use STORE or RETRIEVE"})
