from crewai.tools import BaseTool
import uuid
import random
import json
from datetime import datetime, timedelta


class UtilityServiceTool(BaseTool):

    name: str = "Utility Service Tool"
    description: str = (
        "Handles facility-related requests such as blankets, wheelchairs, chargers, "
        "and housekeeping services. Tracks completion with a one-hour SLA and "
        "triggers reminders if the request is delayed."
    )

    def _run(self, patient_id: str, bed_number: str, request_text: str):

        request_id = f"UT-{uuid.uuid4().hex[:8]}"

        staff_pool = [
            "Staff_Ramesh",
            "Staff_Anil",
            "Staff_Sunita",
            "Staff_Karthik"
        ]

        assigned_staff = random.choice(staff_pool)

        created_time = datetime.utcnow()
        sla_deadline = created_time + timedelta(hours=1)

        request_record = {
            "utility_request_id": request_id,
            "patient_id": patient_id,
            "bed_number": bed_number,
            "request_text": request_text,
            "assigned_staff": assigned_staff,
            "status": "pending",
            "sla_deadline": sla_deadline.isoformat(),
            "created_at": created_time.isoformat()
        }

        return json.dumps(request_record)

    def check_sla_and_trigger_reminder(self, request_record):

        sla_deadline = datetime.fromisoformat(request_record["sla_deadline"])
        current_time = datetime.utcnow()

        if current_time > sla_deadline and request_record["status"] == "pending":

            reminder_event = {
                "utility_request_id": request_record["utility_request_id"],
                "reminder_triggered": True,
                "reminder_time": current_time.isoformat(),
                "message": "Reminder sent to facility staff for pending utility request."
            }

            return reminder_event

        return {"reminder_triggered": False}

    def confirm_completion(self, request_record):

        request_record["status"] = "completed"
        request_record["completion_time"] = datetime.utcnow().isoformat()

        confirmation_message = (
            f"Utility request {request_record['utility_request_id']} has been completed."
        )

        return {
            "request_record": request_record,
            "voice_confirmation": confirmation_message
        }