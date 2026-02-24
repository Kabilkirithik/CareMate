from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from typing import Dict, Any, Type
from pydantic import BaseModel, Field
from pymongo import MongoClient
import os, dotenv

dotenv.load_dotenv()
# --------------------------------------------------
# MongoDB Atlas Connection (Singleton-style)
# --------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable not set")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
client.admin.command("ping")

db = client["hospital_db"]
patients_collection = db["patients"]

# --------------------------------------------------
# Input Schema (Validated)
# --------------------------------------------------
class PatientLookupInput(BaseModel):
    hospital_id: str = Field(..., description="Unique hospital patient ID")
    room_number: str = Field(..., description="Room or ward number")
    bed_number: str = Field(..., description="Bed number")

# --------------------------------------------------
# BaseTool Implementation
# --------------------------------------------------
class PatientRecordRetrievalTool(BaseTool):
    name: str = "patient_record_retrieval"
    description: str = (
        "Retrieves a privacy-safe patient profile using hospital ID, "
        "room number, and bed number. Only non-sensitive, pre-approved "
        "patient context is returned."
    )

    args_schema: Type[BaseModel] = PatientLookupInput

    def _run(
        self,
        hospital_id: str,
        room_number: str,
        bed_number: str
    ) -> Dict[str, Any]:

        query = {
            "hospital_id": hospital_id,
            "room_number": room_number,
            "bed_number": bed_number
        }

        # Explicit allow-list projection (privacy enforcement)
        projection = {
            "_id": 0,
            "hospital_id": 1,
            "name": 1,
            "age": 1,
            "department": 1,
            "known_conditions": 1,
            "dietary_restrictions": 1,
            "mobility_limitations": 1
        }

        patient = patients_collection.find_one(query, projection)

        if not patient:
            return {
                "error": "Patient record not found",
                "hospital_id": hospital_id,
                "room_number": room_number,
                "bed_number": bed_number
            }

        return patient