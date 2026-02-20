from pymongo import MongoClient
import os
from pprint import pprint

# --------------------------------------------------
# MongoDB Atlas Connection
# --------------------------------------------------
MONGO_URI="mongodb+srv://nivedithathangavel7:pgs123mongo@cluster0.uotjlvz.mongodb.net/?appName=Cluster0"
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable not set")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
client.admin.command("ping")
print("✅ Connected to MongoDB Atlas")

db = client["hospital_db"]
patients_collection = db["patients"]

# --------------------------------------------------
# (Optional but Recommended) Clear existing data
# --------------------------------------------------
patients_collection.delete_many({})
print("🧹 Cleared existing patient records")

# --------------------------------------------------
# Patient Data (10 Records)
# --------------------------------------------------
patients = [
    {
        "hospital_id": "HSP1001",
        "room_number": "Ward-3",
        "bed_number": "Bed-12",
        "name": "Anita Sharma",
        "age": 62,
        "department": "Orthopedics",
        "known_conditions": ["Hypertension"],
        "dietary_restrictions": ["Low sodium"],
        "mobility_limitations": ["Requires walker"]
    },
    {
        "hospital_id": "HSP1002",
        "room_number": "ICU-1",
        "bed_number": "Bed-2",
        "name": "Ramesh Kumar",
        "age": 48,
        "department": "Neurology",
        "known_conditions": ["Seizure history"],
        "dietary_restrictions": ["Soft diet"],
        "mobility_limitations": ["Bed rest"]
    },
    {
        "hospital_id": "HSP1003",
        "room_number": "Ward-1",
        "bed_number": "Bed-5",
        "name": "Sita Devi",
        "age": 70,
        "department": "Cardiology",
        "known_conditions": ["Diabetes"],
        "dietary_restrictions": ["Low sugar"],
        "mobility_limitations": ["Limited mobility"]
    },
    {
        "hospital_id": "HSP1004",
        "room_number": "Ward-2",
        "bed_number": "Bed-8",
        "name": "Arjun Patel",
        "age": 35,
        "department": "General Surgery",
        "known_conditions": [],
        "dietary_restrictions": ["High protein"],
        "mobility_limitations": ["Post surgery"]
    },
    {
        "hospital_id": "HSP1005",
        "room_number": "Ward-4",
        "bed_number": "Bed-1",
        "name": "Meena Iyer",
        "age": 55,
        "department": "Endocrinology",
        "known_conditions": ["Hypothyroidism"],
        "dietary_restrictions": ["Low fat"],
        "mobility_limitations": []
    },
    {
        "hospital_id": "HSP1006",
        "room_number": "Ward-5",
        "bed_number": "Bed-9",
        "name": "Rahul Verma",
        "age": 28,
        "department": "Pulmonology",
        "known_conditions": ["Asthma"],
        "dietary_restrictions": [],
        "mobility_limitations": []
    },
    {
        "hospital_id": "HSP1007",
        "room_number": "Ward-6",
        "bed_number": "Bed-3",
        "name": "Kavita Joshi",
        "age": 60,
        "department": "Nephrology",
        "known_conditions": ["Hypertension"],
        "dietary_restrictions": ["Low potassium"],
        "mobility_limitations": ["Limited mobility"]
    },
    {
        "hospital_id": "HSP1008",
        "room_number": "Ward-7",
        "bed_number": "Bed-6",
        "name": "Suresh Naidu",
        "age": 45,
        "department": "Gastroenterology",
        "known_conditions": ["Acid reflux"],
        "dietary_restrictions": ["Avoid spicy food"],
        "mobility_limitations": []
    },
    {
        "hospital_id": "HSP1009",
        "room_number": "Ward-8",
        "bed_number": "Bed-4",
        "name": "Pooja Malhotra",
        "age": 32,
        "department": "Obstetrics",
        "known_conditions": ["Pregnancy"],
        "dietary_restrictions": ["Iron rich diet"],
        "mobility_limitations": ["Limited mobility"]
    },
    {
        "hospital_id": "HSP1010",
        "room_number": "Ward-9",
        "bed_number": "Bed-7",
        "name": "Vijay Rao",
        "age": 68,
        "department": "Oncology",
        "known_conditions": ["Hypertension"],
        "dietary_restrictions": ["High calorie"],
        "mobility_limitations": ["Wheelchair"]
    }
]

# --------------------------------------------------
# Insert into MongoDB
# --------------------------------------------------
result = patients_collection.insert_many(patients)
print(f"✅ Inserted {len(result.inserted_ids)} patient records")

# --------------------------------------------------
# Verify Insert
# --------------------------------------------------
print("\n🔍 Patients in database:")
for patient in patients_collection.find({}, {"_id": 0}):
    pprint(patient)

print("\n🎉 Patient data successfully seeded into MongoDB Atlas")
