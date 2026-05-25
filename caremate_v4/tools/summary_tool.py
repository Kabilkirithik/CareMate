from crewai.tools import BaseTool
import json
from pydantic import BaseModel, Field
from typing import Type, Optional
from datetime import datetime

from caremate_v4.mongodb.db_service import db


class SummaryInput(BaseModel):
    patient_id: str = Field(..., description="Patient ID")
    visit_id: str = Field(..., description="Visit ID")


class SummaryGeneratorTool(BaseTool):

    name: str = "Summary Generator Tool"
    description: str = "Generate doctor visit summaries from patient activity and documents."

    args_schema: Type[SummaryInput] = SummaryInput

    def _run(self, patient_id: str, visit_id: str):

        # -------------------------
        # Fetch patient requests
        # -------------------------
        requests = list(db.requests.find({
            "patient_id": patient_id
        }))

        # -------------------------
        # Fetch OCR documents
        # -------------------------
        documents = list(db.documents.find({
            "patient_id": patient_id
        }))

        # -------------------------
        # Fetch visit events
        # -------------------------
        events = list(db.visit_events.find({
            "patient_id": patient_id
        }))

        # -------------------------
        # Build summary sections
        # -------------------------
        concerns = []
        request_history = []
        ocr_updates = []
        doctor_notes = []

        for event in events:
            if event.get("event_type") == "patient_concern":
                concerns.append(event.get("description"))

            if event.get("event_type") == "doctor_note":
                doctor_notes.append(event.get("description"))

        for r in requests:
            request_history.append(
                f"{r.get('service')} ({r.get('status')})"
            )

        for doc in documents:
            ocr_updates.append(
                f"{doc.get('document_type')} processed"
            )

        # -------------------------
        # Generate summary
        # -------------------------
        summary = {
            "patient_id": patient_id,
            "visit_id": visit_id,
            "patient_concerns": concerns,
            "request_history": request_history,
            "ocr_updates": ocr_updates,
            "doctor_notes": doctor_notes,
            "generated_at": datetime.utcnow()
        }

        # store summary
        db.summaries.insert_one(summary)

        return summary