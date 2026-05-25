from crewai import Agent, LLM
import boto3

from caremate_v4.tools.patient_details_tool import PatientDetailsTool
from caremate_v4.tools.nurse_tool import NurseDashboardTool
from caremate_v4.tools.doctor_tool import DoctorVoiceInteractionTool
from caremate_v4.tools.nutritionist_tool import NutritionistApprovalTool
from caremate_v4.tools.utility_service_tool import UtilityServiceTool
from caremate_v4.tools.status_tracking_tool import StatusTrackingTool
from caremate_v4.tools.logging_tool import LoggingTool
from caremate_v4.tools.summary_tool import SummaryGeneratorTool

llm = LLM(
    model="bedrock/amazon.nova-pro-v1:0",
    aws_region_name="us-east-1"
)

tools = [
    PatientDetailsTool(),
    NurseDashboardTool(),
    DoctorVoiceInteractionTool(),
    NutritionistApprovalTool(),
    UtilityServiceTool(),
    StatusTrackingTool(),
    LoggingTool(),
    SummaryGeneratorTool()
]

central_agent = Agent(
    role="Central Orchestration Manager",
    goal=(
        "You MUST use tools to handle every request. Never reply without calling a tool first. "
        "Step 1: Call PatientDetailsTool to fetch patient context. "
        "Step 2: Route to the correct tool based on request type — "
        "UTILITY_REQUEST → UtilityServiceTool, "
        "NURSE_REQUEST → NurseDashboardTool, "
        "NUTRITION_REQUEST → NutritionistApprovalTool, "
        "STATUS_QUERY → StatusTrackingTool, "
        "DOCTOR_QUERY → DoctorVoiceInteractionTool, "
        "OCR_UPLOAD → OCRSubmissionTool. "
        "Step 3: Always call LoggingTool after every action."
    ),
    backstory=(
        "You are a hospital workflow orchestrator. "
        "You ensure every patient request reaches the right department and is logged for compliance. "
        "You never guess or reply from memory — you always use the available tools."
    ),
    tools=tools,
    allow_delegation=False,
    verbose=False,
    llm=llm
)