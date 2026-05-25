from caremate_v4.tools.nutritionist_tool import NutritionistApprovalTool

tool = NutritionistApprovalTool()

result = tool.run(
    patient_id="P001",
    bed_number="B12",
    food_request="Can I have fruit juice?"
)

print(result)