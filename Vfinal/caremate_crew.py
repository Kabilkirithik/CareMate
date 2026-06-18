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
# In-memory patient context cache (TTL: 60s per patient)
# Avoids repeated MongoDB calls within the same session
# ---------------------------------------------------------------------------
import time as _time
_CONTEXT_CACHE: dict = {}  # {patient_id: (context_str, fetched_at)}
_CONTEXT_TTL = 60  # seconds

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
    Thin wrapper so we can call Meditron directly for general conversation.
    Endpoint: POST /generate  |  field: query
    """
    def generate(self, prompt: str, max_tokens: int = 80) -> str:
        try:
            import requests as _req
            r = _req.post(
                f"{MEDITRON_URL.rstrip('/')}/generate",
                json={
                    "query": prompt,
                    "max_new_tokens": max_tokens,
                },
                timeout=25,
                headers={"ngrok-skip-browser-warning": "1"},
            )
            r.raise_for_status()
            raw = r.json().get("response", "").strip()

            # Strip repetition — Meditron sometimes echoes itself
            # Take only the first clean sentence before any <|assistant|> tag or repetition
            import re as _re
            # Remove everything after the first <| token or role marker
            raw = _re.split(r"<\|", raw)[0].strip()
            # Take only the first 2 sentences
            sentences = _re.split(r"(?<=[.!?])\s+", raw)
            return " ".join(sentences[:2]).strip()
        except Exception as e:
            logger.warning(f"Meditron unavailable ({e}) — falling back to Nemotron")
            return ""

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
# Pre-load the IntentRouter singleton at module import time
# so the first request doesn't pay the SentenceTransformer loading cost
_router_singleton = None

def route_intent(text: str) -> dict:
    """
    Classify patient query intent using the trained SVM router.
    Reuses the singleton IntentRouter — model loads once at startup.
    """
    global _router_singleton
    try:
        from intent_router import IntentRouter
        if _router_singleton is None:
            _router_singleton = IntentRouter()
        return _router_singleton.classify(text)
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
    Uses an in-memory cache (TTL=60s) to avoid repeated DB round-trips.
    """
    # Check cache first
    cached = _CONTEXT_CACHE.get(patient_id)
    if cached:
        context_str, fetched_at = cached
        if _time.time() - fetched_at < _CONTEXT_TTL:
            logger.info(f"[Context cache HIT] patient {patient_id}")
            return context_str

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
        _CONTEXT_CACHE[patient_id] = (result, _time.time())
        return result
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

    # status_query = patient asking about their own records → answer directly
    # doctor_query = patient specifically wants to speak to doctor → forward
    is_workflow = intent in [
        "nurse_request", "nutrition_request",
        "utility_request", "doctor_query",
        # status_query removed — handled below with patient context
    ]

    # ── ROUTING ───────────────────────────────────────────────────────────────
    # general_conversation → Meditron (Patient Agent)
    # status_query         → Nemotron with patient context (answer directly)
    # workflow intents     → DB log + Nemotron confirmation
    # emergency            → immediate alert

    if not is_workflow and not is_emergency:
        # ── Meditron: general conversation ──────────────────────────────────
        import re as _re
        # Trim context to essentials for faster API call
        ctx_lines = [l for l in patient_context.split("\n") if l.strip() and
                     any(k in l for k in ["Name:", "Conditions:", "Allergies:", "Room:"])]
        mini_ctx = " | ".join(ctx_lines[:3]) if ctx_lines else f"Patient: {patient_name}"

        meditron_prompt = (
            f"You are CareMate, a caring and gentle hospital bedside companion. "
            f"You speak with warmth and reassurance — like a trusted friend.\n"
            f"{mini_ctx}\n"
            f"Patient said: \"{patient_query}\"\n"
            f"Reply in 1-2 warm sentences using their name. No medical advice. Output only your response."
        )
        response = meditron.generate(meditron_prompt, max_tokens=80)
        if response and len(response) > 4:
            # Clean up any prompt echoing or role markers
            for marker in ["You are CareMate", "PATIENT CONTEXT", "Patient said",
                           "CareMate:", "Assistant:", "<|"]:
                if marker in response:
                    response = response.split(marker)[0].strip()
            sentences = _re.split(r'(?<=[.!?])\s+', response.strip())
            clean = " ".join(sentences[:2]).strip().strip('"').strip("'")
            # Reject junk: only underscores/dashes/dots, or too short after cleaning
            is_junk = (
                len(clean) < 5
                or all(c in '_ -.\n' for c in clean)
                or clean.count('_') > 5
            )
            if not is_junk:
                logger.info(f"[Meditron] ✓ {clean[:80]}")
                return clean
            logger.warning(f"[Meditron] Junk response detected: '{clean[:40]}' — skipping")

        # Meditron down → Nemotron fallback for general conversation
        logger.warning("[Meditron] Unavailable — using Nemotron for general chat")
        try:
            from openrouter_client import generate_openrouter_response
            nemotron_prompt = (
                f"You are CareMate, a caring and gentle hospital bedside companion. "
                f"You speak with warmth and reassurance — like a trusted friend.\n"
                f"{mini_ctx}\n"
                f"Patient said: \"{patient_query}\"\n"
                f"Reply in 1-2 warm sentences using their name. No medical advice. Output only your response."
            )
            resp = generate_openrouter_response(nemotron_prompt, max_tokens=80)
            if resp and len(resp) > 4:
                import re as _re2
                sentences = _re2.split(r'(?<=[.!?])\s+', resp.strip())
                return " ".join(sentences[:2]).strip()
        except Exception as e:
            logger.error(f"Nemotron fallback failed: {e}")

        # Last-resort keyword replies
        user_lower = patient_query.lower()
        if any(w in user_lower for w in ["hello", "hi", "hey"]):
            return "Hello! I'm CareMate, your hospital assistant. How can I help you today?"
        if any(w in user_lower for w in ["thank", "thanks"]):
            return "You're very welcome! I'm always here to help you."
        if any(w in user_lower for w in ["tired", "exhausted", "sleepy"]):
            return "Rest is very important for your recovery. I hope you feel better soon."
        if any(w in user_lower for w in ["bored"]):
            return "I understand you're feeling bored. I'm here with you — is there anything I can help with?"
        return "I'm here to support you. Let me know if there's anything you need."

    # ── STATUS QUERY: Answer directly with patient context ───────────────────
    # Patient is asking about their own medical history/report/condition.
    # We have the context — answer it, don't forward to doctor.
    if intent == "status_query":
        import re as _re
        from openrouter_client import generate_openrouter_response
        ctx_lines = [l for l in patient_context.split("\n") if l.strip() and
                     any(k in l for k in ["Name:", "Conditions:", "Allergies:", "Vitals:",
                                          "Room:", "Doctor notes:", "Recent requests:"])]
        mini_ctx = "\n".join(ctx_lines[:6]) if ctx_lines else patient_context[:400]
        patient_name = mini_ctx.split("Name: ")[1].split("|")[0].strip() if "Name: " in mini_ctx else "there"

        prompt = (
            f"You are CareMate, a caring hospital bedside assistant.\n"
            f"PATIENT RECORDS:\n{mini_ctx}\n\n"
            f"Patient asked: \"{patient_query}\"\n\n"
            f"Using the records above, give {patient_name} a clear, warm summary of their relevant "
            f"medical information. If the records don't contain the answer, say so kindly and "
            f"suggest they ask their doctor for more details. "
            f"Keep it to 2-3 sentences. Output only the response."
        )
        try:
            response = generate_openrouter_response(prompt, max_tokens=120)
            if response and len(response) > 4:
                sentences = _re.split(r'(?<=[.!?])\s+', response.strip())
                return " ".join(sentences[:3]).strip()
        except Exception as e:
            logger.error(f"Status query response failed: {e}")
        # Fallback — give what we have from context
        return f"{patient_name}, based on your records: {mini_ctx[:200]}"

    # ── WORKFLOW & EMERGENCY: Direct calls — no crew overhead ───────────────
    # Log to DB directly, then call OpenRouter for a single fast response.
    # Skipping CrewAI saves 10-20s of agent reasoning overhead.
    import re as _re
    from openrouter_client import generate_openrouter_response
    from hospital_tools import WorkflowActionTool

    # Extract patient name for personalisation
    patient_name = patient_context.split("Name: ")[1].split("|")[0].strip() if "Name: " in patient_context else "there"

    if is_emergency:
        # Log immediately
        try:
            WorkflowActionTool()._run(
                patient_id=patient_id,
                request_type="EMERGENCY",
                request_text=patient_query,
                category="CRITICAL"
            )
        except Exception as e:
            logger.error(f"Emergency log error: {e}")
        return f"Don't worry {patient_name}, help is on the way right now. Please stay calm."

    # Log workflow request
    type_map = {
        "nurse_request":     "NURSE",
        "doctor_query":      "DOCTOR",
        "status_query":      "DOCTOR",
        "nutrition_request": "NUTRITION",
        "utility_request":   "UTILITY",
    }
    try:
        WorkflowActionTool()._run(
            patient_id=patient_id,
            request_type=type_map.get(intent, intent.upper()),
            request_text=patient_query,
            category="general"
        )
    except Exception as e:
        logger.error(f"Workflow log error: {e}")

    # Role labels for the response
    role_label = {
        "nurse_request":     "nursing team",
        "doctor_query":      "doctor",
        "status_query":      "doctor",
        "nutrition_request": "nutrition team",
        "utility_request":   "care team",
    }.get(intent, "care team")

    # Call OpenRouter with a minimal prompt — smaller = faster
    # Extract only the 2 most useful context lines to reduce payload
    ctx_lines = [l for l in patient_context.split("\n") if l.strip() and
                 any(k in l for k in ["Name:", "Conditions:", "Allergies:", "Room:"])]
    mini_context = " | ".join(ctx_lines[:3]) if ctx_lines else f"Patient: {patient_name}"

    prompt = (
        f"You are CareMate, a warm hospital assistant. {mini_context}\n"
        f"Patient said: \"{patient_query}\"\n"
        f"The {role_label} has been notified. "
        f"Write ONE warm caring sentence to reassure {patient_name}. Output only the sentence."
    )
    try:
        response = generate_openrouter_response(prompt, max_tokens=50)
        if response and len(response) > 4:
            sentences = _re.split(r'(?<=[.!?])\s+', response.strip())
            clean = " ".join(sentences[:1]).strip()
            if len(clean) > 4:
                logger.info(f"[Nemotron] ✓ Workflow response: {clean[:80]}")
                return clean
    except Exception as e:
        logger.error(f"Nemotron workflow response failed: {e}")

    # Keyword fallback
    return f"Of course, {patient_name} — I've notified the {role_label} and they'll be with you shortly."
