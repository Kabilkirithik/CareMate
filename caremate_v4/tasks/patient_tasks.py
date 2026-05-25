from crewai import Task
from caremate_v4.agents.patient_agent import patient_agent


patient_interaction_task = Task(
    description="""
    Understand the patient request.
    If emergency detected, trigger emergency response.
    Otherwise route the request to the Central Orchestration Agent.
    """,

    agent=patient_agent,

    expected_output="""
    Structured patient request or emergency alert.
    """
)