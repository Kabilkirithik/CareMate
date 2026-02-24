# caremate_crew.py

from crewai import Agent, Task, Crew, Process, tools, LLM
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# -------------------------------------------------------------------
# LLM CONFIGURATION (Ollama + smollm2)
# -------------------------------------------------------------------

ollama_llm = LLM(
    provider="ollama",
    model="smollm2",
    base_url="http://localhost:11434"
)

# -------------------------------------------------------------------
# DATA MODELS
# -------------------------------------------------------------------

class PatientProfile(BaseModel):
    patient_name: str
    age: int
    hospital_id: str
    room_number: str
    admitting_department: str
    known_conditions: List[str]
    dietary_restrictions: List[str]
    mobility_limitations: str


class ContextSummary(BaseModel):
    summary: str


class IntentClassification(BaseModel):
    intent_label: str
    confidence_score: float


class EmergencyDetection(BaseModel):
    is_emergency: bool
    distress_severity: str


class MemoryState(BaseModel):
    recent_queries: List[str]
    previous_responses: List[str]
    pending_requests: List[str]


class PolicyEvaluationResult(BaseModel):
    allowed_action_set: List[str]
    required_approvals: List[str]


class ResponseText(BaseModel):
    response: str


class NotificationEvent(BaseModel):
    recipient: str
    patient_id: str
    request_summary: str
    urgency_level: str


class ApprovalState(BaseModel):
    status: str
    approved_by: str


class AuditRecord(BaseModel):
    timestamp: str
    event_type: str
    details: Dict[str, Any]


# -------------------------------------------------------------------
# TOOLS (MOCK IMPLEMENTATIONS)
# -------------------------------------------------------------------

@tools.tool("Patient Record Retrieval Tool")
def patient_record_retrieval_tool(hospital_id: str, room_number: str) -> PatientProfile:
    print(f"[MOCK] Fetching patient record {hospital_id}, Room {room_number}")
    return PatientProfile(
        patient_name="John Doe",
        age=65,
        hospital_id=hospital_id,
        room_number=room_number,
        admitting_department="Cardiology",
        known_conditions=["Hypertension", "Diabetes"],
        dietary_restrictions=["Low Sodium", "Diabetic"],
        mobility_limitations="Limited mobility (post-op)"
    )


@tools.tool("Context Summarization Tool")
def context_summarization_tool(patient_data: PatientProfile) -> ContextSummary:
    print("[MOCK] Summarizing patient context")
    summary = (
        f"65-year-old post-operative cardiology patient with "
        f"{', '.join(patient_data.known_conditions)}. "
        f"Diet: {', '.join(patient_data.dietary_restrictions)}. "
        f"Mobility: {patient_data.mobility_limitations}."
    )
    return ContextSummary(summary=summary)


@tools.tool("Intent Classification Tool")
def intent_classification_tool(patient_query: str) -> IntentClassification:
    print("[MOCK] Classifying intent")
    q = patient_query.lower()

    if any(k in q for k in ["chest pain", "pain", "medicine", "symptom"]):
        return IntentClassification(intent_label="Medical-related request", confidence_score=0.9)
    if any(k in q for k in ["can't breathe", "help", "emergency"]):
        return IntentClassification(intent_label="Emergency or distress request", confidence_score=0.95)

    return IntentClassification(intent_label="General inquiry", confidence_score=0.7)


@tools.tool("Emergency & Distress Detection Tool")
def emergency_distress_detection_tool(patient_query: str) -> EmergencyDetection:
    print("[MOCK] Detecting emergency")
    q = patient_query.lower()

    if any(k in q for k in ["can't breathe", "severe pain", "panic", "help"]):
        return EmergencyDetection(is_emergency=True, distress_severity="Critical")

    return EmergencyDetection(is_emergency=False, distress_severity="Low")


@tools.tool("Interaction Memory Tool")
def interaction_memory_tool(
    patient_query: str,
    system_response: str = "",
    current_memory: MemoryState = None
) -> MemoryState:
    print("[MOCK] Updating interaction memory")
    if not current_memory:
        current_memory = MemoryState(
            recent_queries=[],
            previous_responses=[],
            pending_requests=[]
        )

    current_memory.recent_queries.append(patient_query)
    if system_response:
        current_memory.previous_responses.append(system_response)

    return current_memory


