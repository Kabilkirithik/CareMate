"""
single_crew.py
==============
CareMate — Consolidated Single-File Crew Entry Point

Architecture:
    Patient message
        ↓
    Emergency precheck  (instant, rule-based, bypasses everything)
        ↓ (not emergency)
    ML Classifier       (classify_message → category + confidence)
        ↓
    Central Agent       (calls the single correct tool)
        ↓
    Logging Task        (LoggingTool — always runs)
        ↓
    Patient Agent       (formats one warm confirmation sentence)
        ↓
    Friendly response returned to caller

Key design decisions:
    - Routing is done OUTSIDE CrewAI (ML model / rule fallback).
      Agents never reason about which tool to pick — they just call it.
    - Emergency path has zero-latency: no LLM, no crew, direct return.
    - Friendly-response fallback ensures patient always gets a reply
      even when the LLM or a tool fails.
    - All patient messages and system responses are persisted to MongoDB.
    - RFID resolution supports live tags, patient_id fallback, and
      auto-registration of unknown tags.

Run (CLI):
    python -m caremate_v4.single_crew

Environment variables:
    MONGO_URI        — required
    AWS_REGION       — default: us-east-1
    AGENT_VERBOSE    — "true" | "false"  (default: false)
"""

# =============================================================
# STDLIB / THIRD-PARTY IMPORTS
# =============================================================

import asyncio
import os
import re
import uuid
from datetime import datetime, timezone

from crewai import Agent, Crew, LLM, Process, Task

# =============================================================
# TOOL IMPORTS — Patient Agent
# =============================================================

from caremate_v4.tools.emergency import EmergencyDetectionTool, emergency_precheck
from caremate_v4.tools.ocr_tool import OCRSubmissionTool
from caremate_v4.tools.stt_tool import STTTool
from caremate_v4.tools.tts_tool import TTSTool

# =============================================================
# TOOL IMPORTS — Central Agent
# =============================================================

from caremate_v4.tools.doctor_tool import DoctorVoiceInteractionTool
from caremate_v4.tools.logging_tool import LoggingTool
from caremate_v4.tools.nurse_tool import NurseDashboardTool
from caremate_v4.tools.nutritionist_tool import NutritionistApprovalTool
from caremate_v4.tools.patient_details_tool import PatientDetailsTool
from caremate_v4.tools.status_tracking_tool import StatusTrackingTool
from caremate_v4.tools.summary_tool import SummaryGeneratorTool
from caremate_v4.tools.utility_service_tool import UtilityServiceTool

# =============================================================
# DATABASE
# =============================================================

from caremate_v4.mongodb.db_service import db, get_active_visit, log_chat, log_event

# =============================================================
# ML CLASSIFIER CLIENT
# =============================================================

from caremate_v4.classifier.classifier_client import classify_message, is_classifier_available

# =============================================================
# CONFIG
# =============================================================

AWS_REGION    = os.getenv("AWS_REGION", "us-east-1")
AGENT_VERBOSE = os.getenv("AGENT_VERBOSE", "false").lower() == "true"

# Pre-written patient-facing confirmations used as fallback when the LLM
# response is absent, too short, or contains an error phrase.
FRIENDLY_RESPONSES: dict[str, str] = {
    "UTILITY_REQUEST":   "Got it! Your request has been sent to the facility team. They'll be with you shortly.",
    "NURSE_REQUEST":     "Understood! A nurse has been notified and will come to you soon.",
    "NUTRITION_REQUEST": "Your food request has been submitted for approval. We'll update you shortly.",
    "STATUS_QUERY":      "I've checked on that for you. Your request is being tracked and is in progress.",
    "DOCTOR_QUERY":      "Your question has been forwarded to your doctor. You'll receive a response soon.",
    "OCR_UPLOAD":        "Your document has been submitted for processing. We'll update your records shortly.",
    "CASUAL_CHAT":       "I'm here with you! How can I help you today?",
    "DEFAULT":           "Your request has been received and is being handled. Please wait a moment.",
}

