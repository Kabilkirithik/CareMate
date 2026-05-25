from caremate_v4.tools.summary_tool import SummaryGeneratorTool

tool = SummaryGeneratorTool()


result = tool.run(
    patient_id="P001",
    visit_id="V001"
)

print("\n--- VISIT SUMMARY ---")
print(result)