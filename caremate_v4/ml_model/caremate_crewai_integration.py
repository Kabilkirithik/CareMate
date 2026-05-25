"""
CareMate — CrewAI Integration with Intent Classifier
=====================================================
This shows how to wire the ML classifier into your existing
CrewAI architecture as the pre-routing gate.

Flow:
    Patient Speech
        ↓
    STT Tool  (Patient Agent)
        ↓
    IntentClassifierTool  ← ML model fires here
        ↓              ↓
    Patient Agent    Central Agent
    (casual chat)    (all other intents)
        ↓              ↓
      LLM Response ←──┘
        ↓
    TTS Tool  (Patient Agent)
        ↓
    Patient hears response
"""

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

from intent_classifier import CareMateClassifier


# ── Singleton classifier (load once, reuse across requests) ──────────────────
_classifier = CareMateClassifier()


# ── Pydantic input schema for the tool ───────────────────────────────────────
class IntentInput(BaseModel):
    text: str = Field(..., description="Patient utterance to classify")


# ── CrewAI Tool wrapper ───────────────────────────────────────────────────────
class IntentClassifierTool(BaseTool):
    """
    Classifies patient text into an intent and returns
    the routing decision (which agent / tool to invoke).
    """
    name: str = "intent_classifier"
    description: str = (
        "Classify the patient's utterance into one of 8 intents: "
        "emergency, nurse_request, doctor_query, nutrition_request, "
        "utility_request, status_query, document_submission, or "
        "general_conversation. Returns the intent, the target agent, "
        "and the suggested tool to invoke."
    )
    args_schema: Type[BaseModel] = IntentInput

    def _run(self, text: str) -> str:
        result = _classifier.predict(text)
        return (
            f"intent={result['intent']} | "
            f"agent={result['agent']} | "
            f"tool={result['tool']} | "
            f"confidence={result['confidence']:.2%}"
        )


# ── Example: Minimal agent setup showing classifier integration ──────────────

intent_tool = IntentClassifierTool()

patient_agent = Agent(
    role="Patient Interaction Agent",
    goal=(
        "Interact with the patient via speech. Use the intent_classifier "
        "to decide whether to handle the request locally (general_conversation) "
        "or escalate to the Central Orchestration Agent."
    ),
    backstory=(
        "You are the frontline conversational agent for CareMate. "
        "You speak with the patient, process speech via STT, classify intent, "
        "and deliver the final response via TTS. "
        "You handle general_conversation directly and delegate everything else."
    ),
    tools=[intent_tool],   # add your STT / TTS / Emergency tools here too
    verbose=True,
)

central_agent = Agent(
    role="Central Orchestration Agent",
    goal=(
        "Receive escalated intents from the Patient Agent and orchestrate "
        "the correct workflow tool: nurse dashboard, doctor voice, "
        "nutritionist approval, utility service, status tracking, or OCR."
    ),
    backstory=(
        "You are the core decision-making unit of CareMate. "
        "You never give medical advice. You route requests to the correct "
        "dashboard or service and track workflow state."
    ),
    tools=[],   # add your Nurse / Doctor / Nutrition / Utility tools here
    verbose=True,
)


# ── Example task showing the full routing flow ────────────────────────────────
def handle_patient_utterance(utterance: str):
    """
    Entry point: called with post-STT text from the patient.
    Classifier fires first, then routes to the right agent.
    """
    # Step 1 — classify
    classification = _classifier.predict(utterance)
    print(f"\n🧠 Classifier: {classification['intent']} "
          f"({classification['confidence']:.0%} confidence) "
          f"→ {classification['agent']}")

    # Step 2 — route
    if classification["agent"] == "patient_agent":
        # Handle locally — general conversation
        task = Task(
            description=f"Respond to the patient in a friendly, caring way: '{utterance}'",
            expected_output="A warm conversational response in the patient's language.",
            agent=patient_agent,
        )
    else:
        # Escalate to central agent with full context
        task = Task(
            description=(
                f"Patient said: '{utterance}'\n"
                f"Classified intent: {classification['intent']}\n"
                f"Suggested tool: {classification['tool']}\n"
                f"Invoke the appropriate tool and resolve the patient's request."
            ),
            expected_output="Confirmation that the request has been routed and actioned.",
            agent=central_agent,
        )

    crew = Crew(
        agents=[patient_agent, central_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return result


# ── Quick smoke test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    samples = [
        "I cannot breathe",
        "Can you send a nurse",
        "How are you today",
        "I need a blanket",
    ]
    for s in samples:
        r = _classifier.predict(s)
        print(f"  '{s}'")
        print(f"    → intent={r['intent']}, agent={r['agent']}, tool={r['tool']}\n")