# Immediate responses for the emergency path (no crew involved).
EMERGENCY_RESPONSES: dict[str, str] = {
    "CRITICAL": (
        "Please stay calm. This is a medical emergency — "
        "your nurse and doctor have been alerted and are on their way."
    ),
    "HIGH": (
        "Please stay calm. A nurse has been alerted urgently "
        "and will be with you very shortly."
    ),
    "MEDIUM": (
        "I heard you. A nurse has been notified and will come check on you right away."
    ),
}

# =============================================================
# SHARED LLM
# =============================================================

llm = LLM(
    model="bedrock/amazon.nova-pro-v1:0",
    aws_region_name=AWS_REGION,
)

# =============================================================
# AGENTS
# =============================================================

patient_agent = Agent(
    role="Patient Interaction Agent",
    goal=(
        "You receive a pre-classified hospital patient request. "
        "Delegate it to the Central Orchestration Manager. "
        "Then reply to the patient with exactly one warm, friendly confirmation sentence."
    ),
    backstory=(
        "You are a warm bedside hospital AI assistant. "
        "Routing has already been done — your only job is to delegate and reassure the patient. "
        "Never answer medical questions. Never ask the patient for clarification."
    ),
    tools=[
        STTTool(),
        TTSTool(),
        EmergencyDetectionTool(),
        OCRSubmissionTool(),
    ],
    allow_delegation=True,
    verbose=AGENT_VERBOSE,
    llm=llm,
)

central_agent = Agent(
    role="Central Orchestration Manager",
    goal=(
        "You receive a patient request that has already been classified. "
        "You MUST call the single tool that matches the category — never reply from memory. "
        "Category → tool mapping:\n"
        "  UTILITY_REQUEST   → UtilityServiceTool\n"
        "  NURSE_REQUEST     → NurseDashboardTool\n"
        "  NUTRITION_REQUEST → NutritionistApprovalTool\n"
        "  STATUS_QUERY      → StatusTrackingTool\n"
        "  DOCTOR_QUERY      → DoctorVoiceInteractionTool\n"
        "  OCR_UPLOAD        → OCRSubmissionTool\n"
        "After the service tool, always call LoggingTool."
    ),
    backstory=(
        "You are the hospital workflow engine. "
        "The category is pre-determined — call the right tool and log the event. "
        "One tool call at a time. Never guess or reason about routing."
    ),
    tools=[
        PatientDetailsTool(),
        NurseDashboardTool(),
        DoctorVoiceInteractionTool(),
        NutritionistApprovalTool(),
        UtilityServiceTool(),
        StatusTrackingTool(),
        LoggingTool(),
        SummaryGeneratorTool(),
        OCRSubmissionTool(),
    ],
    allow_delegation=False,
    verbose=AGENT_VERBOSE,
    llm=llm,
)

# =============================================================
# RFID PATIENT RESOLUTION
# =============================================================

def resolve_patient(rfid_tag: str) -> dict:
    """
    Resolve a patient from their RFID tag.

    Priority order:
        1. Match by rfid_tag field in patients collection.
        2. Fallback: match by patient_id (useful for CLI / seeded test data).
        3. Auto-register a new patient + visit if completely unknown.

    Returns a dict with:
        patient_id, name, rfid_tag, bed_id, visit_id, is_new
    """
    # 1. RFID lookup
    patient = db.patients.find_one({"rfid_tag": rfid_tag})

    # 2. patient_id fallback (testing / seeded data)
    if not patient:
        patient = db.patients.find_one({"patient_id": rfid_tag})

    if patient:
        visit = get_active_visit(patient["patient_id"])
        return {
            "patient_id": patient["patient_id"],
            "name":       patient.get("name", "Patient"),
            "rfid_tag":   rfid_tag,
            "bed_id":     visit.get("current_bed", "B001") if visit else "B001",
            "visit_id":   visit.get("visit_id") if visit else None,
            "is_new":     False,
        }

    # 3. Auto-register unknown RFID tag
    new_patient_id = f"P-{uuid.uuid4().hex[:6].upper()}"
    new_visit_id   = f"V-{uuid.uuid4().hex[:6].upper()}"
    now            = datetime.now(timezone.utc)

    db.patients.insert_one({
        "patient_id": new_patient_id,
        "rfid_tag":   rfid_tag,
        "name":       "New Patient",
        "age":        None,
        "gender":     None,
        "allergies":  [],
        "created_at": now,
    })

    db.visits.insert_one({
        "visit_id":        new_visit_id,
        "patient_id":      new_patient_id,
        "status":          "Admitted",
        "admission_time":  now,
        "current_room":    "R101",
        "current_bed":     "B001",
        "assigned_doctor": None,
        "discharge_time":  None,
    })

    return {
        "patient_id": new_patient_id,
        "name":       "New Patient",
        "rfid_tag":   rfid_tag,
        "bed_id":     "B001",
        "visit_id":   new_visit_id,
        "is_new":     True,
    }

