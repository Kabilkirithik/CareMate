from crewai import Crew

from caremate_v4.agents.patient_agent import patient_agent
from caremate_v4.agents.central_agent import central_agent

from caremate_v4.tasks.patient_tasks import patient_interaction_task
from caremate_v4.tasks.manager_tasks import workflow_management_task


caremate_crew = Crew(

    agents=[
        patient_agent,
        central_agent
    ],

    tasks=[
        patient_interaction_task,
        workflow_management_task
    ],

    verbose=True
)