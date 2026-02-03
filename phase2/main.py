import json
import os
from enum import Enum
from typing import List
from pydantic import BaseModel, Field

from crewai import Agent, Crew, Process, Task, LLM
from crewai.tools.base_tool import BaseTool

# Initialize Gemini LLM
gemini_llm = LLM(
    model="gemini/gemini-2.0-flash",
    api_key=os.getenv("GEMINI_API_KEY"),  # Or set GOOGLE_API_KEY/GEMINI_API_KEY
    temperature=0.7
)

# --- TOOL DEFINITIONS ---
# Tools are stateless helpers for agents.

class PatientFileRetrievalTool(BaseTool):
    name: str = "PatientFileRetrievalTool"
    description: str = "Fetches a patient's medical profile using their patient ID."

    def _run(self, patient_id: str) -> str:
        """
        Mocks fetching patient data.
        In a real scenario, this would query a secure database.
        """
        print(f"--- TOOL: Retrieving file for patient_id: {patient_id} ---")
        # Mock data representing a patient's file
        mock_patient_data = {
            "patient_id": patient_id,
            "age": 78,
            "gender": "Female",
            "medical_conditions": ["Hypertension", "Type 2 Diabetes", "Previous Myocardial Infarction"],
            "medications": ["Lisinopril", "Metformin", "Aspirin"],
            "allergies": ["Penicillin"],
            "risk_flags": ["elderly", "cardiac_history", "fall_risk"]
        }
        return json.dumps(mock_patient_data)

class EmergencyAssessmentTool(BaseTool):
    name: str = "EmergencyAssessmentTool"
    description: str = "Detects emergency severity from a user's message based on keywords."

    class EmergencyLevel(str, Enum):
        NONE = "NONE"
        LOW = "LOW"
        MODERATE = "MODERATE"
        CRITICAL = "CRITICAL"

    def _run(self, user_message: str) -> str:
        """
        Mocks emergency assessment.
        A real tool would use a more sophisticated, rule-assisted NLP model.
        """
        print(f"--- TOOL: Assessing emergency level for message: '{user_message}' ---")
        message = user_message.lower()
        if "can't breathe" in message or "chest pain" in message or "not responding" in message:
            return self.EmergencyLevel.CRITICAL
        if "dizzy" in message or "severe headache" in message:
            return self.EmergencyLevel.MODERATE
        if "feeling unwell" in message or "slight pain" in message:
            return self.EmergencyLevel.LOW
        return self.EmergencyLevel.NONE

class ContextSummarizationTool(BaseTool):
    name: str = "ContextSummarizationTool"
    description: str = "Condenses long text into a concise summary."

    def _run(self, long_text: str) -> str:
        """Mocks text summarization."""
        print("--- TOOL: Summarizing context ---")
        return (long_text[:200] + '...') if len(long_text) > 200 else long_text

class EscalationPolicyTool(BaseTool):
    name: str = "EscalationPolicyTool"
    description: str = "Applies hard-coded escalation rules based on emergency level."

    class ActionDecision(str, Enum):
        EMERGENCY_PROTOCOL = "EMERGENCY_PROTOCOL"
        CAUTION_ADVISED = "CAUTION_ADVISED"
        ALLOW_AI_RESPONSE = "ALLOW_AI_RESPONSE"

    def _run(self, emergency_level: str) -> str:
        """Applies deterministic safety rules."""
        print(f"--- TOOL: Applying escalation policy for level: {emergency_level} ---")
        if emergency_level == EmergencyAssessmentTool.EmergencyLevel.CRITICAL:
            return self.ActionDecision.EMERGENCY_PROTOCOL
        if emergency_level == EmergencyAssessmentTool.EmergencyLevel.MODERATE:
            return self.ActionDecision.CAUTION_ADVISED
        return self.ActionDecision.ALLOW_AI_RESPONSE

class DomainMedicalLLMTool(BaseTool):
    name: str = "DomainMedicalLLMTool"
    description: str = "Provides domain-specific, non-diagnostic medical reasoning support."

    def _run(self, structured_query: str) -> str:
        """
        Mocks a call to a specialized medical LLM.
        The output is explicitly non-diagnostic.
        """
        print(f"--- TOOL: Running Domain Medical LLM with query: {structured_query} ---")
        return (
            "Based on the reported symptoms of dizziness and the patient's cardiac history, "
            "potential pathways to consider include hypotension or arrhythmia. "
            "This is not a diagnosis. Further assessment is required."
        )

class InteractionLoggingTool(BaseTool):
    name: str = "InteractionLoggingTool"
    description: str = "Logs agent decisions and system actions for auditability."

    def _run(self, log_entry: str) -> str:
        """Mocks logging by printing to the console."""
        print(f"--- AUDIT LOG: {log_entry} ---")
        return "Log confirmation"

# --- STRUCTURED OUTPUT MODEL ---
# Pydantic model for the strict, structured output from Agent 1

class Agent1Output(BaseModel):
    patient_context: dict = Field(description="The patient's profile information.")
    intent: str = Field(description="The classified user intent (e.g., SYMPTOM_QUERY).")
    emergency_level: str = Field(description="The assessed emergency level (NONE, LOW, MODERATE, CRITICAL).")
    risk_factors: List[str] = Field(description="Key risk factors from the patient's profile.")
    medical_reasoning: str = Field(description="Non-diagnostic medical insights from the domain LLM.")
    confidence_level: str = Field(description="The agent's confidence in its reasoning (LOW, MEDIUM, HIGH).")

