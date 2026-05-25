from caremate_v4.tools.ocr_tool import OCRSubmissionTool

tool = OCRSubmissionTool()


result = tool.run(
    patient_id="P001",
    file_path="sample_report.pdf",   # can also be sample_report.jpg
    document_type="lab_report"
)

print("\n--- OCR SUBMISSION RESULT ---")
print(result)