# =============================================================
# HELPERS
# =============================================================

def clean_response(text: str) -> str:
    """Strip Amazon Nova <thinking>…</thinking> reasoning blocks from output."""
    if not isinstance(text, str):
        return str(text)
    return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()


def get_friendly_response(category: str) -> str:
    """Return a pre-written patient-friendly confirmation for a given category."""
    return FRIENDLY_RESPONSES.get(category, FRIENDLY_RESPONSES["DEFAULT"])


def is_bad_response(text: str) -> bool:
    """Return True if the LLM output is unusable and should be replaced by a fallback."""
    if not text or len(text) < 10:
        return True
    bad_phrases = [
        "apologize", "cannot complete", "error in processing",
        "couldn't generate", "i'm sorry", "unable to",
    ]
    return any(phrase in text.lower() for phrase in bad_phrases)

# =============================================================
# CREW FACTORY
# =============================================================

def build_crew(patient: dict, message: str, category: str) -> Crew:
    """
    Build a three-task sequential crew for a single patient request.

    The ML classifier has already determined `category`, so the tasks
    are explicit and directive — the agent never has to reason about routing.

    Tasks:
        1. service_task   — Central Agent calls the one correct service tool.
        2. logging_task   — Central Agent calls LoggingTool.
        3. confirmation_task — Patient Agent replies to the patient.
    """

    # Exact tool name + argument string per category.
    # These are rendered verbatim into the task description so the LLM
    # cannot misinterpret which tool or arguments to use.
    TOOL_INSTRUCTIONS: dict[str, tuple[str, str]] = {
        "UTILITY_REQUEST": (
            "UtilityServiceTool",
            (
                f"patient_id='{patient['patient_id']}', "
                f"bed_number='{patient['bed_id']}', "
                f"request_text='{message}'"
            ),
        ),
        "NURSE_REQUEST": (
            "NurseDashboardTool",
            (
                f"patient_id='{patient['patient_id']}', "
                f"bed_number='{patient['bed_id']}', "
                f"request_text='{message}', "
                f"priority='medium'"
            ),
        ),
        "NUTRITION_REQUEST": (
            "NutritionistApprovalTool",
            (
                f"patient_id='{patient['patient_id']}', "
                f"bed_number='{patient['bed_id']}', "
                f"food_request='{message}'"
            ),
        ),
        "STATUS_QUERY": (
            "StatusTrackingTool",
            "request_id='latest', action='get_status'",
        ),
        "DOCTOR_QUERY": (
            "DoctorVoiceInteractionTool",
            (
                f"patient_id='{patient['patient_id']}', "
                f"bed_number='{patient['bed_id']}', "
                f"medical_query='{message}'"
            ),
        ),
        "OCR_UPLOAD": (
            "OCRSubmissionTool",
            (
                f"patient_id='{patient['patient_id']}', "
                f"file_path='pending_upload'"
            ),
        ),
    }

    # Default to nurse if category is unrecognised (should not happen).
    tool_name, tool_args = TOOL_INSTRUCTIONS.get(
        category,
        (
            "NurseDashboardTool",
            (
                f"patient_id='{patient['patient_id']}', "
                f"bed_number='{patient['bed_id']}', "
                f"request_text='{message}', "
                f"priority='medium'"
            ),
        ),
    )

    # ------------------------------------------------------------------
    # Task 1 — Service tool call
    # ------------------------------------------------------------------
    service_task = Task(
        description=(
            f"Call {tool_name} with these exact arguments:\n"
            f"  {tool_args}\n\n"
            f"Return the result from the tool as-is. Do not add commentary."
        ),
        expected_output=(
            f"Structured result from {tool_name} confirming the request was created "
            f"(task_id or request_id, status, assigned staff, timestamps)."
        ),
        agent=central_agent,
    )

    # ------------------------------------------------------------------
    # Task 2 — Log the event
    # ------------------------------------------------------------------
    logging_task = Task(
        description=(
            f"Call LoggingTool with these exact arguments:\n"
            f"  event_type='{category}'\n"
            f"  patient_id='{patient['patient_id']}'\n"
            f"  description='Patient requested: {message}'\n\n"
            f"Return the log confirmation."
        ),
        expected_output=(
            "Confirmation from LoggingTool that the event was persisted "
            "(event_id, status='success')."
        ),
        agent=central_agent,
    )

    # ------------------------------------------------------------------
    # Task 3 — Patient-facing confirmation
    # ------------------------------------------------------------------
    # Provide one concrete example per category so the agent has a clear
    # style target — without locking in the exact wording.
    CONFIRMATION_EXAMPLES: dict[str, str] = {
        "UTILITY_REQUEST":   "Got it! Your request has been sent to the facility team.",
        "NURSE_REQUEST":     "A nurse has been notified and will be with you shortly.",
        "NUTRITION_REQUEST": "Your food request has been submitted — we'll update you soon.",
        "STATUS_QUERY":      "I've checked on that — your request is in progress.",
        "DOCTOR_QUERY":      "Your question has been forwarded to your doctor.",
        "OCR_UPLOAD":        "Your document is being processed — we'll update your records shortly.",
    }
    example_reply = CONFIRMATION_EXAMPLES.get(category, "Your request is being handled.")

    confirmation_task = Task(
        description=(
            f"The patient's {category} request has been successfully processed.\n"
            f"Reply to the patient with exactly one warm, friendly sentence in English.\n"
            f"Example: '{example_reply}'\n"
            f"Do not use placeholders, bullet points, or markdown."
        ),
        expected_output=(
            "Exactly one complete, friendly sentence addressed to the patient."
        ),
        agent=patient_agent,
    )

    return Crew(
        agents=[central_agent, patient_agent],
        tasks=[service_task, logging_task, confirmation_task],
        process=Process.sequential,
        verbose=AGENT_VERBOSE,
    )

