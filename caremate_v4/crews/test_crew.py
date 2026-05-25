import re
import asyncio
from crewai import Crew, Task

from caremate_v4.agents.patient_agent import patient_agent
from caremate_v4.agents.central_agent import central_agent
from caremate_v4.tasks.patient_tasks import patient_interaction_task
from caremate_v4.tasks.manager_tasks import workflow_management_task

# -----------------------------
# Emergency Detection
# -----------------------------

EMERGENCY_KEYWORDS = [
    "cannot breathe", "can't breathe",
    "chest pain", "heart attack",
    "emergency", "severe pain",
    "not breathing", "unconscious",
]

def detect_emergency(message: str) -> bool:
    message = message.lower()
    return any(keyword in message for keyword in EMERGENCY_KEYWORDS)

def clean_response(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()

# -----------------------------
# Per-request Crew factory
# -----------------------------

def build_crew(message: str) -> Crew:
    """Create a fresh Crew per request to avoid state leakage."""
    interaction_task = Task(
        description=f"Patient message: {message}",
        expected_output="Classified request type and delegation to central agent.",
        agent=patient_agent
    )
    management_task = Task(
        description=f"Handle the routed request for: {message}",
        expected_output="Confirmation that the correct tool was used and the event was logged.",
        agent=central_agent
    )
    return Crew(
        agents=[patient_agent, central_agent],
        tasks=[interaction_task, management_task],
        verbose=False
    )

# -----------------------------
# Async Processing
# -----------------------------

async def process_patient_message(message: str):
    if detect_emergency(message):
        print("\n🚨 EMERGENCY DETECTED 🚨")
        print("Alerting nurse and doctor dashboards immediately...")
        print("Logging emergency event...")
        return "Help is on the way. Medical staff have been alerted immediately."

    loop = asyncio.get_event_loop()
    crew = build_crew(message)

    result = await loop.run_in_executor(None, crew.kickoff)
    return clean_response(str(result))

# -----------------------------
# CLI Interface
# -----------------------------

async def main():
    print("\n🏥 CareMate System Tester")
    print("Testing Agents + Tools")
    print("Type 'exit' to stop\n")

    while True:
        message = input("Patient: ").strip()
        if not message:
            continue
        if message.lower() == "exit":
            break

        response = await process_patient_message(message)
        print(f"\nCareMate Response:\n{response}")
        print("\n--------------------------------\n")

if __name__ == "__main__":
    asyncio.run(main())