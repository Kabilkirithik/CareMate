import os
import uuid
import random
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from pymongo import MongoClient, UpdateOne, InsertOne, ASCENDING, DESCENDING
from pymongo.errors import AutoReconnect, BulkWriteError
from faker import Faker
from fpdf import FPDF
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load Environment Variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "caremate_db"

def retry_mongodb(func):
    """Decorator to retry MongoDB operations on connection failure."""
    def wrapper(*args, **kwargs):
        for i in range(5):  # Retry up to 5 times
            try:
                return func(*args, **kwargs)
            except (AutoReconnect, BulkWriteError) as e:
                wait_time = (i + 1) * 2
                logger.warning(f"Connection issue: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        return func(*args, **kwargs)
    return wrapper

# Dataset Scale Constants
SCALE = {
    "patients": 200,
    "visits": 1000,
    "requests": 20000,
    "visit_events": 100000,
    "documents": 5000,
    "summaries": 1000,
    "staff_users": 100,
    "rooms": 50,
    "beds": 100,
    "devices": 100
}

# Configuration & Categories
ROOM_TYPES = ["ICU", "GENERAL", "PRIVATE", "SEMI_PRIVATE"]
WARDS = ["Cardiology", "Neurology", "Orthopedics", "Pediatrics", "Emergency", "Oncology"]
STAFF_ROLES = ["doctor", "nurse", "nutritionist", "facility_staff"]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
GENDERS = ["Male", "Female", "Other"]
VISIT_STATUSES = ["ACTIVE", "DISCHARGED"]
REQUEST_TYPES = ["NURSE", "DOCTOR", "NUTRITION", "UTILITY", "STATUS"]
REQUEST_STATUSES = ["REQUESTED", "ASSIGNED", "IN_PROGRESS", "COMPLETED", "ESCALATED", "CANCELLED"]
PRIORITIES = ["LOW", "MEDIUM", "HIGH", "URGENT"]

UTILITY_CATEGORIES = ["blanket", "wheelchair", "charger", "housekeeping"]
NUTRITION_CATEGORIES = ["food_request", "beverage_request", "special_meal"]

DOC_TYPES = ["lab_report", "prescription", "discharge_summary", "radiology_report"]
UPLOAD_SOURCES = ["scanner", "mobile_upload", "nurse_station"]

EVENT_TYPES = [
    "request_created", "request_assigned", "request_completed", 
    "emergency_alert", "doctor_response", "nutrition_approval", 
    "utility_delivered", "ocr_processed", "summary_generated"
]

# Multilingual / Realistic Request Texts
REQUEST_TEMPLATES = [
    "I need a {item} please.",
    "Can someone bring me a {item}?",
    "मुझे {item} चाहिए।",  # Hindi
    "தயவுசெய்து எனக்கு {item} கொண்டு வாருங்கள்.", # Tamil
    "Please send {item} to my room.",
    "I am feeling uncomfortable, can a {role} check on me?",
    "What is the status of my {report}?",
    "When will the {role} visit?"
]

# Global Faker instances
fake = Faker(['en_IN', 'hi_IN'])
fake_en = Faker('en_IN')

class HospitalDataGenerator:
    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.start_date = datetime.now() - timedelta(days=365)
        
        # ID caches for relational consistency
        self.patient_ids = []
        self.visit_ids = []
        self.room_ids = []
        self.bed_ids = []
        self.doctor_ids = []
        self.nurse_ids = []
        self.nutritionist_ids = []
        self.staff_ids = []
        self.request_ids = []

    def clear_database(self):
        logger.info(f"Clearing existing collections in {self.db.name}...")
        collections = [
            "patients", "visits", "requests", "visit_events", 
            "documents", "summaries", "staff_users", "rooms", 
            "beds", "devices"
        ]
        for coll in collections:
            self.db[coll].drop()
        logger.info("Database cleared.")

    def create_indexes(self):
        logger.info("Creating indexes...")
        self.db.patients.create_index([("patient_id", ASCENDING)], unique=True)
        self.db.visits.create_index([("visit_id", ASCENDING)], unique=True)
        self.db.visits.create_index([("patient_id", ASCENDING)])
        self.db.requests.create_index([("request_id", ASCENDING)], unique=True)
        self.db.requests.create_index([("visit_id", ASCENDING)])
        self.db.visit_events.create_index([("visit_id", ASCENDING)])
        self.db.visit_events.create_index([("timestamp", DESCENDING)])
        self.db.documents.create_index([("visit_id", ASCENDING)])
        self.db.summaries.create_index([("visit_id", ASCENDING)])
        self.db.staff_users.create_index([("staff_id", ASCENDING)], unique=True)
        self.db.rooms.create_index([("room_id", ASCENDING)], unique=True)
        self.db.beds.create_index([("bed_id", ASCENDING)], unique=True)
        self.db.devices.create_index([("device_id", ASCENDING)], unique=True)
        logger.info("Indexes created.")

    @retry_mongodb
    def generate_staff(self):
        logger.info(f"Generating {SCALE['staff_users']} staff users...")
        batch = []
        for _ in range(SCALE['staff_users']):
            role = random.choice(STAFF_ROLES)
            staff_id = str(uuid.uuid4())
            user = {
                "staff_id": staff_id,
                "name": fake.name(),
                "role": role,
                "department": random.choice(WARDS),
                "phone": fake.phone_number(),
                "shift": random.choice(["Day", "Night", "Evening"]),
                "availability_status": random.choice(["AVAILABLE", "BUSY", "ON_BREAK"])
            }
            batch.append(user)
            self.staff_ids.append(staff_id)
            if role == "doctor": self.doctor_ids.append(staff_id)
            elif role == "nurse": self.nurse_ids.append(staff_id)
            elif role == "nutritionist": self.nutritionist_ids.append(staff_id)

        self.db.staff_users.insert_many(batch)
        logger.info("Staff users generated.")

    @retry_mongodb
    def generate_rooms_and_beds(self):
        logger.info(f"Generating rooms, beds, and devices...")
        rooms_batch = []
        beds_batch = []
        devices_batch = []
        
        for i in range(SCALE['rooms']):
            room_id = f"R-{100 + i}"
            rooms_batch.append({
                "room_id": room_id,
                "ward": random.choice(WARDS),
                "floor": random.randint(1, 5),
                "room_type": random.choice(ROOM_TYPES),
                "status": "OPERATIONAL"
            })
            self.room_ids.append(room_id)

        # Beds (scaled to match scale requirement)
        for i in range(SCALE['beds']):
            bed_id = f"B-{1000 + i}"
            room_id = random.choice(self.room_ids)
            beds_batch.append({
                "bed_id": bed_id,
                "room_id": room_id,
                "occupancy_status": "VACANT",
                "assigned_patient": None
            })
            self.bed_ids.append(bed_id)
            
            # Devices per bed
            devices_batch.append({
                "device_id": f"DEV-{5000 + i}",
                "bed_id": bed_id,
                "device_status": "ONLINE",
                "firmware_version": f"v{random.randint(1,3)}.{random.randint(0,9)}",
                "last_active": datetime.now()
            })

        self.db.rooms.insert_many(rooms_batch)
        self.db.beds.insert_many(beds_batch)
        self.db.devices.insert_many(devices_batch)
        logger.info("Rooms, beds, and devices generated.")

    @retry_mongodb
    def generate_patients(self):
        logger.info(f"Generating {SCALE['patients']} patients...")
        batch = []
        for _ in range(SCALE['patients']):
            p_id = str(uuid.uuid4())
            patient = {
                "patient_id": p_id,
                "name": fake.name(),
                "age": random.randint(0, 95),
                "gender": random.choice(GENDERS),
                "blood_group": random.choice(BLOOD_GROUPS),
                "phone": fake.phone_number(),
                "address": fake.address().replace('\n', ', '),
                "allergies": random.sample(["Peanuts", "Penicillin", "Dust", "Latex"], random.randint(0, 2)),
                "chronic_conditions": random.sample(["Diabetes", "Hypertension", "Asthma", "Heart Disease"], random.randint(0, 1)),
                "emergency_contact": {
                    "name": fake.name(),
                    "relation": random.choice(["Spouse", "Parent", "Child", "Sibling"]),
                    "phone": fake.phone_number()
                },
                "created_at": self.start_date + timedelta(days=random.randint(0, 30))
            }
            batch.append(patient)
            self.patient_ids.append(p_id)
            if len(batch) >= 1000:
                self.db.patients.insert_many(batch)
                batch = []
        if batch: self.db.patients.insert_many(batch)
        logger.info("Patients generated.")

    @retry_mongodb
    def generate_visits(self):
        logger.info(f"Generating {SCALE['visits']} visits...")
        batch = []
        visit_data = [] # local cache for next steps
        for _ in range(SCALE['visits']):
            v_id = str(uuid.uuid4())
            p_id = random.choice(self.patient_ids)
            admitted_at = self.start_date + timedelta(days=random.randint(31, 300))
            status = random.choice(VISIT_STATUSES)
            discharged_at = admitted_at + timedelta(days=random.randint(1, 14)) if status == "DISCHARGED" else None
            
            visit = {
                "visit_id": v_id,
                "patient_id": p_id,
                "admission_reason": fake.sentence(),
                "assigned_doctor": random.choice(self.doctor_ids),
                "assigned_nurse": random.choice(self.nurse_ids),
                "room_id": random.choice(self.room_ids),
                "bed_id": random.choice(self.bed_ids),
                "status": status,
                "admitted_at": admitted_at,
                "discharged_at": discharged_at
            }
            batch.append(visit)
            visit_data.append((v_id, p_id, admitted_at, discharged_at))
            self.visit_ids.append(v_id)
            if len(batch) >= 5000:
                self.db.visits.insert_many(batch)
                batch = []
        if batch: self.db.visits.insert_many(batch)
        logger.info("Visits generated.")
        return visit_data

    @retry_mongodb
    def generate_requests(self, visit_data):
        logger.info(f"Generating {SCALE['requests']} requests...")
        batch = []
        req_info = []
        
        for i in range(SCALE['requests']):
            v_id, p_id, admitted_at, discharged_at = random.choice(visit_data)
            req_type = random.choice(REQUEST_TYPES)
            
            # Context-specific category
            category = None
            if req_type == "UTILITY": category = random.choice(UTILITY_CATEGORIES)
            elif req_type == "NUTRITION": category = random.choice(NUTRITION_CATEGORIES)
            
            # Realistic text
            item = category if category else (random.choice(["report", "checkup"]) if req_type == "DOCTOR" else "assistance")
            role = req_type.lower()
            text = random.choice(REQUEST_TEMPLATES).format(item=item, role=role, report="blood report")
            
            created_at = admitted_at + timedelta(hours=random.randint(1, 48))
            # Ensure request is before discharge
            if discharged_at and created_at > discharged_at:
                created_at = admitted_at + (discharged_at - admitted_at) / 2
                
            status = random.choice(REQUEST_STATUSES)
            completed_at = created_at + timedelta(minutes=random.randint(10, 120)) if status == "COMPLETED" else None
            
            req_id = str(uuid.uuid4())
            request = {
                "request_id": req_id,
                "patient_id": p_id,
                "visit_id": v_id,
                "request_type": req_type,
                "category": category,
                "request_text": text,
                "status": status,
                "assigned_to": random.choice(self.staff_ids),
                "priority": random.choice(PRIORITIES),
                "created_at": created_at,
                "updated_at": created_at + timedelta(minutes=5),
                "completed_at": completed_at,
                "sla_deadline": created_at + timedelta(minutes=30)
            }
            batch.append(request)
            req_info.append((req_id, p_id, v_id, created_at, req_type))
            self.request_ids.append(req_id)
            
            if len(batch) >= 5000:
                self.db.requests.insert_many(batch)
                batch = []
                if (i % 25000) == 0:
                    logger.info(f"Progress: {i+1} requests inserted...")

        if batch: self.db.requests.insert_many(batch)
        logger.info("Requests generated.")
        return req_info

    @retry_mongodb
    def generate_events(self, req_info, visit_data):
        logger.info(f"Generating {SCALE['visit_events']} events...")
        batch = []
        
        # 1. Generate events from requests (guarantees some consistency)
        for i, (req_id, p_id, v_id, timestamp, req_type) in enumerate(req_info):
            # Creation event
            batch.append({
                "event_id": str(uuid.uuid4()),
                "patient_id": p_id,
                "visit_id": v_id,
                "event_type": "request_created",
                "actor": "system",
                "description": f"Request {req_type} created",
                "metadata": {"request_id": req_id},
                "timestamp": timestamp
            })
            
            # Completion event (probability-based)
            if random.random() > 0.3:
                batch.append({
                    "event_id": str(uuid.uuid4()),
                    "patient_id": p_id,
                    "visit_id": v_id,
                    "event_type": "request_completed",
                    "actor": "staff",
                    "description": f"Request {req_type} fulfilled",
                    "metadata": {"request_id": req_id},
                    "timestamp": timestamp + timedelta(minutes=random.randint(15, 60))
                })

        # 2. Random filler events to reach 1M
        remaining = SCALE['visit_events'] - len(batch)
        logger.info(f"Adding {remaining} filler events...")
        
        for i in range(remaining):
            v_id, p_id, admitted_at, discharged_at = random.choice(visit_data)
            ts = admitted_at + timedelta(hours=random.randint(1, 24))
            e_type = random.choice(EVENT_TYPES)
            
            batch.append({
                "event_id": str(uuid.uuid4()),
                "patient_id": p_id,
                "visit_id": v_id,
                "event_type": e_type,
                "actor": "system" if "processed" in e_type else "staff",
                "description": f"Activity: {e_type.replace('_', ' ')}",
                "metadata": {},
                "timestamp": ts
            })

            if len(batch) >= 5000:
                self.db.visit_events.insert_many(batch)
                batch = []
                if (i % 100000) == 0:
                    logger.info(f"Progress: {i+1} filler events processed...")

        if batch: self.db.visit_events.insert_many(batch)
        logger.info("Events generated.")

    def _generate_report_pdf(self, doc_id, doc_type, patient_name, patient_id):
        """Generates a professional-looking medical report PDF."""
        reports_dir = os.path.join("Vfinal", "patient_reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        file_name = f"{doc_type}_{doc_id}.pdf"
        file_path = os.path.join(reports_dir, file_name)
        
        pdf = FPDF()
        pdf.add_page()
        
        # Hospital Header
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="CARE MATE MULTISPECIALITY HOSPITAL", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 5, txt="Electronic Health Record System | Managed by CareMate AI", ln=True, align='C')
        pdf.line(10, 30, 200, 30)
        
        # Patient Details Section
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="PATIENT DIAGNOSTIC REPORT", ln=True, align='L')
        pdf.set_font("Arial", size=10)
        pdf.cell(100, 7, txt=f"Patient Name: {patient_name}", ln=False)
        pdf.cell(100, 7, txt=f"Date: {datetime.now().strftime('%d-%m-%Y')}", ln=True)
        pdf.cell(100, 7, txt=f"Patient ID: {patient_id}", ln=False)
        pdf.cell(100, 7, txt=f"Report ID: {doc_id[:8].upper()}", ln=True)
        
        # Report Content
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(200, 8, txt=f"TEST CATEGORY: {doc_type.replace('_', ' ').upper()}", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.ln(2)
        
        content = fake.paragraph(nb_sentences=8)
        pdf.multi_cell(0, 6, txt=content)
        
        # Diagnostic Results (Realistic Table-like look)
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(60, 8, "Parameter", 1)
        pdf.cell(60, 8, "Result", 1)
        pdf.cell(60, 8, "Reference Range", 1)
        pdf.ln(8)
        pdf.set_font("Arial", size=10)
        
        params = [("Hemoglobin", "14.2 g/dL", "13.5 - 17.5"), ("WBC Count", "7,500 /mcL", "4,500 - 11,000"), ("Blood Sugar", "98 mg/dL", "70 - 100")]
        for p, r, ref in params:
            pdf.cell(60, 8, p, 1)
            pdf.cell(60, 8, r, 1)
            pdf.cell(60, 8, ref, 1)
            pdf.ln(8)
            
        # Footer
        pdf.ln(20)
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(200, 5, txt="This is a computer-generated report. No physical signature is required.", ln=True, align='C')
        pdf.cell(200, 5, txt="CONFIDENTIAL MEDICAL RECORD", ln=True, align='C')
        
        pdf.output(file_path)
        return f"/patient_reports/{file_name}"

    @retry_mongodb
    def generate_docs_and_summaries(self, visit_data):
        logger.info("Generating documents and summaries...")
        
        # Cache patient names for PDFs
        patient_names = {p['patient_id']: p['name'] for p in self.db.patients.find({}, {"patient_id": 1, "name": 1})}
        
        docs_batch = []
        for i in range(SCALE['documents']):
            v_id, p_id, admitted_at, _ = random.choice(visit_data)
            doc_id = str(uuid.uuid4())
            doc_type = random.choice(DOC_TYPES)
            
            # Generate the actual PDF file
            p_name = patient_names.get(p_id, "Unknown Patient")
            file_url = self._generate_report_pdf(doc_id, doc_type, p_name, p_id)
            
            docs_batch.append({
                "document_id": doc_id,
                "patient_id": p_id,
                "visit_id": v_id,
                "document_type": doc_type,
                "extracted_text": fake.text(max_nb_chars=500),
                "file_path": file_url,
                "upload_source": random.choice(UPLOAD_SOURCES),
                "processing_status": "COMPLETED",
                "uploaded_at": admitted_at + timedelta(hours=random.randint(1, 10))
            })
            
            if len(docs_batch) >= 500: # Smaller batch for file operations
                self.db.documents.insert_many(docs_batch)
                docs_batch = []
                if (i % 1000) == 0:
                    logger.info(f"Progress: {i} PDFs generated...")

        summaries_batch = []
        for _ in range(SCALE['summaries']):
            v_id, p_id, _, _ = random.choice(visit_data)
            summaries_batch.append({
                "summary_id": str(uuid.uuid4()),
                "patient_id": p_id,
                "visit_id": v_id,
                "patient_concerns": fake.sentence(),
                "request_history": f"{random.randint(1, 10)} requests processed",
                "doctor_notes": fake.paragraph(),
                "generated_at": datetime.now()
            })
            if len(summaries_batch) >= 5000:
                self.db.summaries.insert_many(summaries_batch)
                summaries_batch = []

        if docs_batch: self.db.documents.insert_many(docs_batch)
        if summaries_batch: self.db.summaries.insert_many(summaries_batch)
        logger.info("Documents and summaries generated.")

    def run(self):
        start_time = time.time()
        logger.info("Starting production-scale data generation pipeline...")
        
        self.clear_database()
        self.create_indexes()
        self.generate_staff()
        self.generate_rooms_and_beds()
        self.generate_patients()
        visit_data = self.generate_visits()
        req_info = self.generate_requests(visit_data)
        self.generate_events(req_info, visit_data)
        self.generate_docs_and_summaries(visit_data)
        
        end_time = time.time()
        logger.info(f"Pipeline completed in {round((end_time - start_time) / 60, 2)} minutes.")
        logger.info("Database: caremate_db is now populated.")

if __name__ == "__main__":
    if not MONGO_URI:
        logger.error("MONGO_URI not found in .env file.")
    else:
        generator = HospitalDataGenerator(MONGO_URI, DB_NAME)
        generator.run()