@tools.tool("Policy Evaluation Tool")
def policy_evaluation_tool(
    intent: IntentClassification,
    emergency_status: EmergencyDetection
) -> PolicyEvaluationResult:
    print("[MOCK] Evaluating policy")

    allowed = ["Respond with information"]
    approvals = []

    if emergency_status.is_emergency:
        allowed.append("Escalate to Nurse")
        approvals.append("Nurse")
    elif "Medical" in intent.intent_label:
        allowed.append("Suggest speaking to medical staff")
        approvals.append("Doctor")

    return PolicyEvaluationResult(
        allowed_action_set=allowed,
        required_approvals=approvals
    )


@tools.tool("Response Generation Tool")
def response_generation_tool(
    patient_context: ContextSummary,
    intent: IntentClassification,
    policy_result: PolicyEvaluationResult
) -> ResponseText:
    print("[MOCK] Generating response")

    if "Escalate to Nurse" in policy_result.allowed_action_set:
        text = (
            "I’ve detected a possible emergency. "
            "Nursing staff have been alerted and will assist you immediately. "
            "Please stay calm."
        )
    elif "Suggest speaking to medical staff" in policy_result.allowed_action_set:
        text = (
            "Your request concerns a medical issue. "
            "I’m notifying the medical team so they can assist you shortly."
        )
    else:
        text = "I’m here to help. Please let me know what you need."

    return ResponseText(response=text)


@tools.tool("Notification & Escalation Tool")
def notification_escalation_tool(event: NotificationEvent) -> str:
    print(
        f"[MOCK] NOTIFY {event.recipient} | "
        f"Patient {event.patient_id} | "
        f"Urgency: {event.urgency_level}"
    )
    return "Notification sent"


@tools.tool("Approval Workflow Tool")
def approval_workflow_tool(action_to_approve: str, patient_id: str) -> ApprovalState:
    print(f"[MOCK] Approval granted for {action_to_approve}")
    return ApprovalState(status="Approved", approved_by="Nurse")


@tools.tool("Audit & Logging Tool")
def audit_logging_tool(record: AuditRecord) -> str:
    print(f"[MOCK] Audit log: {record.event_type}")
    return "Audit logged"


# -------------------------------------------------------------------
# AGENTS
# -------------------------------------------------------------------

patient_intelligence_agent = Agent(
    role="Patient Intelligence Agent",
    goal="Analyze patient requests and prepare structured understanding.",
    backstory="Perception and analysis layer of CareMate.",
    llm=ollama_llm,
    verbose=True,
    allow_delegation=False,
    tools=[
        patient_record_retrieval_tool,
        context_summarization_tool,
        intent_classification_tool,
        emergency_distress_detection_tool,
        interaction_memory_tool
    ]
)

central_orchestrator_agent = Agent(
    role="Central Orchestrator & Policy Agent",
    goal="Enforce policy, manage escalation, and control responses.",
    backstory="Decision authority ensuring safety and compliance.",
    llm=ollama_llm,
    verbose=True,
    allow_delegation=True,
    tools=[
        policy_evaluation_tool,
        response_generation_tool,
        notification_escalation_tool,
        approval_workflow_tool,
        audit_logging_tool
    ]
)

# -------------------------------------------------------------------
# TASKS
# -------------------------------------------------------------------

task_analyze_patient_request = Task(
    description=(
        "Analyze the patient's query '{patient_query}', retrieve patient context, "
        "classify intent, and detect emergency signals.\n"
        "Patient ID: {hospital_id}, Room: {room_number}"
    ),
    expected_output="Structured patient analysis",
    agent=patient_intelligence_agent
)

task_orchestrate_response = Task(
    description=(
        "Based on the analysis, enforce policy, decide actions, "
        "generate a safe response, and escalate if required.\n"
        "Patient query: {patient_query}"
    ),
    expected_output="Final patient-facing response",
    agent=central_orchestrator_agent
)

# -------------------------------------------------------------------
# CREW
# -------------------------------------------------------------------

caremate_crew = Crew(
    agents=[
        patient_intelligence_agent,
        central_orchestrator_agent
    ],
    tasks=[
        task_analyze_patient_request,
        task_orchestrate_response
    ],
    process=Process.sequential,
    verbose=True
)

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

if __name__ == "__main__":
    print("\n🩺 CareMate Crew Simulation Started\n")

    patient_input = {
        "patient_query": "I am feeling a lot of pain in my chest and I can't breathe well. Please help!",
        "hospital_id": "HOSP123",
        "room_number": "RM201"
    }

    result = caremate_crew.kickoff(inputs=patient_input)

    print("\n--- FINAL OUTPUT ---")
    print(result)
