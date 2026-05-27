import os
import logging
import requests
from typing import Any, List, Optional
from dotenv import load_dotenv
from crewai import Agent, Task, LLM
from hospital_tools import PatientContextTool, MedicalRAGTool, SummaryContextTool, WorkflowActionTool, MeditronMedicalTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from pydantic import Field
from meditron_client import MeditronClient

load_dotenv()

# --- LOGGER SETUP ---
logger = logging.getLogger(__name__)

# --- SILENCE LOGGING ---
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["LITELLM_LOG"] = "ERROR"
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

# --- Custom LLM Wrapper for Meditron (SageMaker) ---

class MeditronLLMWrapper(BaseChatModel):
    """Wraps our SageMaker Meditron client as a ChatModel for CrewAI."""
    
    client: MeditronClient = Field(default_factory=MeditronClient)
    model_name: str = "meditron-v1"

    @property
    def _llm_type(self) -> str:
        return "meditron-chat"

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> ChatResult:
        # Construct a clean prompt for Meditron
        prompt = ""
        # We find the last human message and relevant context if present
        for m in messages:
            if m.type == "human":
                prompt = m.content
                break
        
        if not prompt:
            prompt = messages[-1].content
            
        logger.info(f"--- CALLING MEDITRON (SageMaker) with prompt length: {len(prompt)} ---")
        
        # Use direct client call
        response_text = self.client.generate_response(prompt)
        
        # SAFETY: If the model echoed the prompt, try to strip it
        clean_response = response_text
        if prompt in response_text:
            clean_response = response_text.split(prompt)[-1].strip()
        
        # Remove common "AI:" or "Response:" prefixes if Meditron adds them
        prefixes = ["Expert Medical Response:", "Response:", "AI:", "Answer:"]
        for pref in prefixes:
            if clean_response.startswith(pref):
                clean_response = clean_response[len(pref):].strip()

        logger.info(f"--- MEDITRON RESPONSE RECEIVED (length: {len(clean_response)}) ---")
        
        message = AIMessage(content=clean_response)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

# --- LLM Configurations ---

# Load API keys from environment variables
load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-caremate-dummy")
os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY")

# 1. Meditron (SageMaker) for Medical Reasoning
meditron_llm = MeditronLLMWrapper()

# 2. Nemotron (OpenRouter) for Orchestration
orchestrator_llm = LLM(
    model="openrouter/nvidia/nemotron-3-super-120b-a12b:free", 
    api_key=os.environ["OPENROUTER_API_KEY"]
)

class CareMateAgents:
    def patient_agent(self):
        """
        Powered directly by Meditron via SageMaker. 
        Prompts are stripped of language instructions to focus on medical context.
        """
        return Agent(
            role='Medical Interaction Specialist',
            goal='Provide expert medical responses based ONLY on provided patient records.',
            backstory="""You are an expert medical assistant powered by Meditron. 
            You have access to real hospital data and PDF reports.
            Your job is to provide clinical answers based on those records. 
            Provide ONLY the medical response text. Do NOT include tool logs or reasoning.""",
            tools=[PatientContextTool(), MedicalRAGTool(), SummaryContextTool()],
            llm=meditron_llm, 
            verbose=False,
            allow_delegation=False
        )

    def central_agent(self):
        """
        Powered by Nemotron. Handles hospital logistics.
        """
        return Agent(
            role='Clinical Workflow Orchestrator',
            goal='Execute hospital protocols precisely based on detected intent.',
            backstory="""You are an ultra-fast logistics brain. You do not chat. 
            You receive intents and trigger hospital tools instantly.
            Provide a brief, professional confirmation of the action.""",
            tools=[WorkflowActionTool(), PatientContextTool()],
            llm=orchestrator_llm,
            verbose=False,
            allow_delegation=False
        )

class CareMateTasks:
    def respond_to_patient(self, agent, patient_id, user_input):
        return Task(
            description=f"""
            1. Retrieve the medical profile and RAG context for patient: {patient_id}.
            2. Analyze the findings to answer: '{user_input}'.
            3. Provide a clear, medical response based on that data.
            """,
            expected_output="A professional medical response based on the patient's records.",
            agent=agent
        )

    def execute_workflow(self, agent, patient_id, user_input, classified_intent):
        return Task(
            description=f"""
            1. Use the Workflow Action Tool to execute the {classified_intent} protocol.
            2. Provide the original text: '{user_input}' as context.
            3. Confirm that the record has been created.
            """,
            expected_output="A brief confirmation that the task has been logged.",
            agent=agent
        )
