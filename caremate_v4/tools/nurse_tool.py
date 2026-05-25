from crewai.tools import BaseTool
import uuid
import random
import json
from datetime import datetime


class NurseDashboardTool(BaseTool):

    name: str = "Nurse Dashboard Tool"
    description: str = (
        "Handles nurse-related patient requests such as assistance, bed adjustment, "
        "and comfort needs by creating a nurse task and assigning an available nurse."
    )

    def _run(self, patient_id: str, bed_number: str, request_text: str, priority: str = "medium"):

        task_id = f"NT-{uuid.uuid4().hex[:8]}"

        available_nurses = [
            "Nurse_Asha",
            "Nurse_Ravi",
            "Nurse_Meena",
            "Nurse_Kumar"
        ]

        assigned_nurse = random.choice(available_nurses)

        sla_times = {
            "low": "15 minutes",
            "medium": "10 minutes",
            "high": "5 minutes"
        }

        response_time = sla_times.get(priority, "10 minutes")

        task = {
            "task_id": task_id,
            "patient_id": patient_id,
            "bed_number": bed_number,
            "request_text": request_text,
            "priority": priority,
            "assigned_nurse": assigned_nurse,
            "status": "pending",
            "estimated_response_time": response_time,
            "created_at": datetime.utcnow().isoformat()
        }

        return json.dumps(task)