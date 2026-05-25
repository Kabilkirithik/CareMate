from crewai.tools import BaseTool
import json
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from caremate_v4.mongodb.db_service import db


# -----------------------------
# Input Schema
# -----------------------------
from crewai.tools import BaseTool
import json
from pydantic import BaseModel, Field
from typing import Optional, Type
from datetime import datetime

from caremate_v4.mongodb.db_service import db


class StatusTrackingInput(BaseModel):
    request_id: str = Field(..., description="Unique request ID")
    action: str = Field(..., description="get_status or update_status")
    new_status: Optional[str] = Field(None, description="New status if updating")



# -----------------------------
# Status Tracking Tool
# -----------------------------
class StatusTrackingTool(BaseTool):

    name: str = "Status Tracking Tool"
    description: str = "Track and update lifecycle status of patient service requests."

    args_schema: Type[StatusTrackingInput] = StatusTrackingInput
    # -----------------------------
    # Main Tool Execution
    # -----------------------------
    def _run(
        self,
        request_id: str,
        action: str,
        new_status: Optional[str] = None
    ) -> str:

        if action == "get_status":
            return self.get_status(request_id)

        elif action == "update_status":
            if not new_status:
                return "New status must be provided for update."

            return self.update_status(request_id, new_status)

        else:
            return "Invalid action. Use 'get_status' or 'update_status'."

    # -----------------------------
    # Fetch Request Status
    # -----------------------------
    def get_status(self, request_id: str):

        request = db.requests.find_one({"request_id": request_id})

        if not request:
            return f"No request found with ID {request_id}"

        status = request.get("status", "Unknown")

        return json.dumps({
            "request_id": request_id,
            "status": status,
            "message": f"The current status of your request is '{status}'."
        })

    # -----------------------------
    # Update Request Status
    # -----------------------------
    def update_status(self, request_id: str, new_status: str):

        update_result = db.requests.update_one(
            {"request_id": request_id},
            {
                "$set": {
                    "status": new_status,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if update_result.matched_count == 0:
            return f"Request {request_id} not found."

        return json.dumps({
            "request_id": request_id,
            "updated_status": new_status,
            "message": f"Request status updated to '{new_status}'."
        })