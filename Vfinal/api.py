import os
import uuid
import logging
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Any
from main import CareMateBackend
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize FastAPI App
app = FastAPI(title="CareMate AI Production API", description="Hospital Assistant Full Backend")

# 1. Enable CORS for Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Serve generated audio files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "generated_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

# Initialize Backend Core
backend = CareMateBackend()

# --- Dual Database Setup ---
CORE_MONGO_URI = os.getenv("MONGO_URI")
core_client = MongoClient(CORE_MONGO_URI)
db = core_client["caremate_db"]

FRONTEND_MONGO_URI = os.getenv(
    "FRONTEND_MONGO_URI",
    "mongodb+srv://Caremate-frontend:FIOWipLqLhFyp4uP@cluster0.agxm8kg.mongodb.net/?appName=Cluster0",
)
frontend_client = MongoClient(FRONTEND_MONGO_URI)
interaction_db = frontend_client["caremate_interaction_db"]
frontend_db = interaction_db  # alias — same DB, clearer name for staff queries


def _audio_public_url(req: Request, audio_path: Optional[str]) -> Optional[str]:
    if not audio_path:
        return None
    return f"{str(req.base_url).rstrip('/')}/audio/{os.path.basename(audio_path)}"


def _ws_payload(msg_type: str, data: dict) -> dict:
    """WebSocket message with nested data and top-level fields for frontend compatibility."""
    return {
        "type": msg_type,
        "data": data,
        "timestamp": datetime.now().isoformat(),
        **data,
    }


