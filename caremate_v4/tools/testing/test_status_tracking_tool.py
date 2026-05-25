from caremate_v4.tools.status_tracking_tool import StatusTrackingTool

tool = StatusTrackingTool()

# -----------------------------
# Test 1: Fetch Status
# -----------------------------
result = tool.run(
    request_id="REQ123",
    action="get_status"
)

print("\n--- REQUEST STATUS ---")
print(result)


# -----------------------------
# Test 2: Update Status
# -----------------------------
result = tool.run(
    request_id="REQ123",
    action="update_status",
    new_status="IN_PROGRESS"
)

print("\n--- STATUS UPDATED ---")
print(result)


# from caremate_v4.mongodb.db_service import db
# from datetime import datetime

# db.requests.insert_one({
#     "request_id": "REQ123",
#     "patient_id": "P001",
#     "type": "utility",
#     "service": "blanket",
#     "status": "REQUESTED",
#     "created_at": datetime.utcnow(),
#     "updated_at": datetime.utcnow()
# })

# print("Test request inserted.")