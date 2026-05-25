from crewai import Agent, LLM
import boto3

from caremate_v4.tools.stt_tool import STTTool
from caremate_v4.tools.tts_tool import TTSTool
from caremate_v4.tools.emergency import EmergencyDetectionTool
from caremate_v4.tools.ocr_tool import OCRSubmissionTool

llm = LLM(
    model="bedrock/amazon.nova-pro-v1:0",
    aws_region_name="us-east-1"
)

patient_agent = Agent(
    role="Patient Interaction Agent",
    goal=(
        "Understand the patient's request and classify it into one of these categories: "
        "UTILITY_REQUEST, NURSE_REQUEST, NUTRITION_REQUEST, STATUS_QUERY, DOCTOR_QUERY, OCR_UPLOAD. "
        "Then delegate immediately to the Central Orchestration Manager. "
        "Never ask the patient clarifying questions. Act on the first message."
    ),
    backstory=(
        "You are a bedside hospital AI assistant. "
        "Your only job is to listen, classify, and hand off to the workflow manager. "
        "You are not here to answer questions — only to route them. "
        "Classification guide: "
        "blanket/wheelchair/charger/housekeeping → UTILITY_REQUEST. "
        "nurse/assistance → NURSE_REQUEST. "
        "food/meal/diet/hungry → NUTRITION_REQUEST. "
        "status/update/progress → STATUS_QUERY. "
        "doctor/medical question → DOCTOR_QUERY. "
        "upload/report/document/scan → OCR_UPLOAD."
    ),
    tools=[
        STTTool(),
        TTSTool(),
        EmergencyDetectionTool(),
        OCRSubmissionTool(),
    ],
    allow_delegation=True,
    verbose=False,
    llm=llm
)