from caremate_v4.tools.doctor_tool import DoctorVoiceInteractionTool

tool = DoctorVoiceInteractionTool()

result = tool.run(
    patient_id="P001",
    bed_number="B12",
    medical_query="I am feeling severe chest pain. What should I do?"
)

print(result)