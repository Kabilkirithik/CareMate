from crewai.tools import BaseTool
import json
import uuid
from datetime import datetime


class DoctorVoiceInteractionTool(BaseTool):

    name: str = "Doctor Voice Interaction Tool"
    description: str = (
        "Handles medical queries by forwarding patient requests to the doctor dashboard "
        "and returning the doctor's recorded voice response. Prevents AI from giving "
        "medical advice directly."
    )

    def _run(self, patient_id: str, bed_number: str, medical_query: str):

        # Generate consultation session ID
        consultation_id = f"DR-{uuid.uuid4().hex[:8]}"

        # Simulated doctor assignment
        assigned_doctor = "Dr. Sharma"

        # Simulated doctor response audio path
        doctor_response_audio = f"doctor_responses/{consultation_id}.mp3"

        consultation_record = {
            "consultation_id": consultation_id,
            "patient_id": patient_id,
            "bed_number": bed_number,
            "medical_query": medical_query,
            "assigned_doctor": assigned_doctor,
            "status": "pending_doctor_response",
            "response_audio_path": doctor_response_audio,
            "created_at": datetime.utcnow().isoformat()
        }

        return consultation_record