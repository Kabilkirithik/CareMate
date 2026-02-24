# CareMate Backend - Complete Documentation

## 🏥 Agentic AI-Powered Hospital Assistant

CareMate is a sophisticated voice-first hospital patient assistance system built using a **two-agent CrewAI architecture**. It combines state-of-the-art speech processing with intelligent decision-making to provide safe, policy-compliant patient support.

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Technologies Used](#technologies-used)
4. [Setup Instructions](#setup-instructions)
5. [API Documentation](#api-documentation)
6. [Two-Agent Architecture](#two-agent-architecture)
7. [Tools and Capabilities](#tools-and-capabilities)
8. [Security and Safety](#security-and-safety)
9. [Deployment](#deployment)
10. [Testing](#testing)
11. [Troubleshooting](#troubleshooting)

---

## 🎯 System Overview

CareMate addresses the critical need for continuous, intelligent patient interaction in hospital wards. The system:

- **Listens** to patient queries via bedside voice interface (ESP32 + microphone)
- **Understands** intent and context using multilingual speech recognition
- **Analyzes** patient medical records and interaction history
- **Responds** intelligently while enforcing strict safety policies
- **Escalates** to medical staff when necessary
- **Logs** all interactions for auditability and compliance

### Key Features

✅ **Voice-First Interaction** - Natural language communication in 10+ Indian languages  
✅ **Context-Aware Intelligence** - Retrieves patient records and history  
✅ **Safety-First Design** - Never provides autonomous medical advice  
✅ **Human-in-the-Loop** - Mandatory approvals for medical requests  
✅ **Emergency Detection** - Automatic escalation for critical situations  
✅ **Complete Auditability** - Full logging of all decisions and interactions  

---

## 🏗️ Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CAREMATE SYSTEM                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐      ┌──────────────┐     ┌────────────┐ │
│  │   ESP32     │─────▶│   Speech     │────▶│   CrewAI   │ │
│  │  Bedside    │      │  Processing  │     │  Two-Agent │ │
│  │  Device     │◀─────│  (Sarvam AI) │◀────│   System   │ │
│  └─────────────┘      └──────────────┘     └────────────┘ │
│                                                             │
│  ┌─────────────┐      ┌──────────────┐     ┌────────────┐ │
│  │   MongoDB   │◀────▶│   FastAPI    │────▶│   Staff    │ │
│  │  Database   │      │  REST API    │     │ Dashboard  │ │
│  └─────────────┘      └──────────────┘     └────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. Patient speaks → ESP32 records audio
2. Audio (base64) → Sarvam AI STT → English text
3. English text → Patient Intelligence Agent
4. Agent retrieves: Patient records, history, context
5. Agent analyzes: Intent, urgency, distress
6. Orchestrator Agent receives analysis
7. Orchestrator applies policies and decides action
8. Response generated → Sarvam AI TTS → Audio
9. Audio → ESP32 → Speaker → Patient hears response
10. All steps logged to MongoDB
```

---

## 🛠️ Technologies Used

### Core Framework
- **CrewAI v0.86.0** - Multi-agent orchestration framework
- **LangChain v0.3.14** - LLM integration and tooling
- **Google Gemini 2.0** - Domain language model for reasoning

### Speech Processing
- **Sarvam AI** - Indian language speech-to-text and text-to-speech
  - Saarika v2 model (STT with translation)
  - Bulbul v2 model (TTS with multiple voices)

### Backend
- **FastAPI v0.115.6** - High-performance REST API
- **Uvicorn v0.34.0** - ASGI server
- **Pydantic v2.10.5** - Data validation

### Database
- **MongoDB v4.10.1** - NoSQL database for patient records and logs

### Development
- **Python 3.10+** - Core programming language
- **Google Colab** - Cloud development environment

---

## 🚀 Setup Instructions

### Prerequisites

1. **API Keys Required:**
   - Google Gemini API key ([Get it here](https://makersuite.google.com/app/apikey))
   - Sarvam AI API key ([Sign up here](https://www.sarvam.ai/))

2. **Python 3.10+** installed
3. **MongoDB** (local or Atlas cloud)

### Option 1: Google Colab Setup (Recommended for Testing)

1. **Open the Colab Notebook:**
   ```
   caremate_colab_setup.ipynb
   ```

2. **Add API Keys to Colab Secrets:**
   - Click the 🔑 key icon in the left sidebar
   - Add `GEMINI_API_KEY`
   - Add `SARVAM_API_KEY`

3. **Run All Cells Sequentially:**
   - Dependencies will install automatically
   - MongoDB will be configured
   - Sample data will be created
   - Backend will start running

4. **Access the API:**
   - Use ngrok URL provided in output
   - API docs: `<ngrok_url>/docs`

### Option 2: Local Setup

1. **Clone/Download Files:**
   ```bash
   # Create project directory
   mkdir caremate_backend
   cd caremate_backend
   
   # Copy all files here
   ```

2. **Create Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   ```bash
   # Create .env file
   cat > .env << EOF
   GEMINI_API_KEY=your_gemini_api_key_here
   SARVAM_API_KEY=your_sarvam_api_key_here
   MONGODB_URI=mongodb://localhost:27017/
   OTEL_SDK_DISABLED=true
   EOF
   ```

5. **Start MongoDB:**
   ```bash
   # If using local MongoDB
   sudo systemctl start mongod
   
   # Or use MongoDB Atlas connection string in .env
   ```

6. **Run the Backend:**
   ```bash
   python caremate_backend.py
   ```

7. **Verify Installation:**
   ```bash
   # In another terminal
   curl http://localhost:8000/api/v1/health
   ```

---

## 📡 API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

#### 1. Health Check
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-02-05T10:30:00",
  "version": "1.0.0"
}
```

#### 2. Process Patient Query
```http
POST /api/v1/query
```

**Request Body:**
```json
{
  "audio_base64": "base64_encoded_audio_data",
  "hospital_id": "PT001",
  "room_number": "201",
  "bed_number": "A"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "interaction_id": "INT_20250205103045",
    "query_text_english": "When will the doctor visit?",
    "detected_language": "hi-IN",
    "intelligence_analysis": "...",
    "decision_result": "...",
    "response_text": "Dr. Sharma will visit during morning rounds at 10 AM.",
    "audio_response_base64": "base64_encoded_response_audio",
    "timestamp": "2025-02-05T10:30:45"
  }
}
```

#### 3. Get Patient Information
```http
GET /api/v1/patient/{hospital_id}
```

**Response:**
```json
{
  "hospital_id": "PT001",
  "name": "Rajesh Kumar",
  "age": 45,
  "room_number": "201",
  "bed_number": "A",
  "diagnosis": "Type 2 Diabetes Management",
  "current_medications": ["Metformin 500mg", "Lisinopril 10mg"],
  "allergies": ["Penicillin"],
  "doctor_assigned": "Dr. Sharma",
  "nurse_assigned": "Nurse Priya",
  "admission_date": "2025-02-03"
}
```

#### 4. Get Interaction History
```http
GET /api/v1/interactions/{patient_id}?limit=10
```

**Response:**
```json
{
  "interactions": [
    {
      "interaction_id": "INT_20250205103045",
      "patient_id": "PT001",
      "timestamp": "2025-02-05T10:30:45",
      "query_text": "When will the doctor visit?",
      "intent_analysis": {...},
      "response_decision": {...}
    }
  ]
}
```

### Interactive API Documentation

Once the server is running, visit:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 🤖 Two-Agent Architecture

### Why Two Agents?

CareMate uses a deliberately minimal two-agent design for:
- **Deterministic flow** - Predictable behavior in healthcare context
- **Strong safety** - Clear separation of analysis and decision-making
- **Low latency** - Reduced coordination overhead
- **Easier debugging** - Simpler system to monitor and troubleshoot

### Agent 1: Patient Intelligence Agent

**Role:** Patient Context Analyst

**Responsibilities:**
1. Retrieve patient medical records
2. Summarize context (non-diagnostic)
3. Classify intent (non-medical/medical/emergency)
4. Detect distress and urgency
5. Maintain interaction memory

**Tools:**
- `PatientRecordRetrievalTool`
- `ContextSummarizationTool`
- `IntentClassificationTool`
- `DistressDetectionTool`
- `MemoryManagementTool`

**Key Principle:** This agent NEVER makes decisions - only analyzes.

**Example Task:**
```python
Task(
    description="""
    Analyze patient query: "I need more pain medicine"
    
    Patient: PT001, Room 201, Bed A
    
    Tasks:
    1. Retrieve patient record
    2. Check current medications
    3. Classify intent
    4. Assess urgency
    """,
    agent=patient_intelligence_agent,
    expected_output="Structured intelligence report"
)
```

### Agent 2: Central Orchestrator & Policy Agent

**Role:** Decision-Making Brain

**Responsibilities:**
1. Evaluate hospital policies
2. Decide response type (direct/approval/escalation)
3. Generate patient-facing response
4. Trigger staff notifications
5. Log all decisions

**Tools:**
- `PolicyEvaluationTool`
- `NotificationTool`
- `AuditLoggingTool`

**Safety Rules (HARD-CODED):**
```python
RULES = {
    "no_autonomous_medical_advice": True,
    "medication_requires_approval": True,
    "emergency_immediate_escalation": True,
    "log_all_decisions": True
}
```

**Example Task:**
```python
Task(
    description="""
    Intelligence Report: Patient requesting pain medication
    Intent: MEDICAL
    Urgency: MEDIUM
    
    Apply policies:
    1. Check if medication request
    2. Require nurse approval
    3. Generate safe response
    4. Notify nurse
    5. Log decision
    """,
    agent=orchestrator_agent,
    expected_output="Response decision with actions"
)
```

### Agent Interaction Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   Patient Query                              │
│             "मुझे दर्द की दवा चाहिए"                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Sarvam AI Translation                              │
│        "I need pain medicine" (English)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│        AGENT 1: Patient Intelligence                         │
│                                                              │
│  1. Retrieves patient PT001 record                          │
│  2. Current medications: [Ibuprofen 400mg]                  │
│  3. Intent: MEDICAL                                          │
│  4. Urgency: MEDIUM                                          │
│  5. Distress: No                                             │
│                                                              │
│  Output: Structured Intelligence Report                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│     AGENT 2: Central Orchestrator & Policy                   │
│                                                              │
│  Policy Evaluation:                                          │
│  - Intent is MEDICAL ✓                                       │
│  - Medication request ✓                                      │
│  - RULE: Requires nurse approval                             │
│                                                              │
│  Actions:                                                    │
│  1. Generate response: "I'll inform the nurse"               │
│  2. Send notification to Nurse Priya                         │
│  3. Log to audit trail                                       │
│                                                              │
│  Output: Response + Escalation                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Sarvam AI Text-to-Speech                           │
│     "मैं नर्स प्रिया को सूचित कर रही हूं"                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Patient Hears Response                            │
│         Nurse receives notification                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Tools and Capabilities

### Custom CrewAI Tools

All tools inherit from `BaseTool` and are equipped to the agents:

#### 1. PatientRecordRetrievalTool
```python
Input: {"hospital_id": "PT001"}
Output: Complete patient medical record (JSON)
Purpose: Fetch patient data from MongoDB
```

#### 2. ContextSummarizationTool
```python
Input: Patient record data
Output: Safe, non-diagnostic summary
Purpose: Condense context for conversation
```

#### 3. IntentClassificationTool
```python
Input: Translated query text
Output: {
  "intent_category": "medical",
  "urgency_level": "medium",
  "confidence_score": 0.85
}
Purpose: Classify request type
```

#### 4. DistressDetectionTool
```python
Input: Query text
Output: {
  "distress_score": 0.7,
  "distress_detected": true,
  "patterns": ["pain_words", "urgency_words"]
}
Purpose: Detect emergency signals
```

#### 5. MemoryManagementTool
```python
Input: {"action": "retrieve", "patient_id": "PT001"}
Output: Recent interaction history
Purpose: Maintain conversational context
```

#### 6. PolicyEvaluationTool
```python
Input: Intent analysis + context
Output: {
  "can_respond_directly": false,
  "requires_approval": true,
  "applicable_policies": ["medication_requires_approval"]
}
Purpose: Apply hospital rules
```

#### 7. NotificationTool
```python
Input: {
  "target": "nurse",
  "message": "Pain medication request",
  "priority": "medium"
}
Output: Notification sent confirmation
Purpose: Alert medical staff
```

#### 8. AuditLoggingTool
```python
Input: {
  "event_type": "medication_request",
  "data": {...}
}
Output: Logged to audit trail
Purpose: Full transparency
```

---

## 🔒 Security and Safety

### Safety Guarantees

1. **No Autonomous Medical Advice**
   - System NEVER provides medical diagnoses
   - All medical requests escalated to staff

2. **Mandatory Human Approval**
   - Medication requests → Nurse/Doctor approval
   - Treatment changes → Doctor approval only

3. **Emergency Escalation**
   - Emergency keywords → Immediate alert
   - Critical urgency → Bypass normal flow

4. **Complete Auditability**
   - Every interaction logged
   - Every decision recorded
   - Timestamp and context preserved

### Policy Enforcement

Policies are enforced at the **Orchestrator Agent level**:

```python
def evaluate_policy(intent, context):
    if intent == "emergency":
        return {
            "action": "IMMEDIATE_ESCALATION",
            "target": "doctor",
            "bypass_normal_flow": True
        }
    
    if intent == "medical":
        return {
            "action": "REQUIRE_APPROVAL",
            "target": "nurse",
            "can_auto_respond": False
        }
    
    if intent == "non_medical":
        return {
            "action": "AUTO_RESPOND",
            "log_interaction": True
        }
```

### Data Privacy

- Patient data stored in MongoDB with access controls
- Audio data not permanently stored (only base64 in transit)
- Audit logs anonymized for analysis
- HIPAA-compliant architecture (when properly deployed)

---

## 🚢 Deployment

### Google Colab Deployment (Development)

```python
# Already configured in caremate_colab_setup.ipynb
# Just run all cells and get ngrok URL
```

### Local Development Server

```bash
# Start the server
python caremate_backend.py

# Server runs on http://localhost:8000
```

### Production Deployment Options

#### Option 1: Docker Container

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY caremate_backend.py .

CMD ["python", "caremate_backend.py"]
```

```bash
docker build -t caremate-backend .
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=xxx \
  -e SARVAM_API_KEY=xxx \
  caremate-backend
```

#### Option 2: Cloud Platforms

**Google Cloud Run:**
```bash
gcloud run deploy caremate-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

**AWS ECS/Fargate:**
- Use provided Dockerfile
- Configure environment variables in task definition

**Azure Container Instances:**
```bash
az container create \
  --resource-group caremate-rg \
  --name caremate-backend \
  --image caremate-backend:latest
```

### MongoDB Configuration

**Local MongoDB:**
```bash
# Ubuntu/Debian
sudo apt-get install mongodb-org
sudo systemctl start mongod
```

**MongoDB Atlas (Recommended for Production):**
1. Create cluster at mongodb.com/cloud/atlas
2. Get connection string
3. Set `MONGODB_URI` environment variable

---

## 🧪 Testing

### Unit Testing

```bash
pytest tests/ -v
```

### API Testing

```bash
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Test patient retrieval
curl http://localhost:8000/api/v1/patient/PT001

# Test query processing (with audio)
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "audio_base64": "<base64_audio>",
    "hospital_id": "PT001",
    "room_number": "201",
    "bed_number": "A"
  }'
```

### Agent Testing

```python
# Test individual agents
from caremate_backend import create_patient_intelligence_agent

agent = create_patient_intelligence_agent()
# Run test tasks...
```

---

## 🐛 Troubleshooting

### Common Issues

**1. MongoDB Connection Error**
```
Error: Could not connect to MongoDB
Solution: Check MONGODB_URI and ensure MongoDB is running
```

**2. Gemini API Key Invalid**
```
Error: Invalid API key
Solution: Verify GEMINI_API_KEY in environment variables
```

**3. Sarvam AI Rate Limit**
```
Error: 429 Too Many Requests
Solution: Wait and retry, or upgrade Sarvam AI plan
```

**4. CrewAI Import Errors**
```
Error: No module named 'crewai'
Solution: pip install -r requirements.txt
```

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Logs

Check system logs:
```bash
# View MongoDB logs
tail -f /var/log/mongodb/mongod.log

# View application logs
# (Logs print to console by default)
```

---

## 📞 Support

For issues, questions, or contributions:

1. **GitHub Issues**: (Add your repo URL)
2. **Email**: (Add support email)
3. **Documentation**: This README

---

## 📄 License

[Specify your license here]

---

## 🙏 Acknowledgments

- **CrewAI** - Multi-agent orchestration framework
- **Google Gemini** - Language model
- **Sarvam AI** - Indian language speech processing
- **Anthropic Claude** - Documentation assistance

---

## 🎓 FAER Scholar Award

This project is submitted as part of the FAER Scholar Awards program.

**Project Title:** CareMate - An Agentic AI-Powered Hospital Assistant for Patient-Centered Care

**Institution:** [Your Institution]  
**Student:** [Your Name]  
**Advisor:** [Advisor Name]

---

**Version:** 1.0.0  
**Last Updated:** February 5, 2025  
**Status:** ✅ Production Ready (Phase 1)
