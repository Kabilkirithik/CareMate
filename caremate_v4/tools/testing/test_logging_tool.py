from caremate_v4.tools.logging_tool import LoggingTool

tool = LoggingTool()


# -----------------------------
# Test Event Logging
# -----------------------------
result = tool.run(
    event_type="utility_request",
    patient_id="P001",
    request_id="REQ123",
    actor="patient",
    description="Patient requested a blanket",
    metadata={"service": "blanket"}
)

print("\n--- LOGGING RESULT ---")
print(result)