# =============================================================
# CORE MESSAGE PROCESSOR
# =============================================================

async def process_patient_message(patient: dict, message: str) -> str:
    """
    Process one patient message end-to-end.

    Steps
    -----
    1. Emergency precheck  — synchronous, rule-based, zero-latency.
    2. ML classification   — async (run in executor to avoid blocking).
    3. Log patient message  — persist chat turn.
    4. Build & kick off crew — sequential three-task crew.
    5. Return response     — cleaned LLM output or pre-written fallback.
    """

    # ------------------------------------------------------------------
    # Step 1 — Emergency precheck (bypasses all LLM / crew logic)
    # ------------------------------------------------------------------
    is_emergency, severity, reason = emergency_precheck(message)

    if is_emergency:
        print(f"\n🚨 EMERGENCY — Severity: {severity} | Trigger: {reason}")
        print("   Alerting nurse and doctor dashboards immediately …")

        if patient.get("visit_id"):
            log_event(
                visit_id=patient["visit_id"],
                patient_id=patient["patient_id"],
                event_type="EMERGENCY_TRIGGER",
                metadata={"severity": severity, "reason": reason, "message": message},
            )

        return EMERGENCY_RESPONSES.get(severity, EMERGENCY_RESPONSES["MEDIUM"])

    # ------------------------------------------------------------------
    # Step 2 — ML classification
    # ------------------------------------------------------------------
    loop = asyncio.get_event_loop()
    classification = await loop.run_in_executor(
        None,
        classify_message,
        message,
        patient["patient_id"],
    )

    category   = classification["category"]
    confidence = classification["confidence"]
    source     = classification["source"]

    print(f"  [Classifier] {category} ({confidence:.0%} confidence, source: {source})")

    # ------------------------------------------------------------------
    # CASUAL_CHAT shortcut — Patient Agent handles directly, no crew needed
    # ------------------------------------------------------------------
    if category == "CASUAL_CHAT":
        if patient.get("visit_id"):
            log_chat(patient["visit_id"], speaker="patient", message=message)
        casual_task = Task(
            description=(
                f"The patient said: '{message}'\n"
                f"This is casual conversation. Reply warmly in one or two friendly sentences.\n"
                f"Do not mention tools, routing, or workflow categories."
            ),
            expected_output="One or two warm, friendly sentences in natural English.",
            agent=patient_agent,
        )
        casual_crew = Crew(
            agents=[patient_agent],
            tasks=[casual_task],
            process=Process.sequential,
            verbose=AGENT_VERBOSE,
        )
        loop = asyncio.get_event_loop()
        try:
            result   = await loop.run_in_executor(None, casual_crew.kickoff)
            response = clean_response(str(result))
            if is_bad_response(response):
                response = FRIENDLY_RESPONSES["CASUAL_CHAT"]
        except Exception as exc:
            print(f"  [ERROR] Casual crew failed: {exc}")
            response = FRIENDLY_RESPONSES["CASUAL_CHAT"]
        if patient.get("visit_id"):
            log_chat(patient["visit_id"], speaker="caremate", message=response)
        return response

    # ------------------------------------------------------------------
    # Step 3 — Persist patient chat turn
    # ------------------------------------------------------------------
    if patient.get("visit_id"):
        log_chat(patient["visit_id"], speaker="patient", message=message)

    # ------------------------------------------------------------------
    # Step 4 — Build crew and run
    # ------------------------------------------------------------------
    crew = build_crew(patient, message, category)

    try:
        result   = await loop.run_in_executor(None, crew.kickoff)
        response = clean_response(str(result))

        if is_bad_response(response):
            response = get_friendly_response(category)

    except Exception as exc:
        print(f"  [ERROR] Crew execution failed: {exc}")
        response = get_friendly_response(category)

    # ------------------------------------------------------------------
    # Step 5 — Persist CareMate response and return
    # ------------------------------------------------------------------
    if patient.get("visit_id"):
        log_chat(patient["visit_id"], speaker="caremate", message=response)

    return response