# --- AGENT DEFINITIONS ---

# Initialize all tools
patient_file_tool = PatientFileRetrievalTool()
emergency_tool = EmergencyAssessmentTool()
summarization_tool = ContextSummarizationTool()
escalation_tool = EscalationPolicyTool()
medical_llm_tool = DomainMedicalLLMTool()
logging_tool = InteractionLoggingTool()

# Agent 1: Context & Intelligence Agent (Clinical Reasoning)
context_agent = Agent(
    role='Clinical Reasoning Agent',
    goal=(
        "Comprehensively analyze the user's message and patient context to produce a "
        "structured JSON output containing patient context, user intent, emergency level, "
        "risk factors, medical reasoning, and a confidence estimate. "
        "This output is for internal system use ONLY."
    ),
    backstory=(
        "You are a specialized AI agent designed for deep clinical reasoning. "
        "Your sole purpose is to understand and structure information. You do not interact with the user, "
        "make final decisions, or provide advice. You only analyze and output a JSON object."
    ),
    tools=[
        patient_file_tool,
        emergency_tool,
        summarization_tool,
        medical_llm_tool,
        logging_tool
    ],
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

# Agent 2: Control, Authorization & Response Agent (CareMate Orchestrator)
orchestrator_agent = Agent(
    role='CareMate Orchestrator Agent',
    goal=(
        "Act as the governance and safety layer. Based on the structured JSON from the "
        "Clinical Reasoning Agent, decide whether to escalate to an emergency protocol, "
        "ask clarifying questions, or generate a safe, non-diagnostic, and empathetic response to the user."
    ),
    backstory=(
        "You are the final checkpoint in the CareMate system. Your primary responsibility is safety. "
        "You are the ONLY agent that communicates with the user. You must ensure all responses are "
        "non-diagnostic, supportive, and action-oriented, and apply necessary disclaimers. "
        "You do not perform medical reasoning yourself; you only orchestrate the response based "
        "on the analysis provided to you."
    ),
    tools=[
        escalation_tool,
        summarization_tool,
        logging_tool
    ],
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

# --- TASK DEFINITIONS ---

# Sample inputs for the crew
PATIENT_ID = "PATIENT-12345"
# Try changing this message to "My mother is reporting severe chest pain and can't breathe."
USER_MESSAGE = "My mother is feeling very dizzy and has a severe headache."

# Task 1: Analyze the situation
context_task = Task(
    description=(
        f"Analyze the user's message: '{USER_MESSAGE}' in the context of the patient profile "
        f"retrieved for patient ID '{PATIENT_ID}'. Follow these steps:\n"
        "1. Retrieve the patient file using the PatientFileRetrievalTool.\n"
        "2. Assess the emergency level of the user's message using the EmergencyAssessmentTool.\n"
        "3. Use the DomainMedicalLLMTool to get a preliminary, non-diagnostic reasoning.\n"
        "4. Classify the user's intent (e.g., SYMPTOM_QUERY).\n"
        "5. Estimate a confidence level (LOW, MEDIUM, HIGH) based on the clarity of the information.\n"
        "6. Compile all this information into the required JSON format."
    ),
    expected_output=(
        "A single, validated JSON object that strictly adheres to the 'Agent1Output' pydantic model. "
        "This JSON will serve as the input for the next agent."
    ),
    agent=context_agent,
    response_format=Agent1Output,
)

# Task 2: Govern and Respond
orchestrator_task = Task(
    description=(
        "Using the structured JSON data from the Clinical Reasoning Agent, execute the final step. "
        "Follow this logic:\n"
        "1. Use the EscalationPolicyTool on the 'emergency_level' to decide the course of action.\n"
        "2. If the action is EMERGENCY_PROTOCOL, formulate a response that instructs the user to call emergency services immediately.\n"
        "3. If confidence is LOW, formulate a response asking empathetic and clear clarifying questions.\n"
        "4. If the action is ALLOW_AI_RESPONSE and confidence is not LOW, generate a safe, non-diagnostic AI guidance response. The response must be empathetic, mention the key risks, and include a clear disclaimer that this is not medical advice.\n"
        "5. Log the final action using the InteractionLoggingTool."
    ),
    expected_output=(
        "The final, user-facing response as a single string. This is the only text the user will see."
    ),
    agent=orchestrator_agent,
    context=[context_task] # This task depends on the output of the context_task
)

# --- CREW DEFINITION AND EXECUTION ---

# Assemble the crew
caremate_crew = Crew(
    agents=[context_agent, orchestrator_agent],
    tasks=[context_task, orchestrator_task],
    process=Process.sequential,
    verbose= True # Use verbose=2 for detailed, step-by-step agent execution logging
)

if __name__ == "__main__":
    print("🚀 Kicking off CareMate Crew...")
    print("---------------------------------")
    print(f"Patient ID: {PATIENT_ID}")
    print(f"User Message: {USER_MESSAGE}")
    print("---------------------------------")

    # Run the crew
    final_result = caremate_crew.kickoff()

    print("\n---------------------------------")
    print("✅ Crew execution finished.")
    print("---------------------------------")
    print("Final User-Facing Response:")
    print(final_result)