def _log_interaction(patient_id: str, patient_name: str, room_id: str, **fields) -> str:
    interaction_id = str(uuid.uuid4())
    interaction_db.interactions.insert_one({
        "interaction_id": interaction_id,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "room_id": room_id,
        "timestamp": datetime.now(),
        **fields,
    })
    return interaction_id

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        # Store connections with their staff_id and role
        self.active_connections: dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, staff_id: str = None, role: str = None):
        await websocket.accept()
        self.active_connections[websocket] = {
            "staff_id": staff_id,
            "role": role
        }
        logger.info(f"New Dashboard Connected (staff_id={staff_id}, role={role}). Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            info = self.active_connections[websocket]
            del self.active_connections[websocket]
            logger.info(f"Dashboard Disconnected (staff_id={info.get('staff_id')}). Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast to all connected dashboards (for emergencies only)"""
        logger.info(f"Broadcasting to {len(self.active_connections)} dashboards: {message['type']}")
        for connection in list(self.active_connections.keys()):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast Error: {e}")

    async def send_to_role(self, message: dict, target_role: str):
        """Send message only to dashboards with specific role"""
        count = 0
        for connection, info in list(self.active_connections.items()):
            if info.get("role") == target_role:
                try:
                    await connection.send_json(message)
                    count += 1
                except Exception as e:
                    logger.error(f"Send to role error: {e}")
        logger.info(f"Sent {message['type']} to {count} {target_role} dashboards")

    async def send_to_assigned_staff(self, message: dict, patient_id: str, intent: str):
        """Send message only to staff assigned to this patient based on intent"""
        # Determine which roles should receive this notification
        role_mapping = {
            "doctor_query": ["doctor", "admin"],
            "status_query": ["doctor", "admin"],
            "emergency": ["doctor", "admin"],  # Emergencies go to all doctors + admin
            "nurse_request": ["nurse", "admin"],
            "nutrition_request": ["nutritionist", "admin"],
            "utility_request": ["utility", "admin"],
            "general_conversation": [],  # No dashboard notification
        }
        
        target_roles = role_mapping.get(intent, ["admin"])
        
        # For emergencies, broadcast to all doctors
        if intent == "emergency":
            await self.broadcast(message)
            return
        
        # Get assigned staff for this patient
        lookup = interaction_db.patient_lookup.find_one({"patient_id": patient_id})
        if not lookup:
            # If no assignment found, send to all staff of target roles
            for role in target_roles:
                await self.send_to_role(message, role)
            return
        
        # Get assigned staff IDs
        assigned_staff_ids = []
        if "doctor" in target_roles and lookup.get("doctor_id"):
            assigned_staff_ids.append(lookup.get("doctor_id"))
        if "nurse" in target_roles and lookup.get("nurse_id"):
            assigned_staff_ids.append(lookup.get("nurse_id"))
        
        # Send to assigned staff + admin
        count = 0
        for connection, info in list(self.active_connections.items()):
            staff_id = info.get("staff_id")
            role = info.get("role")
            
            # Send if: assigned to patient OR admin OR utility (sees all)
            if (staff_id in assigned_staff_ids or 
                role == "admin" or 
                (role == "utility" and "utility" in target_roles) or
                (role == "nutritionist" and "nutritionist" in target_roles)):
                try:
                    await connection.send_json(message)
                    count += 1
                except Exception as e:
                    logger.error(f"Send to assigned staff error: {e}")
        
        logger.info(f"Sent {message['type']} to {count} assigned staff for patient {patient_id}")

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast Error: {e}")

manager = ConnectionManager()

# --- Data Models ---
class ChatRequest(BaseModel):
    patient_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    transcript: Optional[str] = None
    response_text: str
    response_audio_url: Optional[str] = None
    intent: str

class LoginRequest(BaseModel):
    email: str
    password: str


class DoctorTextResponse(BaseModel):
    patient_id: str
    message: str

# --- API Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "online", "database": "connected", "agents": "ready"}

@app.post("/auth/login")
async def login(request: LoginRequest):
    staff = interaction_db.staff_directory.find_one({
        "email": request.email.lower(),
        "password": request.password
    })
    if not staff:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "token": "token-" + str(uuid.uuid4())[:8],
        "user": {"id": staff["staff_id"], "name": staff["name"], "role": staff["role"]},
    }


@app.post("/auth/logout")
async def logout():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, req: Request):
    try:
        lookup = interaction_db.patient_lookup.find_one({"patient_id": request.patient_id})
        patient_name = lookup.get("name") if lookup else "Unknown"
        room_id = lookup.get("room_id") if lookup else "N/A"
        
        classification = backend.router.classify(request.message)
        intent = classification['intent']
        result_text = backend.process_input(request.message, request.patient_id)
        
        audio_path = backend.speech.tts(result_text)
        audio_url = f"{str(req.base_url).rstrip('/')}/audio/{os.path.basename(audio_path)}" if audio_path else None
        
        _log_interaction(
            request.patient_id, patient_name, room_id,
            type="TEXT", message=request.message, intent=intent,
        )

        await manager.send_to_assigned_staff(_ws_payload("NEW_REQUEST", {
            "patient_id": request.patient_id,
            "patient_name": patient_name,
            "room": room_id,
            "intent": intent,
            "message": request.message,
        }), request.patient_id, intent)
        
        return ChatResponse(session_id=str(uuid.uuid4()), response_text=result_text, response_audio_url=audio_url, intent=intent)
    except Exception as e:
        logger.error(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice", response_model=ChatResponse)
async def voice_endpoint(req: Request, patient_id: str, file: UploadFile = File(...), patient_name: Optional[str] = Query(None)):
    temp_filename = f"v_{uuid.uuid4()}.mp3"
    temp_path = os.path.join(AUDIO_DIR, temp_filename)
    try:
        logger.info(f"/voice request for patient_id={patient_id}, filename={file.filename}")
        
        lookup = interaction_db.patient_lookup.find_one({"patient_id": patient_id})
        p_name = patient_name or (lookup.get("name") if lookup else "Unknown")
        room_id = lookup.get("room_id") if lookup else "N/A"

        # Save uploaded file with validation
        content = await file.read()
        logger.info(f"Audio file size: {len(content)} bytes")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        with open(temp_path, "wb") as buffer: 
            buffer.write(content)
        
        logger.info("Starting voice processing...")
        
        # Get intent early for targeted notification (we'll classify after STT)
        # For now, send processing notification to all assigned staff
        # We'll send the final notification with proper targeting after intent classification
        
        # OPTIMIZATION 2: Process with timeout handling
        try:
            # Use asyncio.wait_for to add timeout protection
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, backend.process_voice_input, temp_path, patient_id
                ),
                timeout=60.0  # 60 second timeout
            )
        except asyncio.TimeoutError:
            logger.error("Voice processing timed out after 60 seconds")
            # Send quick fallback response
            fallback_response = "I received your message and am processing it. Please wait a moment for a detailed response."
            audio_path = backend.speech.tts(fallback_response)
            
            # Send timeout notification to assigned staff only
            await manager.send_to_assigned_staff(_ws_payload("PROCESSING_TIMEOUT", {
                "patient_id": patient_id,
                "patient_name": p_name,
                "room": room_id,
                "message": "Processing timeout - sending quick response",
                "status": "timeout"
            }), patient_id, "general_conversation")
            
            return ChatResponse(
                session_id=str(uuid.uuid4()),
                transcript="[Voice message received]",
                response_text=fallback_response,
                response_audio_url=_audio_public_url(req, audio_path),
                intent="general_conversation"
            )
        
        logger.info(f"Voice processing result: {result}")
        
        if "error" in result: 
            logger.error(f"Voice processing error: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
            
        logger.info("Classifying intent...")
        intent = backend.router.classify(result['transcript'])['intent']
        
        logger.info("Logging interaction...")
        _log_interaction(
            patient_id, p_name, room_id,
            type="VOICE", transcript=result["transcript"], intent=intent,
        )

        logger.info("Sending targeted WebSocket notification...")
        # Send to assigned staff based on intent (emergencies go to all doctors)
        await manager.send_to_assigned_staff(_ws_payload(
            "EMERGENCY_ALERT" if intent == "emergency" else "NEW_REQUEST",
            {
                "patient_id": patient_id,
                "patient_name": p_name,
                "room": room_id,
                "intent": intent,
                "message": result["transcript"],
                "status": "completed"
            },
        ), patient_id, intent)

        logger.info("Generating audio URL...")
        audio_url = _audio_public_url(req, result.get("response_audio"))
        
        logger.info("Voice endpoint completed successfully")
        return ChatResponse(
            session_id=str(uuid.uuid4()),
            transcript=result.get("transcript") or "[Voice message received]",
            response_text=result.get("response_text") or "I received your message. A staff member will assist you shortly.",
            response_audio_url=audio_url,
            intent=intent,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice endpoint error: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")
    finally:
        if os.path.exists(temp_path): 
            os.remove(temp_path)

# --- Nurse & OCR Upload Endpoints ---

@app.post("/nurse/upload-document")
async def upload_document(patient_id: str, file: UploadFile = File(...)):
    try:
        REPORTS_DIR = os.path.join(BASE_DIR, "patient_reports")
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        filename = f"rep_{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(REPORTS_DIR, filename)
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        lookup = interaction_db.patient_lookup.find_one({"patient_id": patient_id})
        p_name = lookup.get("name") if lookup else "Unknown"
        room_id = lookup.get("room_id") if lookup else "N/A"
        
        doc_id = str(uuid.uuid4())
        doc_record = {
            "document_id": doc_id,
            "patient_id": patient_id,
            "document_type": "OCR_Report",
            "file_path": f"/patient_reports/{filename}",
            "uploaded_at": datetime.now(),
            "status": "INDEXED"
        }
        db.documents.insert_one(doc_record)
        
        # Run IDP pipeline in background (non-blocking)
        async def run_idp():
            try:
                from idp_pipeline import get_idp_pipeline
                pipeline = get_idp_pipeline()
                
                # Try Textract first, fall back to pypdf
                aws_key = os.getenv("AWS_ACCESS_KEY_ID", "")
                if aws_key and aws_key != "YOUR_ACCESS_KEY":
                    result = pipeline.process_document(file_path, patient_id)
                else:
                    logger.warning("AWS credentials not configured — using pypdf fallback")
                    result = pipeline.process_document_fallback(file_path, patient_id)
                
                logger.info(f"IDP result for patient {patient_id}: {result}")
                
                # Send update to assigned doctor and admin only
                await manager.send_to_assigned_staff(_ws_payload("DOCUMENT_PROCESSED", {
                    "patient_id":        result.get("patient_id", patient_id),
                    "patient_name":      p_name,
                    "room":              room_id,
                    "document_id":       doc_id,
                    "updated_fields":    result.get("updated_fields", []),
                    "abnormal_flags":    result.get("abnormal_flags", []),
                    "critical_count":    result.get("critical_count", 0),
                    "ai_interpretation": result.get("ai_interpretation", ""),
                    "history_id":        result.get("history_id", ""),
                    "status":            result.get("status"),
                }), patient_id, "doctor_query")  # Send to doctor assigned to this patient
            except Exception as e:
                logger.error(f"IDP background error: {e}")
        # Schedule IDP as background task
        import asyncio
        asyncio.create_task(run_idp())
        
        _log_interaction(
            patient_id, p_name, room_id,
            type="DOCUMENT",
            message=f"Clinical report '{file.filename}' uploaded. IDP processing started.",
            intent="document_submission",
        )

        # Notify assigned doctor and nurse about document upload
        await manager.send_to_assigned_staff(_ws_payload("NEW_REQUEST", {
            "patient_id": patient_id,
            "patient_name": p_name,
            "room": room_id,
            "intent": "document_submission",
            "message": f"Clinical report '{file.filename}' uploaded. Processing with IDP...",
        }), patient_id, "doctor_query")
        
        return {
            "status": "success",
            "document_id": doc_id,
            "message": "Document uploaded. IDP extraction running in background.",
        }
    except Exception as e:
        logger.error(f"Document Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nurse/documents")
async def get_nurse_documents():
    docs = list(db.documents.find({}, {"_id": 0}))
    return {"documents": docs}

@app.get("/patients/{patient_id}/document-status")
async def get_document_status(patient_id: str):
    """Get IDP processing status for a patient's documents"""
    docs = list(db.documents.find(
        {"patient_id": patient_id},
        {"_id": 0, "document_id": 1, "document_type": 1, "status": 1,
         "uploaded_at": 1, "idp_processed_at": 1, "lab_results": 1}
    ).sort("uploaded_at", -1).limit(10))
    return {"documents": docs}


@app.get("/patients/{patient_id}/history")
async def get_patient_history(patient_id: str):
    """Get full patient history including lab reports, analysis, and AI interpretations"""
    history = list(db.patient_history.find(
        {"patient_id": patient_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(20))

    # Serialize datetime objects
    for entry in history:
        for key, val in entry.items():
            if hasattr(val, "isoformat"):
                entry[key] = val.isoformat()

    return {"history": history, "total": len(history)}


@app.get("/patients/{patient_id}/history/latest")
async def get_latest_history(patient_id: str):
    """Get the most recent lab report analysis for a patient"""
    entry = db.patient_history.find_one(
        {"patient_id": patient_id},
        {"_id": 0},
        sort=[("created_at", -1)]
    )
    if not entry:
        raise HTTPException(status_code=404, detail="No history found")

    for key, val in entry.items():
        if hasattr(val, "isoformat"):
            entry[key] = val.isoformat()

    return {"entry": entry}

@app.get("/nurse/assignments")
async def get_nurse_assignments():
    visits = list(db.visits.find({"status": "ACTIVE"}, {"_id": 0}))
    return {"assignments": visits}

@app.get("/admin/activities")
async def get_admin_activities(range: str = "1h"):
    activities = list(interaction_db.interactions.find({}, {"_id": 0}).sort("timestamp", -1).limit(20))
    return {"activities": activities}

@app.get("/doctor/queries")
async def get_doctor_queries(staff_id: Optional[str] = Query(None)):
    """Get queries only for the doctor's assigned patients, enriched with real patient names"""
    doctor_intents = ["doctor_query", "status_query", "emergency"]

    if staff_id:
        assignment = frontend_db.staff_assignments.find_one(
            {"staff_id": staff_id, "role": "doctor"}, {"_id": 0}
        )
        patient_ids = assignment.get("patient_ids", []) if assignment else []
        query_filter = {"intent": {"$in": doctor_intents}, "patient_id": {"$in": patient_ids}} if patient_ids else {"intent": {"$in": doctor_intents}}
    else:
        query_filter = {"intent": {"$in": doctor_intents}}

    queries = list(
        interaction_db.interactions.find(query_filter, {"_id": 0})
        .sort("timestamp", -1).limit(50)
    )

    # Enrich with real patient names from patient_lookup
    for q in queries:
        lookup = interaction_db.patient_lookup.find_one(
            {"patient_id": q.get("patient_id")}, {"_id": 0, "name": 1, "room_id": 1}
        )
        if lookup:
            q["patient_name"] = lookup.get("name", q.get("patient_name", "Unknown"))
            if not q.get("room_id") or q.get("room_id") == "N/A":
                q["room_id"] = lookup.get("room_id", "N/A")

    return {"queries": queries}


@app.get("/nurse/queries")
async def get_nurse_queries(staff_id: Optional[str] = Query(None)):
    """Get queries only for the nurse's assigned patients"""
    nurse_intents = ["nurse_request", "medication_query", "vital_signs"]

    if staff_id:
        assignment = frontend_db.staff_assignments.find_one(
            {"staff_id": staff_id, "role": "nurse"}, {"_id": 0}
        )
        patient_ids = assignment.get("patient_ids", []) if assignment else []

        if patient_ids:
            queries = list(
                interaction_db.interactions.find(
                    {"intent": {"$in": nurse_intents}, "patient_id": {"$in": patient_ids}},
                    {"_id": 0}
                ).sort("timestamp", -1).limit(20)
            )
        else:
            queries = []
    else:
        queries = list(
            interaction_db.interactions.find(
                {"intent": {"$in": nurse_intents}},
                {"_id": 0}
            ).sort("timestamp", -1).limit(20)
        )

    return {"queries": queries}


@app.get("/nutrition/queries")
async def get_nutrition_queries(staff_id: Optional[str] = Query(None)):
    """Get nutrition queries for the nutritionist's assigned patients"""
    nutrition_intents = ["nutrition_request", "dietary_query", "meal_request"]

    if staff_id:
        assignment = frontend_db.staff_assignments.find_one(
            {"staff_id": staff_id, "role": "nutritionist"}, {"_id": 0}
        )
        patient_ids = assignment.get("patient_ids", []) if assignment else []

        if patient_ids:
            queries = list(
                interaction_db.interactions.find(
                    {"intent": {"$in": nutrition_intents}, "patient_id": {"$in": patient_ids}},
                    {"_id": 0}
                ).sort("timestamp", -1).limit(20)
            )
        else:
            queries = []
    else:
        queries = list(
            interaction_db.interactions.find(
                {"intent": {"$in": nutrition_intents}},
                {"_id": 0}
            ).sort("timestamp", -1).limit(20)
        )

    return {"queries": queries}


@app.get("/utility/queries")
async def get_utility_queries(staff_id: Optional[str] = Query(None)):
    """Get utility queries (utility staff see all rooms)"""
    utility_intents = ["utility_request", "maintenance_request", "room_service"]

    queries = list(
        interaction_db.interactions.find(
            {"intent": {"$in": utility_intents}},
            {"_id": 0}
        ).sort("timestamp", -1).limit(20)
    )

    return {"queries": queries}


@app.get("/staff/{staff_id}/assignment")
async def get_staff_assignment(staff_id: str):
    """Get a staff member's assigned patients and rooms"""
    assignment = frontend_db.staff_assignments.find_one(
        {"staff_id": staff_id}, {"_id": 0}
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Staff assignment not found")
    return {"assignment": assignment}


@app.get("/staff/directory")
async def get_staff_directory(role: Optional[str] = Query(None)):
    """Get all staff, optionally filtered by role"""
    query = {}
    if role:
        query["role"] = role.lower()
    staff = list(frontend_db.staff_directory.find(query, {"_id": 0, "password": 0}))
    return {"staff": staff}

@app.post("/doctor/voice-response")
async def doctor_voice_response(patient_id: str, file: UploadFile = File(...), req: Request = None):
    """Enhanced doctor voice response with audio validation"""
    try:
        logger.info(f"Doctor voice response for patient {patient_id}, file: {file.filename}")
        
        # Read and validate audio content
        content = await file.read()
        logger.info(f"Audio file size: {len(content)} bytes")
        
        # Validate audio file
        if len(content) < 1000:  # Less than 1KB is likely invalid
            logger.error(f"Audio file too small: {len(content)} bytes")
            raise HTTPException(status_code=400, detail=f"Audio file too small ({len(content)} bytes). Please record a proper voice message.")
        
        # Save audio file
        filename = f"dr_{uuid.uuid4()}.mp3"
        path = os.path.join(AUDIO_DIR, filename)
        
        with open(path, "wb") as f: 
            f.write(content)
        
        # Verify file was written correctly
        if not os.path.exists(path) or os.path.getsize(path) != len(content):
            logger.error("Failed to save audio file properly")
            raise HTTPException(status_code=500, detail="Failed to save audio file")
        
        # Generate URL
        url = f"{str(req.base_url).rstrip('/')}/audio/{filename}" if req else f"http://localhost:8000/audio/{filename}"
        
        # Store in database
        interaction_db.doctor_messages.insert_one({
            "patient_id": patient_id, 
            "audio_url": url, 
            "sent_at": datetime.now(), 
            "played": False,
            "file_size": len(content),
            "filename": filename
        })
        
        logger.info(f"Doctor voice message saved successfully: {filename} ({len(content)} bytes)")
        return {"status": "success", "filename": filename, "size": len(content)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Doctor voice response error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process voice message: {str(e)}")

@app.get("/admin/metrics")
async def get_metrics():
    metrics = {
        "total_patients": db.patients.count_documents({}),
        "active_visits": db.visits.count_documents({"status": "ACTIVE"}),
        "emergency_alerts": interaction_db.interactions.count_documents({"intent": "emergency"}),
        "pending_requests": db.requests.count_documents({"status": "REQUESTED"}),
        "staff_online": interaction_db.staff_directory.count_documents({}),
    }
    return {"metrics": metrics, **metrics}


@app.get("/admin/alerts")
async def get_admin_alerts():
    emergencies = list(
        interaction_db.interactions.find({"intent": "emergency"}, {"_id": 0})
        .sort("timestamp", -1).limit(10)
    )
    alerts = [
        {
            "id": e.get("interaction_id", str(uuid.uuid4())),
            "room": e.get("room_id", "N/A"),
            "type": e.get("intent", "emergency"),
            "message": e.get("message") or e.get("transcript", ""),
            "patient_id": e.get("patient_id"),
            "timestamp": e.get("timestamp"),
        }
        for e in emergencies
    ]
    return {"alerts": alerts}


@app.get("/admin/users")
async def get_admin_users():
    users = list(interaction_db.staff_directory.find({}, {"_id": 0, "password": 0}))
    return {"users": users}


@app.get("/patients/{patient_id}")
async def get_patient(patient_id: str):
    patient = db.patients.find_one({"patient_id": patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = db.visits.find_one({"patient_id": patient_id, "status": "ACTIVE"}, {"_id": 0})
    return {"patient": {**patient, "visit": visit}}


@app.get("/patients/{patient_id}/vitals")
async def get_patient_vitals(patient_id: str):
    visit = db.visits.find_one({"patient_id": patient_id, "status": "ACTIVE"}, {"_id": 0})
    vitals = (visit or {}).get("vitals", [])
    return {"vitals": vitals if isinstance(vitals, list) else [vitals]}


@app.get("/patients/{patient_id}/medications")
async def get_patient_medications(patient_id: str):
    patient = db.patients.find_one({"patient_id": patient_id}, {"_id": 0})
    meds = (patient or {}).get("medications", [])
    return {"medications": meds if isinstance(meds, list) else []}


@app.get("/patients/{patient_id}/notes")
async def get_patient_notes(patient_id: str):
    summaries = list(db.summaries.find({"patient_id": patient_id}, {"_id": 0}).limit(10))
    return {"notes": summaries}


def _requests_for_role(request_type: str, limit: int = 30):
    """Build dashboard queue items from core requests + patient lookup."""
    reqs = list(
        db.requests.find(
            {"request_type": {"$regex": request_type, "$options": "i"}, "status": "REQUESTED"},
            {"_id": 0},
        ).sort("created_at", -1).limit(limit)
    )
    items = []
    for r in reqs:
        patient = db.patients.find_one({"patient_id": r["patient_id"]}, {"_id": 0, "name": 1})
        visit = db.visits.find_one({"patient_id": r["patient_id"], "status": "ACTIVE"}, {"_id": 0, "room_id": 1})
        items.append({
            **r,
            "patient_name": (patient or {}).get("name", "Unknown"),
            "room": (visit or {}).get("room_id", "N/A"),
        })
    return items


@app.get("/nutrition/plans")
async def get_nutrition_plans():
    patients = list(db.patients.find({}, {"_id": 0, "patient_id": 1, "name": 1, "allergies": 1, "dietary_restrictions": 1}).limit(50))
    plans = []
    for p in patients:
        visit = db.visits.find_one({"patient_id": p["patient_id"], "status": "ACTIVE"}, {"_id": 0, "room_id": 1})
        if not visit:
            continue
        plans.append({
            "patient_id": p["patient_id"],
            "patient_name": p.get("name"),
            "room": visit.get("room_id"),
            "allergies": p.get("allergies", []),
            "restrictions": p.get("dietary_restrictions", "Standard hospital diet"),
        })
    return {"plans": plans}


@app.get("/nutrition/meals")
async def get_nutrition_meals(date: str = ""):
    items = _requests_for_role("NUTRITION|nutrition", 40)
    if not items:
        activities = list(
            interaction_db.interactions.find({"intent": "nutrition_request"}, {"_id": 0})
            .sort("timestamp", -1).limit(20)
        )
        items = [
            {
                "request_id": a.get("interaction_id"),
                "room": a.get("room_id"),
                "patient_name": a.get("patient_name"),
                "request_text": a.get("message") or a.get("transcript"),
                "created_at": a.get("timestamp"),
            }
            for a in activities
        ]
    return {"meals": items}


@app.get("/nutrition/alerts")
async def get_nutrition_alerts():
    alerts = list(
        db.patients.find({"allergies": {"$exists": True, "$ne": []}}, {"_id": 0, "patient_id": 1, "name": 1, "allergies": 1}).limit(20)
    )
    return {"alerts": [{"patient_id": a["patient_id"], "name": a.get("name"), "allergies": a.get("allergies", [])} for a in alerts]}


@app.get("/utility/maintenance")
async def get_utility_maintenance():
    items = _requests_for_role("UTILITY|utility", 40)
    if not items:
        activities = list(
            interaction_db.interactions.find({"intent": "utility_request"}, {"_id": 0})
            .sort("timestamp", -1).limit(20)
        )
        items = [
            {
                "request_id": a.get("interaction_id"),
                "room": a.get("room_id"),
                "patient_name": a.get("patient_name"),
                "request_text": a.get("message") or a.get("transcript"),
                "category": "general",
                "created_at": a.get("timestamp"),
                "priority": "MEDIUM",
            }
            for a in activities
        ]
    return {"requests": items}


@app.get("/utility/systems")
async def get_utility_systems():
    rooms_total = db.rooms.count_documents({}) if "rooms" in db.list_collection_names() else 0
    beds = db.beds.count_documents({}) if "beds" in db.list_collection_names() else 0
    return {
        "systems": [
            {"name": "HVAC", "status": "operational", "uptime": 99.2},
            {"name": "Power", "status": "operational", "uptime": 99.9},
            {"name": "Water", "status": "operational", "uptime": 98.5},
            {"name": "Rooms monitored", "status": "operational", "count": rooms_total or beds},
        ]
    }


@app.get("/utility/alerts")
async def get_utility_alerts():
    high = list(db.requests.find({"priority": "HIGH", "status": "REQUESTED"}, {"_id": 0}).limit(10))
    return {"alerts": high}


@app.post("/doctor/text-response")
async def doctor_text_response(body: DoctorTextResponse):
    interaction_db.doctor_messages.insert_one({
        "patient_id": body.patient_id,
        "text": body.message,
        "sent_at": datetime.now(),
        "played": False,
    })
    return {"status": "success", "patient_id": body.patient_id}

@app.get("/patients/{patient_id}/lookup")
async def get_patient_lookup(patient_id: str):
    """Quick lookup — returns patient name and room from patient_lookup"""
    lookup = interaction_db.patient_lookup.find_one({"patient_id": patient_id}, {"_id": 0})
    if not lookup:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "patient_id": lookup["patient_id"],
        "name": lookup.get("name", "Unknown"),
        "room_id": lookup.get("room_id", "N/A"),
        "bed_id": lookup.get("bed_id", "N/A"),
    }


@app.get("/patients/{patient_id}/doctor-messages")
async def get_patient_doctor_messages(patient_id: str):
    """Get unplayed doctor messages for a specific patient"""
    try:
        # Get unplayed messages
        messages = list(
            interaction_db.doctor_messages.find(
                {"patient_id": patient_id, "played": False},
                {"_id": 0}
            ).sort("sent_at", 1)
        )
        
        # Mark messages as played
        if messages:
            interaction_db.doctor_messages.update_many(
                {"patient_id": patient_id, "played": False},
                {"$set": {"played": True}}
            )
        
        # Format messages for frontend
        formatted_messages = []
        for msg in messages:
            if "text" in msg:
                formatted_messages.append({
                    "type": "text",
                    "text": msg["text"],
                    "sent_at": msg["sent_at"].isoformat()
                })
            elif "audio_url" in msg:
                formatted_messages.append({
                    "type": "audio", 
                    "audio_url": msg["audio_url"],
                    "sent_at": msg["sent_at"].isoformat()
                })
        
        return {"messages": formatted_messages}
        
    except Exception as e:
        logger.error(f"Error getting doctor messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, staff_id: str = Query(None), role: str = Query(None)):
    await manager.connect(websocket, staff_id=staff_id, role=role)
    try:
        while True:
            # Receive messages from client (can be used for heartbeat or commands)
            data = await websocket.receive_text()
            # Optional: handle client messages here
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
