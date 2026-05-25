from crewai.tools import BaseTool
import json
from pydantic import BaseModel, Field
from typing import Optional, Dict, Type
from datetime import datetime
from bson import ObjectId

from caremate_v4.mongodb.db_service import db


# -----------------------------
# Input Schema
# -----------------------------
class LoggingInput(BaseModel):
    event_type: str = Field(..., description="Type of event (nurse_request, doctor_query, utility_request, etc)")
    patient_id: Optional[str] = Field(None, description="Patient ID related to the event")
    visit_id: Optional[str] = Field(None, description="Visit ID if applicable")
    request_id: Optional[str] = Field(None, description="Request ID if related to a service request")
    actor: Optional[str] = Field(None, description="Who triggered the event (patient, nurse, doctor, system)")
    description: str = Field(..., description="Human-readable description of the event")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Additional structured metadata")


# -----------------------------
# Logging Tool
# -----------------------------
class LoggingTool(BaseTool):

    name: str = "Centralized Logging Tool"
    description: str = (
        "Logs structured hospital workflow events such as nurse requests, doctor queries, "
        "nutrition approvals, utility services, OCR updates, and status changes into MongoDB."
    )

    args_schema: Type[LoggingInput] = LoggingInput

    # -----------------------------
    # Tool Execution
    # -----------------------------
    def _run(
        self,
        event_type: str,
        description: str,
        patient_id: Optional[str] = None,
        visit_id: Optional[str] = None,
        request_id: Optional[str] = None,
        actor: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> dict:

        event = {
            "_id": str(ObjectId()),
            "event_type": event_type,
            "patient_id": patient_id,
            "visit_id": visit_id,
            "request_id": request_id,
            "actor": actor,
            "description": description,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow()
        }

        db.visit_events.insert_one(event)

        return json.dumps({
            "status": "success",
            "message": "Event logged successfully",
            "event_id": event["_id"]
        })