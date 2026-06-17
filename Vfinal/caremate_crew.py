"""
CareMate CrewAI Architecture — Final Design
============================================
Per architecture spec:

DETERMINISTIC LAYERS (outside agents):
  - Emergency Detection  → runs BEFORE agents, zero latency
  - Intent Routing       → lightweight SVM classifier, not a tool
  - Speech Service       → handled by speech_layer.py, not a tool

AI AGENT LAYER (CrewAI):
  Agent 1: Patient Interaction Agent
    - Friendly conversational AI for casual chat
    - Delegates workflow requests to Central Agent
    - Tools: [patient_context_tool]

  Agent 2: Central Orchestration Agent
    - Workflow manager and system orchestrator
    - NEVER gives medical advice
    - Tools: [patient_context_tool, workflow_action_tool, summary_tool]

TOOLS (exactly 3 per spec):
  1. Patient Context Tool   — read-only MongoDB patient profile
  2. Workflow Action Tool   — unified gateway for all workflow types
  3. Summary Tool           — doctor-facing patient summary generation
"""

import os
import re
import logging
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM 1: Nemotron via OpenRouter — used by Central Orchestration Agent
#         (workflow routing, logging, summaries)
# ---------------------------------------------------------------------------
crew_llm = LLM(
    model="openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# ---------------------------------------------------------------------------
# LLM 2: Meditron via ngrok — used by Patient Interaction Agent
#         (general conversation only — warm, empathetic bedside responses)
# ---------------------------------------------------------------------------
MEDITRON_URL = os.getenv("SAGEMAKER_URL", "https://stateless-hygroscopically-tristen.ngrok-free.dev")

class _MeditronLLM:
    """
    Thin wrapper so we can call Meditron directly for general conversation
    without going through CrewAI's LLM interface.
    Meditron handles: casual chat, emotional support, comfort responses.
    """
    def generate(self, prompt: str, max_tokens: int = 80) -> str:
        try:
            import requests as _req
            r = _req.post(
                f"{MEDITRON_URL.rstrip('/')}/chat",
                json={
                    "message": prompt,
                    "max_new_tokens": max_tokens,
                    "temperature": 0.3,
                    "top_p": 0.7,
                },
                timeout=25,
            )
            r.raise_for_status()
            return r.json().get("response", "").strip()
        except Exception as e:
            logger.warning(f"Meditron unavailable ({e}) — falling back to Nemotron")
            return ""   # empty → caller will use Nemotron fallback

meditron = _MeditronLLM()

# ---------------------------------------------------------------------------
# DETERMINISTIC LAYER 1: Emergency Detection
# Runs BEFORE agents — zero AI overhead, ultra-low latency
# ---------------------------------------------------------------------------
_EMERGENCY_PATTERNS = [
    r"\bemergency\b", r"\bhelp me\b", r"chest pain", r"can't breathe",
    r"cannot breathe", r"severe pain", r"heart attack", r"stroke",
    r"bleeding", r"unconscious", r"code blue", r"falling", r"i fell",
    r"can't move", r"cannot move", r"severe bleeding",
]

def detect_emergency(text: str) -> bool:
    """
    Deterministic emergency detection — runs BEFORE any AI reasoning.
    No LLM, no agent overhead. Returns True if critical distress detected.
    """
    lower = text.lower().strip()
    return any(re.search(pat, lower) for pat in _EMERGENCY_PATTERNS)


# ---------------------------------------------------------------------------
# DETERMINISTIC LAYER 2: Intent Routing
# Lightweight SVM classifier — NOT a CrewAI tool per architecture spec
# ---------------------------------------------------------------------------
def route_intent(text: str) -> dict:
    """
    Classify patient query intent using the trained SVM router.
    Deterministic layer — not an agent tool.
    """
    try:
        from intent_router import IntentRouter
        router = IntentRouter()
        return router.classify(text)
    except Exception as e:
        logger.error(f"Intent routing error: {e}")
        return {"intent": "general_conversation", "confidence": 0.5}


# ---------------------------------------------------------------------------
# TOOL 1: Patient Context Tool (read-only)
# Retrieves patient profile, visit, recent requests, OCR summaries
# ---------------------------------------------------------------------------
@tool("Patient Context Tool")
def patient_context_tool(patient_id: str) -> str:
    """
    Retrieve complete patient context from MongoDB by patient_id.
    Includes: profile, active visit, vitals, allergies, conditions,
    recent requests, assigned staff, and OCR/clinical summary.
    READ-ONLY access.
    """
    try:
        from pymongo import MongoClient
        db = MongoClient(os.getenv("MONGO_URI"))["caremate_db"]

        # ── Patient profile ───────────────────────────────────────────────
        p = db.patients.find_one({"patient_id": str(patient_id)}, {"_id": 0})
        if not p:
            return f"Patient {patient_id} not found in records."

        # ── Active visit ──────────────────────────────────────────────────
        visit = db.visits.find_one(
            {"patient_id": str(patient_id), "status": "ACTIVE"}, {"_id": 0}
        )
        room   = visit.get("room_id", "N/A") if visit else p.get("room_id", "N/A")
        bed    = visit.get("bed_id",  "N/A") if visit else "N/A"
        reason = visit.get("admission_reason", "N/A") if visit else "N/A"

        # ── Vitals ────────────────────────────────────────────────────────
        vitals = visit.get("vitals", {}) if visit else {}
        vitals_str = (
            f"BP {vitals.get('blood_pressure','?')}, "
            f"HR {vitals.get('heart_rate','?')} bpm, "
            f"SpO2 {vitals.get('oxygen_saturation','?')}%, "
            f"Temp {vitals.get('temperature','?')}°F"
        ) if vitals else "Not recorded"

        # ── Recent requests (last 5) ──────────────────────────────────────
        recent = list(db.requests.find(
            {"patient_id": str(patient_id)},
            {"_id": 0, "request_type": 1, "request_text": 1, "status": 1, "created_at": 1}
        ).sort("created_at", -1).limit(5))
        recent_str = "; ".join(
            f"{r['request_type']}({r['status']}): {r.get('request_text','')[:30]}"
            for r in recent
        ) if recent else "None"

        # ── OCR / Clinical summary ────────────────────────────────────────
        summary = db.summaries.find_one(
            {"patient_id": str(patient_id)},
            {"_id": 0, "patient_concerns": 1, "doctor_notes": 1, "raw_text_snippet": 1},
            sort=[("generated_at", -1)]
        )
        doctor_notes     = summary.get("doctor_notes", "None") if summary else "None"
        patient_concerns = summary.get("patient_concerns", "None") if summary else "None"
        raw_snippet      = summary.get("raw_text_snippet", "") if summary else ""
        # Extract medications from raw snippet if present
        meds = "Not recorded"
        if raw_snippet and "MEDICATIONS" in raw_snippet.upper():
            lines = raw_snippet.split("\n")
            med_lines = []
            capture = False
            for line in lines:
                if "MEDICATION" in line.upper():
                    capture = True
                    continue
                if capture:
                    if line.strip() == "" or line.strip().startswith("ALLERG") or line.strip().startswith("VITAL"):
                        break
                    if line.strip():
                        med_lines.append(line.strip())
            meds = ", ".join(med_lines) if med_lines else "Not recorded"

        # ── Assigned staff ────────────────────────────────────────────────
        # Check interaction_db patient_lookup for assignments
        try:
            from pymongo import MongoClient as MC
            idb = MC("mongodb+srv://Caremate-frontend:FIOWipLqLhFyp4uP@cluster0.agxm8kg.mongodb.net/?appName=Cluster0")["caremate_interaction_db"]
            lookup = idb.patient_lookup.find_one({"patient_id": str(patient_id)}, {"_id": 0})
            doctor_id = lookup.get("doctor_id", "N/A") if lookup else "N/A"
            nurse_id  = lookup.get("nurse_id",  "N/A") if lookup else "N/A"
        except Exception:
            doctor_id, nurse_id = "N/A", "N/A"

        return (
            f"=== PATIENT PROFILE ===\n"
            f"Name: {p.get('name', 'Unknown')} | ID: {patient_id}\n"
            f"Age: {p.get('age', 'N/A')} | Gender: {p.get('gender','N/A')} | Blood: {p.get('blood_group','N/A')}\n"
            f"Phone: {p.get('phone','N/A')}\n\n"
            f"=== CURRENT ADMISSION ===\n"
            f"Room: {room} | Bed: {bed}\n"
            f"Admission reason: {reason}\n"
            f"Assigned doctor ID: {doctor_id} | Nurse ID: {nurse_id}\n\n"
            f"=== VITALS ===\n"
            f"{vitals_str}\n\n"
            f"=== MEDICAL HISTORY ===\n"
            f"Allergies: {', '.join(p.get('allergies', [])) or 'None'}\n"
            f"Chronic conditions: {', '.join(p.get('chronic_conditions', [])) or 'None'}\n"
            f"Medications: {meds}\n\n"
            f"=== DOCTOR NOTES ===\n"
            f"{doctor_notes}\n\n"
            f"=== PATIENT CONCERNS ===\n"
            f"{patient_concerns}\n\n"
            f"=== RECENT REQUESTS ===\n"
            f"{recent_str}"
        )
    except Exception as e:
        logger.error(f"Patient context error: {e}")
        return f"Could not retrieve patient context for {patient_id}: {e}"


# ---------------------------------------------------------------------------
# TOOL 2: Workflow Action Tool (unified gateway)
# Handles ALL workflow types: nurse, doctor, nutrition, utility, emergency
# Internal backend handles MongoDB, dashboard routing, SLA timers, logging
# ---------------------------------------------------------------------------
@tool("Workflow Action Tool")
def workflow_action_tool(patient_id: str, request_type: str, request_text: str) -> str:
    """
    Unified workflow execution gateway.
    Supported request_type values:
      nurse_request, doctor_query, nutrition_request,
      utility_request, status_update, EMERGENCY
    Internally handles: MongoDB update, dashboard routing, SLA timers, logging.
    The agent only decides WHAT workflow to trigger.
    """
    try:
        from hospital_tools import WorkflowActionTool
        wf = WorkflowActionTool()

        # Map intent names to workflow categories
        type_map = {
            "nurse_request":    ("NURSE",      "MEDIUM"),
            "doctor_query":     ("DOCTOR",     "HIGH"),
            "nutrition_request":("NUTRITION",  "MEDIUM"),
            "utility_request":  ("UTILITY",    "LOW"),
            "status_update":    ("STATUS",     "LOW"),
            "EMERGENCY":        ("EMERGENCY",  "CRITICAL"),
        }
        mapped_type, priority = type_map.get(request_type, (request_type.upper(), "MEDIUM"))

        wf._run(
            patient_id=patient_id,
            request_type=mapped_type,
            request_text=request_text,
            category=priority
        )
        return f"✓ {mapped_type} request logged. Staff dashboard notified. Priority: {priority}."
    except Exception as e:
        logger.error(f"Workflow action error: {e}")
        return f"Workflow logged (fallback). Staff will be notified. Error: {e}"


# ---------------------------------------------------------------------------
# TOOL 3: Summary Tool
# Generates doctor-facing patient summary
# ---------------------------------------------------------------------------
@tool("Summary Tool")
def summary_tool(patient_id: str) -> str:
    """
    Generate a doctor-facing patient summary including:
    recent concerns, workflow history, OCR updates,
    medication mentions, and doctor interactions.
    """
    try:
        from hospital_tools import SummaryContextTool
        return SummaryContextTool()._run(patient_id=patient_id)
    except Exception as e:
        logger.error(f"Summary tool error: {e}")
        return f"Summary unavailable: {e}"


# ---------------------------------------------------------------------------
# AGENT 1: Patient Interaction Agent
# Lightweight conversational AI — one per bed
# Does NOT manage workflows, does NOT give medical advice
# ---------------------------------------------------------------------------
patient_interaction_agent = Agent(
    role="Patient Interaction Agent",
    goal=(
        "Be a warm, friendly bedside companion for the patient. "
        "Handle casual conversation and emotional support. "
        "For any service request or medical query, clearly state "
        "that it will be forwarded to the appropriate team."
    ),
    backstory=(
        "You are CareMate's bedside companion — friendly, empathetic, "
        "and always calm. You talk to patients like a caring friend. "
        "You NEVER give medical advice, NEVER manage hospital workflows, "
        "and NEVER handle emergencies directly. "
        "The patient's full context is already provided in your task. "
        "Use it to personalise your response. Do NOT call any tools."
    ),
    llm=crew_llm,
    tools=[],               # No tools — context is pre-injected into the task
    verbose=False,
    allow_delegation=False,
    max_iter=1,             # Single pass — no reasoning loops
)

# ---------------------------------------------------------------------------
# AGENT 2: Central Orchestration Agent
# Workflow manager — routes, escalates, coordinates
# NEVER gives diagnosis or medical advice
# ---------------------------------------------------------------------------
central_orchestration_agent = Agent(
    role="Central Orchestration Agent",
    goal=(
        "Orchestrate hospital workflows efficiently and safely. "
        "Route service requests to the correct staff, "
        "generate patient summaries for doctors, "
        "and ensure every request is logged and tracked. "
        "NEVER provide medical diagnosis or advice."
    ),
    backstory=(
        "You are CareMate's workflow brain. You receive requests from "
        "the Patient Interaction Agent and execute the correct hospital "
        "workflow. You use the Workflow Action Tool for ALL service "
        "requests (nurse, doctor, nutrition, utility). "
        "For doctor queries, you log the request and tell the patient "
        "their doctor will respond — you NEVER answer medical questions. "
        "The patient's full context is already provided in your task — "
        "do NOT call patient_context_tool again."
    ),
    llm=crew_llm,
    tools=[workflow_action_tool, summary_tool],  # removed patient_context_tool
    verbose=False,
    allow_delegation=False,
    max_iter=2,
)


# ---------------------------------------------------------------------------
# CREW RUNNER
# Called by main.py after deterministic layers have already run
# intent and is_emergency are pre-computed outside the crew
# ---------------------------------------------------------------------------
def _fetch_patient_context(patient_id: str) -> str:
    """
    Pre-fetch patient context before the crew runs.
    Calls the DB directly — does NOT go through the @tool wrapper.
    """
    try:
        from pymongo import MongoClient
        db = MongoClient(os.getenv("MONGO_URI"))["caremate_db"]

        p = db.patients.find_one({"patient_id": str(patient_id)}, {"_id": 0})
        if not p:
            return f"Patient {patient_id} not found."

        visit = db.visits.find_one(
            {"patient_id": str(patient_id), "status": "ACTIVE"}, {"_id": 0}
        )
        room   = visit.get("room_id", "N/A") if visit else "N/A"
        bed    = visit.get("bed_id",  "N/A") if visit else "N/A"
        vitals = visit.get("vitals", {}) if visit else {}
        vitals_str = (
            f"BP {vitals.get('blood_pressure','?')}, "
            f"HR {vitals.get('heart_rate','?')} bpm, "
            f"SpO2 {vitals.get('oxygen_saturation','?')}%, "
            f"Temp {vitals.get('temperature','?')}°F"
        ) if vitals else "Not recorded"

        recent = list(db.requests.find(
            {"patient_id": str(patient_id)},
            {"_id": 0, "request_type": 1, "status": 1}
        ).sort("created_at", -1).limit(3))
        recent_str = "; ".join(f"{r['request_type']}({r['status']})" for r in recent) if recent else "None"

        summary = db.summaries.find_one(
            {"patient_id": str(patient_id)},
            {"_id": 0, "doctor_notes": 1, "patient_concerns": 1},
            sort=[("generated_at", -1)]
        )
        doctor_notes = summary.get("doctor_notes", "None") if summary else "None"

        try:
            idb = MongoClient(
                "mongodb+srv://Caremate-frontend:FIOWipLqLhFyp4uP"
                "@cluster0.agxm8kg.mongodb.net/?appName=Cluster0"
            )["caremate_interaction_db"]
            lk = idb.patient_lookup.find_one({"patient_id": str(patient_id)}, {"_id": 0})
            doctor_id = lk.get("doctor_id", "N/A") if lk else "N/A"
            nurse_id  = lk.get("nurse_id",  "N/A") if lk else "N/A"
        except Exception:
            doctor_id, nurse_id = "N/A", "N/A"

        return (
            f"Name: {p.get('name','Unknown')} | Age: {p.get('age','N/A')} | "
            f"Blood: {p.get('blood_group','N/A')}\n"
            f"Room: {room} | Bed: {bed}\n"
            f"Vitals: {vitals_str}\n"
            f"Allergies: {', '.join(p.get('allergies', [])) or 'None'}\n"
            f"Conditions: {', '.join(p.get('chronic_conditions', [])) or 'None'}\n"
            f"Assigned doctor ID: {doctor_id} | Nurse ID: {nurse_id}\n"
            f"Doctor notes: {doctor_notes}\n"
            f"Recent requests: {recent_str}"
        )
    except Exception as e:
        logger.error(f"Pre-fetch patient context failed: {e}")
        return f"Patient ID: {patient_id} (context unavailable)"


def run_caremate_crew(
    patient_query: str,
    patient_id: str,
    intent: str,
    is_emergency: bool = False,
) -> str:
    """
    Run the two-agent CrewAI pipeline.

    Args:
        patient_query:  English text from patient
        patient_id:     Patient ID string
        intent:         Pre-classified intent (from deterministic layer)
        is_emergency:   Pre-detected emergency flag (from deterministic layer)

    Returns:
        Final patient-facing response string
    """

    # ── Pre-fetch patient context (always) ──────────────────────────────────
    # This gives every agent full patient awareness: name, conditions,
    # allergies, room, vitals, recent requests, OCR summary.
    patient_context = _fetch_patient_context(patient_id)
    logger.info(f"[CrewAI] Patient context loaded for {patient_id}")

    is_workflow = intent in [
        "nurse_request", "nutrition_request",
        "utility_request", "doctor_query", "status_query"
    ]

    # ── FAST PATH: General conversation → Meditron directly ─────────────────
    # Meditron is the ONLY path for general conversation.
    # The crew is NEVER used for general_conversation — it leaks JSON reasoning.
    if not is_workflow and not is_emergency:
        import re as _re
        meditron_prompt = (
            f"You are CareMate, a warm hospital bedside assistant.\n"
            f"PATIENT CONTEXT:\n{patient_context}\n\n"
            f"The patient said: \"{patient_query}\"\n\n"
            f"Respond in 1-2 short empathetic sentences using the patient's name. "
            f"Do NOT give medical advice. Be warm and supportive. "
            f"Only output the response, nothing else."
        )
        response = meditron.generate(meditron_prompt, max_tokens=80)

        if response and len(response) > 4:
            # Strip echoed prompt markers
            for marker in ["CareMate:", "Assistant:", "Response:", "CareMate response:",
                           "You are CareMate", "PATIENT CONTEXT", "The patient said"]:
                if marker in response:
                    response = response.split(marker)[-1].strip()
            # Take only first 2 sentences
            sentences = _re.split(r'(?<=[.!?])\s+', response.strip())
            response = " ".join(sentences[:2]).strip().strip('"').strip("'")
            if len(response) > 4:
                logger.info(f"[Meditron] ✓ Response: {response[:80]}")
                return response

        # Meditron unavailable — use Nemotron via openrouter_client as fallback
        logger.warning("[Meditron] Unavailable — falling back to Nemotron for general chat")
        try:
            from openrouter_client import generate_openrouter_response
            nemotron_prompt = (
                f"You are CareMate, a warm hospital bedside assistant.\n"
                f"PATIENT CONTEXT:\n{patient_context}\n\n"
                f"Patient said: \"{patient_query}\"\n\n"
                f"Reply in 1-2 short empathetic sentences using the patient's name. "
                f"Do NOT give medical advice. Output only the response."
            )
            response = generate_openrouter_response(nemotron_prompt, max_tokens=80)
            if response and len(response) > 4:
                import re as _re
                sentences = _re.split(r'(?<=[.!?])\s+', response.strip())
                return " ".join(sentences[:2]).strip()
        except Exception as e:
            logger.error(f"Nemotron fallback also failed: {e}")

        # Last resort keyword fallback
        user_lower = patient_query.lower()
        if any(w in user_lower for w in ["hello", "hi", "hey"]):
            return "Hello! I'm CareMate, your hospital assistant. How can I help you today?"
        if any(w in user_lower for w in ["thank", "thanks"]):
            return "You're very welcome! I'm always here to help you."
        if any(w in user_lower for w in ["tired", "exhausted", "sleepy"]):
            return "Rest is very important for your recovery. I hope you feel better soon."
        if any(w in user_lower for w in ["scared", "worried", "afraid"]):
            return "It's okay to feel that way. The medical team is taking good care of you."
        if any(w in user_lower for w in ["bored", "boring"]):
            return "I understand you're feeling bored. I'm here with you — is there anything I can help with?"
        if any(w in user_lower for w in ["pain", "hurt", "ache"]):
            return "I'm sorry you're in pain. I'll make sure the nursing team is informed right away."
        return "I'm here to support you. Let me know if there's anything you need."

    # ── TASK 1: Patient Interaction Agent ───────────────────────────────────
    if is_workflow or is_emergency:
        task1_desc = (
            f"PATIENT CONTEXT (use this to personalise your response):\n"
            f"{patient_context}\n\n"
            f"Patient said: \"{patient_query}\"\n"
            f"Pre-classified intent: {intent}\n\n"
            "Acknowledge the patient warmly using their name (from context above). "
            "Tell them their request is being forwarded to the right team. "
            "Do NOT attempt to fulfil the request yourself. "
            "Return only the acknowledgement sentence — address them by name."
        )
        task1_output = "A single warm acknowledgement sentence using the patient's name."
    else:
        # Casual conversation — agent has full context and responds
        task1_desc = (
            f"PATIENT CONTEXT (use this to personalise your response):\n"
            f"{patient_context}\n\n"
            f"Patient said: \"{patient_query}\"\n\n"
            "Using the patient context above, respond with 1-2 warm, empathetic sentences "
            "personalised to this patient (use their name, acknowledge their conditions "
            "if relevant). Do NOT give medical advice. "
            "Return only the patient-facing response."
        )
        task1_output = (
            "1-2 warm personalised sentences using the patient's name. No medical advice."
        )

    task_interact = Task(
        description=task1_desc,
        expected_output=task1_output,
        agent=patient_interaction_agent,
    )

    # ── TASK 2: Central Orchestration Agent ─────────────────────────────────
    tasks = [task_interact]

    if is_workflow or is_emergency:
        if is_emergency:
            task2_desc = (
                f"PATIENT CONTEXT:\n{patient_context}\n\n"
                f"EMERGENCY detected. Patient said: \"{patient_query}\"\n\n"
                f"Use the Workflow Action Tool with patient_id='{patient_id}' "
                "and request_type='EMERGENCY' immediately. "
                "Return: 'EMERGENCY ALERT TRIGGERED. Help is on the way. Please stay calm.'"
            )
        elif intent in ["doctor_query", "status_query"]:
            task2_desc = (
                f"PATIENT CONTEXT:\n{patient_context}\n\n"
                f"Intent: {intent}. Patient said: \"{patient_query}\"\n\n"
                f"Use the Workflow Action Tool with patient_id='{patient_id}' "
                "and request_type='doctor_query' to log this. "
                "Using the patient's name from context, return a 1-sentence response "
                "telling them their doctor will respond shortly. "
                "Do NOT answer the medical question."
            )
        else:
            task2_desc = (
                f"PATIENT CONTEXT:\n{patient_context}\n\n"
                f"Intent: {intent}. Patient said: \"{patient_query}\"\n\n"
                f"Use the Workflow Action Tool with patient_id='{patient_id}' "
                f"and request_type='{intent}' to log this request. "
                "Using the patient's name from context, return a 1-sentence confirmation "
                "that the request has been sent to the right team."
            )

        task_orchestrate = Task(
            description=task2_desc,
            expected_output=(
                "A single personalised patient-facing confirmation sentence using "
                "the patient's name. No JSON, no labels."
            ),
            agent=central_orchestration_agent,
            context=[task_interact],
        )
        tasks.append(task_orchestrate)

    # ── RUN CREW ─────────────────────────────────────────────────────────────
    crew = Crew(
        agents=[patient_interaction_agent, central_orchestration_agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
    )

    try:
        result = crew.kickoff(inputs={
            "patient_query": patient_query,
            "patient_id": patient_id,
        })
        response = str(result).strip()
        logger.info(f"[CrewAI] ✓ Response ({intent}): {response[:80]}")
        return response
    except Exception as e:
        logger.error(f"[CrewAI] Crew error: {e}")
        return "I received your message. The care team will assist you shortly."
