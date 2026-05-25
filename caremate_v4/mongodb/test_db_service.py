from db_service import (
    get_patient,
    get_active_visit,
    log_event,
    create_request,
    get_visit_timeline,
    add_summary,
    log_chat
)

print("\n🚀 Starting DB Service Tests...\n")

# --------------------------------------------------
# 1️⃣ Test Patient Fetch
# --------------------------------------------------
patient = get_patient("P001")
print("Patient Fetch:", patient)

# --------------------------------------------------
# 2️⃣ Test Active Visit Fetch
# --------------------------------------------------
visit = get_active_visit("P001")
print("\nActive Visit:", visit)

if not visit:
    print("❌ No active visit found. Make sure seed data is inserted.")
    exit()

visit_id = visit["visit_id"]

# --------------------------------------------------
# 3️⃣ Test Event Logging
# --------------------------------------------------
event = log_event(
    visit_id=visit_id,
    patient_id="P001",
    event_type="SYSTEM_ACTION",
    staff_id="S001",
    room=visit["current_room"],
    bed=visit["current_bed"],
    metadata={"test": True}
)

print("\nEvent Logged:", event)

# --------------------------------------------------
# 4️⃣ Test Request Creation
# --------------------------------------------------
request = create_request(
    visit_id=visit_id,
    request_type="NURSE_REQUEST",
    metadata={"reason": "Testing service layer"}
)

print("\nRequest Created:", request)

# --------------------------------------------------
# 5️⃣ Test Timeline Fetch
# --------------------------------------------------
timeline = get_visit_timeline(visit_id)

print("\nTimeline Events (Latest):")
for t in timeline[:3]:
    print(t)

# --------------------------------------------------
# 6️⃣ Test Summary Insert
# --------------------------------------------------
summary = add_summary(
    visit_id=visit_id,
    summary_type="test_summary",
    content="This is a test summary."
)

print("\nSummary Added:", summary)

# --------------------------------------------------
# 7️⃣ Test Chat Log
# --------------------------------------------------
log_chat(
    visit_id=visit_id,
    speaker="patient",
    message="Testing chat log"
)

print("\nChat Log Inserted")

print("\n🎉 DB Service Test Completed Successfully!")