"""
CareMate CrewAI Implementation
Main crew configuration with two agents and sequential task flow
"""

from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, crew, task
from typing import Dict, Any
import json

from .models import PatientAnalysisOutput, OrchestratorOutput
from .tools.patient_intelligence_tools import (
    PatientRecordRetrievalTool,
    ContextSummarizationTool,
    IntentClassificationTool,
    DistressDetectionTool,
    MemoryManagementTool
)
from .tools.orchestrator_tools import (
    PolicyEvaluationTool,
    ResponseGenerationTool,
    NotificationTool,
    ApprovalWorkflowTool,
    AuditLoggingTool
)


@CrewBase
class CareMateC Crew():
    """CareMate Two-Agent Healthcare Assistant Crew"""
    
    # ========================================================================
    # Agent Definitions
    # ========================================================================
    
    @agent
    def patient_intelligence_agent(self) -> Agent:
        """
        Patient Intelligence Agent
        Analyzes patient context, intent, and urgency without making decisions
        """
        return Agent(
            role="Patient Context and Intent Analyzer",
            goal=(
                "Accurately understand patient needs, context, and urgency "
                "without making medical decisions"
            ),
            backstory=(
                "You are a specialized healthcare AI assistant focused on understanding patients. "
                "You analyze what patients say, retrieve their medical context, and classify their "
                "requests - but you NEVER make medical decisions or provide medical advice. "
                "Your job is to prepare complete, accurate information for the decision-making agent."
            ),
            tools=[
                PatientRecordRetrievalTool(),
                ContextSummarizationTool(),
                IntentClassificationTool(),
                DistressDetectionTool(),
                MemoryManagementTool()
            ],
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True
        )
    
    @agent
    def orchestrator_policy_agent(self) -> Agent:
        """
        Central Orchestrator & Policy Agent
        Makes decisions, enforces policies, generates responses
        """
        return Agent(
            role="Healthcare Policy Enforcement and Orchestration Coordinator",
            goal=(
                "Ensure all patient interactions comply with hospital policies, "
                "route medical requests to staff, and provide safe non-medical assistance"
            ),
            backstory=(
                "You are the central decision-maker for the CareMate system. You enforce strict "
                "hospital safety policies: NO medical advice, ALL medication requests require "
                "nurse approval, ALL emergencies escalate immediately. You generate safe, helpful "
                "responses for non-medical requests and ensure proper staff notification for "
                "medical needs. Patient safety is your absolute priority."
            ),
            tools=[
                PolicyEvaluationTool(),
                ResponseGenerationTool(),
                NotificationTool(),
                ApprovalWorkflowTool(),
                AuditLoggingTool()
            ],
            verbose=True,
            allow_delegation=False,
            max_iter=5,
            memory=True
        )
    
    # ========================================================================
    # Task Definitions
    # ========================================================================
    
    @task
    def patient_analysis_task(self) -> Task:
        """
        Task 1: Analyze patient query and context
        Executed by Patient Intelligence Agent
        """
        return Task(
            description=(
                "Analyze the patient query: {query}\n\n"
                "Steps:\n"
                "1. Retrieve patient context using hospital_id: {hospital_id} and bed: {bed_number}\n"
                "2. Classify the intent (MEDICAL/NON_MEDICAL/EMERGENCY)\n"
                "3. Detect any distress signals or urgent keywords\n"
                "4. Summarize relevant patient history\n"
                "5. Check recent interaction memory\n\n"
                "Return structured output with:\n"
                "- patient_context: Summary of relevant patient info\n"
                "- intent_category: One of [MEDICAL, NON_MEDICAL, EMERGENCY]\n"
                "- urgency_level: One of [LOW, MEDIUM, HIGH, CRITICAL]\n"
                "- distress_flags: List of detected concerns\n"
                "- conversation_history: Recent relevant interactions"
            ),
            expected_output=(
                "JSON object containing patient_context, intent_category, urgency_level, "
                "distress_flags, and conversation_history"
            ),
            agent=self.patient_intelligence_agent(),
            output_json=PatientAnalysisOutput
        )
    
    @task
    def policy_evaluation_and_response_task(self) -> Task:
        """
        Task 2: Evaluate policies and generate response
        Executed by Orchestrator Agent
        """
        return Task(
            description=(
                "Based on patient analysis from previous task, determine the appropriate action.\n\n"
                "Policy Rules:\n"
                "- EMERGENCY: Immediately notify emergency staff, skip approval\n"
                "- MEDICAL requests: Route to nurse/doctor dashboard for approval\n"
                "- Medication requests: ALWAYS require nurse approval\n"
                "- NON_MEDICAL: Generate direct response if safe\n"
                "- High distress: Escalate even if non-medical\n\n"
                "Original Query: {query}\n\n"
                "Steps:\n"
                "1. Apply policy evaluation rules\n"
                "2. Determine response path\n"
                "3. Generate appropriate response OR create approval request\n"
                "4. Send notifications if needed\n"
                "5. Log all decisions to audit trail\n\n"
                "Output:\n"
                "- response_text: Patient-facing message\n"
                "- action_taken: Description of system action\n"
                "- requires_approval: Boolean\n"
                "- staff_notified: List of staff IDs notified\n"
                "- audit_log_id: Reference to log entry"
            ),
            expected_output=(
                "JSON object with response_text, action_taken, requires_approval, "
                "staff_notified, and audit_log_id"
            ),
            agent=self.orchestrator_policy_agent(),
            output_json=OrchestratorOutput,
            context=[self.patient_analysis_task()]
        )
    
    # ========================================================================
    # Crew Assembly
    # ========================================================================
    
    @crew
    def crew(self) -> Crew:
        """
        Assemble the CareMate crew with sequential process
        """
        return Crew(
            agents=[
                self.patient_intelligence_agent(),
                self.orchestrator_policy_agent()
            ],
            tasks=[
                self.patient_analysis_task(),
                self.policy_evaluation_and_response_task()
            ],
            process=Process.sequential,  # Tasks execute in order
            verbose=True,
            memory=True,  # Enable crew-level memory
            cache=True  # Cache results for efficiency
        )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def process_patient_query(
        self,
        query: str,
        hospital_id: str,
        bed_number: str
    ) -> Dict[str, Any]:
        """
        Main entry point for processing patient queries
        
        Args:
            query: Patient's question or request
            hospital_id: Patient's hospital ID
            bed_number: Patient's bed number
            
        Returns:
            Complete response with all agent outputs
        """
        # Prepare inputs for the crew
        inputs = {
            'query': query,
            'hospital_id': hospital_id,
            'bed_number': bed_number
        }
        
        # Execute the crew
        result = self.crew().kickoff(inputs=inputs)
        
        return result
    
    def process_with_translation(
        self,
        voice_input: str,
        hospital_id: str,
        bed_number: str,
        patient_language: str = "en"
    ) -> Dict[str, Any]:
        """
        Full pipeline with speech-to-text and translation
        
        This would integrate with:
        - Azure Speech Services (or similar) for STT
        - Azure Translator (or similar) for translation
        - CrewAI processing
        - Translation back to patient language
        - TTS for voice output
        
        Args:
            voice_input: Raw audio input (or already transcribed text)
            hospital_id: Patient's hospital ID
            bed_number: Patient's bed number
            patient_language: Patient's preferred language code
            
        Returns:
            Response with translated text ready for TTS
        """
        # TODO: Implement speech-to-text
        # transcribed_text = speech_to_text(voice_input)
        transcribed_text = voice_input  # Placeholder
        
        # TODO: Implement translation to English if needed
        # if patient_language != "en":
        #     english_query = translate(transcribed_text, patient_language, "en")
        # else:
        #     english_query = transcribed_text
        english_query = transcribed_text  # Placeholder
        
        # Process through CrewAI
        crew_result = self.process_patient_query(
            query=english_query,
            hospital_id=hospital_id,
            bed_number=bed_number
        )
        
        # Extract response text
        response_text = crew_result.get('response_text', 'I apologize, but I encountered an error.')
        
        # TODO: Translate response back to patient language
        # if patient_language != "en":
        #     translated_response = translate(response_text, "en", patient_language)
        # else:
        #     translated_response = response_text
        translated_response = response_text  # Placeholder
        
        # TODO: Convert to speech
        # audio_output = text_to_speech(translated_response, patient_language)
        
        return {
            'original_query': transcribed_text,
            'english_query': english_query,
            'response_english': response_text,
            'response_translated': translated_response,
            'crew_output': crew_result
        }


# ============================================================================
# Usage Example
# ============================================================================

def main():
    """
    Example usage of CareMate Crew
    """
    # Initialize the crew
    caremate = CareMateCrew()
    
    # Example patient query
    result = caremate.process_patient_query(
        query="I'm having severe chest pain and trouble breathing",
        hospital_id="PT-12345",
        bed_number="ICU-201"
    )
    
    print("\n" + "="*80)
    print("CAREMATE RESPONSE")
    print("="*80)
    print(json.dumps(result, indent=2))
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
