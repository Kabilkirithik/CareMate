from crewai import Task
from caremate_v4.agents.central_agent import central_agent


workflow_management_task = Task(
    description="""
    Process incoming patient requests.
    Categorize the request and route to the correct hospital service.
    Update workflow status and log the event.
    """,

    agent=central_agent,

    expected_output="""
    Staff task created and workflow updated.
    """
)