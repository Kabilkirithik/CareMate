from pymongo import MongoClient
from datetime import datetime, timedelta
import random

# -------------------------------------------------
# 🔗 MongoDB Connection
# -------------------------------------------------
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URL)
db = client["caremate_db"]

print("✅ Connected to CareMate DB")


# -------------------------------------------------
# 👤 1️⃣ INSERT 50 PATIENTS
# -------------------------------------------------

patients = []

for i in range(1, 51):
    patients.append({
        "patient_id": f"P{i:03}",
        "name": f"Patient_{i}",
        "age": random.randint(20, 80),
        "gender": random.choice(["Male", "Female"]),
        "allergies": [],
        "created_at": datetime.utcnow()
    })

db.patients.insert_many(patients)
print("✅ 50 Patients Inserted")


# -------------------------------------------------
# 👩‍⚕️ 2️⃣ INSERT STAFF (10 DOCTORS + NURSES)
# -------------------------------------------------

staff = []

roles = ["doctor", "nurse"]

for i in range(1, 11):
    role = random.choice(roles)
    staff.append({
        "staff_id": f"S{i:03}",
        "name": f"Staff_{i}",
        "role": role,
        "department": "General Ward",
        "active": True,
        "created_at": datetime.utcnow()
    })

db.staff_users.insert_many(staff)
print("✅ 10 Staff Users Inserted")


# -------------------------------------------------
# 🏢 3️⃣ INSERT ROOMS
# -------------------------------------------------

rooms = []
for i in range(1, 6):
    rooms.append({
        "room_id": f"R10{i}",
        "ward": "General",
        "floor": 1
    })

db.rooms.insert_many(rooms)
print("✅ Rooms Inserted")


# -------------------------------------------------
# 🛏️ 4️⃣ INSERT BEDS + DEVICES
# -------------------------------------------------

beds = []
devices = []

device_counter = 1

for room in rooms:
    for b in range(1, 5):

        device_id = f"ESP32_{device_counter:03}"

        beds.append({
            "bed_id": f"B{device_counter:03}",
            "room_id": room["room_id"],
            "device_id": device_id
        })

        devices.append({
            "device_id": device_id,
            "status": "online",
            "last_seen": datetime.utcnow(),
            "firmware_version": "1.0"
        })

        device_counter += 1

db.beds.insert_many(beds)
db.devices.insert_many(devices)

print("✅ Beds & Devices Inserted")


# -------------------------------------------------
# 🏥 5️⃣ INSERT VISITS FOR EACH PATIENT
# -------------------------------------------------

visits = []

for i in range(1, 51):

    admission_time = datetime.utcnow() - timedelta(days=random.randint(0, 3))

    visits.append({
        "visit_id": f"V{i:03}",
        "patient_id": f"P{i:03}",
        "assigned_doctor": f"S{random.randint(1,5):03}",
        "status": "Admitted",
        "admission_time": admission_time,
        "discharge_time": None,
        "current_room": random.choice(rooms)["room_id"],
        "current_bed": random.choice(beds)["bed_id"]
    })

db.visits.insert_many(visits)

print("✅ Visits Inserted")


# -------------------------------------------------
# 📋 6️⃣ INSERT SAMPLE REQUESTS
# -------------------------------------------------

requests = []

request_types = [
    "NURSE_REQUEST",
    "DOCTOR_QUERY",
    "UTILITY_REQUEST",
    "NUTRITION_REQUEST"
]

for i in range(1, 30):
    requests.append({
        "request_id": f"REQ{i:03}",
        "visit_id": f"V{random.randint(1,50):03}",
        "type": random.choice(request_types),
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "metadata": {}
    })

db.requests.insert_many(requests)

print("✅ Requests Inserted")


# -------------------------------------------------
# 🕒 7️⃣ INSERT VISIT EVENTS (NFC + EMERGENCY)
# -------------------------------------------------

events = []

event_types = [
    "NFC_SCAN",
    "BED_CHANGE",
    "EMERGENCY_TRIGGER",
    "SYSTEM_ACTION"
]

for i in range(1, 80):

    visit_id = f"V{random.randint(1,50):03}"

    events.append({
        "visit_id": visit_id,
        "patient_id": f"P{visit_id[1:]}",
        "event_type": random.choice(event_types),
        "staff_id": f"S{random.randint(1,10):03}",
        "room": random.choice(rooms)["room_id"],
        "bed": random.choice(beds)["bed_id"],
        "metadata": {},
        "timestamp": datetime.utcnow() - timedelta(minutes=random.randint(1,300))
    })

db.visit_events.insert_many(events)

print("✅ Visit Events Inserted")


# -------------------------------------------------
# 🧠 8️⃣ INSERT SUMMARIES
# -------------------------------------------------

summaries = []

for i in range(1, 20):
    summaries.append({
        "visit_id": f"V{random.randint(1,50):03}",
        "summary_type": "doctor_round",
        "content": "Patient stable. Monitoring ongoing.",
        "generated_at": datetime.utcnow()
    })

db.summaries.insert_many(summaries)

print("✅ Summaries Inserted")


# -------------------------------------------------
# 📄 9️⃣ INSERT DOCUMENTS
# -------------------------------------------------

documents = []

for i in range(1, 20):
    documents.append({
        "visit_id": f"V{random.randint(1,50):03}",
        "doc_type": "LabReport",
        "file_url": "https://dummy-url/report.pdf",
        "classification": "Blood Test",
        "ocr_text": "Sample OCR Text",
        "uploaded_at": datetime.utcnow()
    })

db.documents.insert_many(documents)

print("✅ Documents Inserted")


print("\n🎉 CareMate Database Seeded Successfully!")