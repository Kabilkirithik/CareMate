from caremate_v4.tools.nurse_tool import NurseDashboardTool

tool = NurseDashboardTool()

result = tool.run(
    patient_id="P001",
    bed_number="B12",
    request_text="I need help adjusting my bed",
    priority="medium"
)

print(result)