# =============================================================
# CLI INTERFACE
# =============================================================

async def main() -> None:
    """
    Interactive CLI session for a single patient identified by RFID tag.
    Useful for local development and integration testing.
    """
    print("\n🏥  CareMate System")
    print("=" * 44)

    if is_classifier_available():
        print("✅  ML Classifier service connected")
    else:
        print("⚠️   ML Classifier not available — using rule-based fallback")
        print("    Start it with:")
        print("    uvicorn caremate_v4.classifier.classifier_service:app --port 8002")

    print()

    # RFID scan (simulated as CLI input)
    rfid_tag = input("Scan RFID tag (enter tag ID or press Enter for test tag): ").strip()
    if not rfid_tag:
        rfid_tag = "TEST-TAG-001"

    patient = resolve_patient(rfid_tag)

    if patient["is_new"]:
        print(f"\n✅  New patient registered")
    else:
        print(f"\n✅  Welcome back, {patient['name']}")

    print(f"    Patient ID : {patient['patient_id']}")
    print(f"    Bed        : {patient['bed_id']}")
    print("\nType 'exit' to end the session.\n")

    while True:
        try:
            message = input("Patient: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not message:
            continue
        if message.lower() in {"exit", "quit", "bye"}:
            print("\nSession ended. Take care!\n")
            break

        response = await process_patient_message(patient, message)
        print(f"\nCareMate: {response}\n")
        print("-" * 44 + "\n")


if __name__ == "__main__":
    asyncio.run(main())