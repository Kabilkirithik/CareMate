# emergency_tool.py

from typing import Tuple

# ⚡ Fast Emergency PreCheck (System Layer)
def emergency_precheck(text: str) -> Tuple[bool, str, str]:
    """
    Fast rule-based emergency detection.
    Runs BEFORE CrewAI reasoning to minimize latency.
    Returns: (is_emergency, severity, reason)
    """

    if not text:
        return False, "LOW", None

    text_lower = text.lower()

    # 🔴 Critical Emergency Keywords
    CRITICAL_KEYWORDS = [
        "can't breathe",
        "cannot breathe",
        "chest pain",
        "severe bleeding",
        "fainted",
        "unconscious",
        "not breathing",
        "heart pain",
        "emergency help"
    ]

    # 🟠 High Distress Keywords
    HIGH_KEYWORDS = [
        "help urgently",
        "dizzy",
        "fall down",
        "extreme pain",
        "panic",
        "scared"
    ]

    for word in CRITICAL_KEYWORDS:
        if word in text_lower:
            return True, "CRITICAL", word

    for word in HIGH_KEYWORDS:
        if word in text_lower:
            return True, "HIGH", word

    if "help" in text_lower:
        return True, "MEDIUM", "distress phrase"

    return False, "LOW", None



# emergency_tool.py (continue)

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import asyncio
import httpx


class EmergencyInput(BaseModel):
    patient_id: str = Field(...)
    bed_id: str = Field(...)
    severity: str = Field(...)
    reason: str = Field(...)


class EmergencyDetectionTool(BaseTool):

    name: str = "EmergencyDetectionTool"
    description: str = "Triggers emergency alerts to nurse and doctor dashboards."

    args_schema: Type[BaseModel] = EmergencyInput

    async def _run(self, **kwargs):

        patient_id = kwargs["patient_id"]
        bed_id = kwargs["bed_id"]
        severity = kwargs["severity"]
        reason = kwargs["reason"]

        print(f"[EmergencyTool] Triggered → {severity} ({reason})")

        loop = asyncio.get_running_loop()
        loop.create_task(
            self.send_alert(patient_id, bed_id, severity, reason)
        )

        return {
            "alert_sent": True,
            "severity": severity,
            "reason": reason
        }

    async def send_alert(self, patient_id, bed_id, severity, reason):

        payload = {
            "patient_id": patient_id,
            "bed_id": bed_id,
            "severity": severity,
            "reason": reason
        }

        nurse_url = "http://localhost:8000/api/nurse/emergency"
        doctor_url = "http://localhost:8000/api/doctor/emergency"

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(2.0)) as client:
                await asyncio.gather(
                    client.post(nurse_url, json=payload),
                    client.post(doctor_url, json=payload),
                    self.log_event(payload)
                )

        except Exception as e:
            print(f"[EmergencyTool] Alert Failed: {e}")

    async def log_event(self, payload):

        log_url = "http://localhost:8000/api/logs/emergency"

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(2.0)) as client:
                await client.post(log_url, json=payload)
        except Exception:
            pass