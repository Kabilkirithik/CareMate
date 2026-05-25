from crewai.tools import BaseTool
import uuid
import random
import json
from datetime import datetime, timedelta


class NutritionistApprovalTool(BaseTool):

    name: str = "Nutritionist Approval Tool"
    description: str = (
        "Handles patient food requests requiring nutritionist approval. "
        "Creates a nutrition request, assigns a nutritionist, tracks approval status, "
        "and triggers a reminder if approval is not received within 30 minutes."
    )

    def _run(self, patient_id: str, bed_number: str, food_request: str):

        request_id = f"NR-{uuid.uuid4().hex[:8]}"

        nutritionists = [
            "Nutritionist_Anita",
            "Nutritionist_Raj",
            "Nutritionist_Priya"
        ]

        assigned_nutritionist = random.choice(nutritionists)

        created_time = datetime.utcnow()
        sla_deadline = created_time + timedelta(minutes=30)

        request_record = {
            "nutrition_request_id": request_id,
            "patient_id": patient_id,
            "bed_number": bed_number,
            "food_request": food_request,
            "assigned_nutritionist": assigned_nutritionist,
            "status": "pending_approval",
            "sla_deadline": sla_deadline.isoformat(),
            "created_at": created_time.isoformat()
        }

        return json.dumps(request_record)

    def check_sla_and_trigger_reminder(self, request_record):

        sla_deadline = datetime.fromisoformat(request_record["sla_deadline"])
        current_time = datetime.utcnow()

        if current_time > sla_deadline and request_record["status"] == "pending_approval":

            reminder_event = {
                "nutrition_request_id": request_record["nutrition_request_id"],
                "reminder_triggered": True,
                "reminder_time": current_time.isoformat(),
                "message": "Reminder sent to nutritionist for pending approval."
            }

            return reminder_event

        return {
            "reminder_triggered": False
        }