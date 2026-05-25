from pymongo import MongoClient, DESCENDING
from datetime import datetime, timezone
from bson import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime

# -------------------------------------------------
# 🔗 MongoDB Connection (Single Shared Instance)
# -------------------------------------------------
load_dotenv()

MONGO_URL = os.getenv("MONGO_URI")

if not MONGO_URL:
    raise ValueError("❌ MONGO_URI not found in environment variables")

client = MongoClient(MONGO_URL)
db = client["caremate_db"]

print("✅ CareMate DB Service Connected")


# =================================================
# 🔧 INTERNAL SERIALIZATION HELPERS
# =================================================

def _serialize_document(doc):
    """Convert MongoDB ObjectId to string and ensure safe JSON output."""
    if not doc:
        return None

    doc = dict(doc)

    if "_id" in doc:
        doc["_id"] = str(doc["_id"])

    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)

    return doc


def _serialize_list(docs):
    return [_serialize_document(doc) for doc in docs]


# =================================================
# 👤 PATIENT FUNCTIONS
# =================================================

def get_patient(patient_id: str):
    doc = db.patients.find_one({"patient_id": patient_id}, {"_id": 0})
    return _serialize_document(doc)


# =================================================
# 🏥 VISIT FUNCTIONS
# =================================================

def get_active_visit(patient_id: str):
    doc = db.visits.find_one(
        {"patient_id": patient_id, "status": "Admitted"},
        {"_id": 0}
    )
    return _serialize_document(doc)


def update_bed(visit_id: str, room: str, bed: str):
    db.visits.update_one(
        {"visit_id": visit_id},
        {"$set": {"current_room": room, "current_bed": bed}}
    )


# =================================================
# 📋 REQUEST FUNCTIONS
# =================================================

def create_request(visit_id: str, request_type: str, metadata=None):
    metadata = metadata or {}

    request = {
        "request_id": f"REQ_{datetime.now(timezone.utc).timestamp()}",
        "visit_id": visit_id,
        "type": request_type,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "metadata": metadata
    }

    db.requests.insert_one(request)
    return _serialize_document(request)


def update_request_status(request_id: str, status: str):
    db.requests.update_one(
        {"request_id": request_id},
        {"$set": {
            "status": status,
            "updated_at": datetime.now(timezone.utc)
        }}
    )


# =================================================
# 🕒 EVENT LOGGING FUNCTIONS
# =================================================

def log_event(
    visit_id: str,
    patient_id: str,
    event_type: str,
    staff_id=None,
    room=None,
    bed=None,
    metadata=None
):
    metadata = metadata or {}

    event = {
        "visit_id": visit_id,
        "patient_id": patient_id,
        "event_type": event_type,
        "staff_id": staff_id,
        "room": room,
        "bed": bed,
        "metadata": metadata,
        "timestamp": datetime.now(timezone.utc)
    }

    db.visit_events.insert_one(event)
    return _serialize_document(event)


def get_visit_timeline(visit_id: str, limit=50):
    docs = list(
        db.visit_events.find({"visit_id": visit_id})
        .sort("timestamp", DESCENDING)
        .limit(limit)
    )
    return _serialize_list(docs)


# =================================================
# 🧠 SUMMARY FUNCTIONS
# =================================================

def add_summary(visit_id: str, summary_type: str, content: str):
    summary = {
        "visit_id": visit_id,
        "summary_type": summary_type,
        "content": content,
        "generated_at": datetime.now(timezone.utc)
    }

    db.summaries.insert_one(summary)
    return _serialize_document(summary)


def get_summaries(visit_id: str):
    docs = list(db.summaries.find({"visit_id": visit_id}, {"_id": 0}))
    return _serialize_list(docs)


# =================================================
# 💬 CHAT LOG FUNCTIONS
# =================================================

def log_chat(visit_id: str, speaker: str, message: str):
    chat = {
        "visit_id": visit_id,
        "speaker": speaker,
        "message": message,
        "timestamp": datetime.now(timezone.utc)
    }

    db.chat_logs.insert_one(chat)
    return _serialize_document(chat)



def _serialize_document(doc):
    if not doc:
        return None

    doc = dict(doc)

    if "_id" in doc:
        doc["_id"] = str(doc["_id"])

    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
        elif isinstance(value, ObjectId):
            doc[key] = str(value)

    return doc