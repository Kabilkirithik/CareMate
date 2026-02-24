from caremate import PatientRecordRetrievalTool

tool = PatientRecordRetrievalTool()

result = tool.run(
    hospital_id="HSP1001",
    room_number="Ward-3",
    bed_number="Bed-12"
)

print(result)
