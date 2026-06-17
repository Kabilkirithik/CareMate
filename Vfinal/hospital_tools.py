import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field
from pymongo import MongoClient
from dotenv import load_dotenv
from rag_pipeline import CareMateRAG

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "caremate_db"

# --- Schema Definitions for Tools ---

class PatientIDInput(BaseModel):
    patient_id: str = Field(..., description="The unique ID of the patient.")

class RAGQueryInput(BaseModel):
    patient_id: str = Field(..., description="The unique ID of the patient.")
    query: str = Field(..., description="The medical question or search term.")

class WorkflowInput(BaseModel):
    patient_id: str = Field(..., description="The unique ID of the patient.")
    request_type: str = Field(..., description="Type: NURSE, DOCTOR, NUTRITION, UTILITY, STATUS")
    category: Optional[str] = Field(None, description="Sub-category (e.g., blanket, water, pain)")
    request_text: str = Field(..., description="The original text from the patient.")

# --- Tool Implementations ---

class PatientContextTool:
    def _run(self, patient_id: str) -> str:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        patient = db.patients.find_one({"patient_id": patient_id}, {"_id": 0})
        if not patient:
            return f"Error: Patient {patient_id} not found."
            
        visit = db.visits.find_one({"patient_id": patient_id, "status": "ACTIVE"}, {"_id": 0})
        if not visit:
            # Fallback to last visit if no active one
            visits = list(db.visits.find({"patient_id": patient_id}).sort("admitted_at", -1).limit(1))
            visit = visits[0] if visits else {}
            visit_status = "Historical"
        else:
            visit_status = "Active"

        context = f"Patient: {patient['name']} (Age: {patient['age']}, Blood: {patient['blood_group']})\n"
        context += f"Allergies: {', '.join(patient.get('allergies', []))}\n"
        context += f"Current Status: {visit_status} Visit\n"
        context += f"Room: {visit.get('room_id', 'N/A')}, Bed: {visit.get('bed_id', 'N/A')}\n"
        context += f"Assigned Doctor ID: {visit.get('assigned_doctor', 'N/A')}\n"
        
        return context

class MedicalRAGTool:
    def _run(self, patient_id: str, query: str) -> str:
        rag = CareMateRAG()
        results = rag.query_reports(query, patient_id, n_results=2)
        
        if not results['documents'] or not results['documents'][0]:
            return "No matching medical records found for this query."
            
        return "\n---\n".join(results['documents'][0])

class SummaryContextTool:
    def _run(self, patient_id: str) -> str:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        summaries = list(db.summaries.find({"patient_id": patient_id}).sort("generated_at", -1).limit(1))
        if not summaries:
            return "No previous clinical summaries found."
            
        s = summaries[0]
        return f"Recent Summary (Date: {s['generated_at']}):\nConcerns: {s['patient_concerns']}\nHistory: {s['request_history']}\nDoctor Notes: {s['doctor_notes']}"

class WorkflowActionTool:
    def _run(self, patient_id: str, request_type: str, request_text: str, category: Optional[str] = None) -> str:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        # 1. Get Visit ID
        visit = db.visits.find_one({"patient_id": patient_id, "status": "ACTIVE"})
        v_id = visit['visit_id'] if visit else "Unknown"
        
        # 2. Create Request record
        req_id = str(uuid.uuid4())
        # Priority: EMERGENCY > DOCTOR/NURSE > others
        _priority_map = {
            "EMERGENCY": "CRITICAL",
            "DOCTOR": "HIGH",
            "NURSE": "HIGH",
            "NUTRITION": "MEDIUM",
            "UTILITY": "LOW",
            "STATUS": "LOW",
        }
        priority = _priority_map.get(request_type.upper(), "MEDIUM")
        
        request_doc = {
            "request_id": req_id,
            "patient_id": patient_id,
            "visit_id": v_id,
            "request_type": request_type.upper(),
            "category": category,
            "request_text": request_text,
            "status": "REQUESTED",
            "created_at": datetime.now(),
            "priority": priority,
        }
        db.requests.insert_one(request_doc)
        
        # 3. Log Event
        db.visit_events.insert_one({
            "event_id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "visit_id": v_id,
            "event_type": "request_created",
            "actor": "CareMate_AI",
            "description": f"New {request_type} request: {request_text[:50]}...",
            "timestamp": datetime.now()
        })
        
        return f"Successfully created {request_type} request (ID: {req_id}). Staff has been notified."
