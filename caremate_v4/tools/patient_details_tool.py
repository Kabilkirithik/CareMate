from crewai.tools import BaseTool
import json
from pydantic import BaseModel, Field
from typing import Type, Optional, Dict, Any
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
# ⭐ Import Service Layer (NO direct DB access)
from caremate_v4.mongodb.db_service import (
    get_patient,
    get_active_visit,
    get_visit_timeline
)


# -------------------------------------------------
# INPUT SCHEMA
# -------------------------------------------------
class PatientDetailsInput(BaseModel):
    patient_id: str = Field(..., description="Unique patient ID")
    action: str = Field(
        ...,
        description="Type of data required: basic_info | active_visit | timeline | summary_data"
    )
    limit: Optional[int] = Field(
        default=20,
        description="Timeline fetch limit"
    )


# -------------------------------------------------
# PATIENT DETAILS TOOL
# -------------------------------------------------
class PatientDetailsTool(BaseTool):

    name: str = "PatientDetailsTool"
    description: str = (
        "Fetches patient details, active visit info, and timeline context "
        "from CareMate database via service layer."
    )

    args_schema: Type[BaseModel] = PatientDetailsInput

    # -------------------------------------------------
    # MAIN EXECUTION
    # -------------------------------------------------
    def _run(self, **kwargs) -> Dict[str, Any]:

        patient_id = kwargs["patient_id"]
        action = kwargs["action"]
        limit = kwargs.get("limit", 20)

        # -------------------------------------------------
        # BASIC INFO
        # -------------------------------------------------
        if action == "basic_info":
            patient = get_patient(patient_id)
            return json.dumps({"basic_info": patient})

        # -------------------------------------------------
        # ACTIVE VISIT
        # -------------------------------------------------
        if action == "active_visit":
            visit = get_active_visit(patient_id)
            return json.dumps({"active_visit": visit})

        # -------------------------------------------------
        # TIMELINE EVENTS
        # -------------------------------------------------
        if action == "timeline":

            visit = get_active_visit(patient_id)

            if not visit:
                return json.dumps({"error": "No active visit"})

            timeline = get_visit_timeline(
                visit_id=visit["visit_id"],
                limit=limit
            )

            return json.dumps({"timeline": timeline})

        # -------------------------------------------------
        # FULL SUMMARY CONTEXT (MOST IMPORTANT)
        # -------------------------------------------------
        if action == "summary_data":

            patient = get_patient(patient_id)
            visit = get_active_visit(patient_id)

            if not visit:
                return json.dumps({"error": "No active visit"})

            timeline = get_visit_timeline(
                visit_id=visit["visit_id"],
                limit=limit
            )

            return json.dumps({
                "patient": patient,
                "visit": visit,
                "recent_events": timeline
            })

        return json.dumps({"error": "Invalid action"})