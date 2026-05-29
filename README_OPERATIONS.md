# CareMate AI Hospital System — Operations Guide

## Overview

CareMate is a voice-first, multilingual AI hospital coordination system. It connects patients, doctors, nurses, nutritionists, utility staff, and administrators through real-time voice, AI routing, and emergency-grade alerts.

---

## System Architecture

```
Patient (Streamlit device)
        │ Voice / Text
        ▼
  FastAPI Backend (api.py)  ←──── WebSocket ────► Next.js Frontend (dashboards)
        │
        ├── Intent Router (SVM ML model)
        ├── Speech Layer (Sarvam AI STT/TTS)
        ├── AI Models (Meditron + OpenRouter/Nemotron)
        ├── IDP Pipeline (Amazon Textract + Medical Analyzer)
        └── MongoDB (caremate_db + caremate_interaction_db)
```

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |

---

## Environment Setup

### 1. Configure `.env` (root: `E:\FAER\CareMate\.env`)

```env
# MongoDB
MONGO_URI=mongodb+srv://...

# Sarvam AI (Speech)
SARVAM_API_KEY=sk_...

# OpenRouter (Nemotron)
OPENROUTER_API_KEY=sk-or-v1-...

# Meditron (SageMaker/ngrok)
SAGEMAKER_URL=https://your-ngrok-url.ngrok-free.dev

# AWS Textract (IDP)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-south-1

# Development mode (set false for production)
DEVELOPMENT_MODE=false
```

### 2. Install Python dependencies

```bash
cd E:\FAER\CareMate\Vfinal
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```bash
cd E:\FAER\CareMate\Vfinal-frontend
npm install
```

---

## Running the System

### Step 1 — Start the API Server

```bash
cd E:\FAER\CareMate\Vfinal
python api.py
```

Server starts at: `http://localhost:8000`

> The server takes ~30 seconds to load (downloads SentenceTransformer model on first run).

### Step 2 — Start the Frontend Dashboard

```bash
cd E:\FAER\CareMate\Vfinal-frontend
npm run dev
```

Dashboard opens at: `http://localhost:3000` (or `5173`)

### Step 3 — Start the Patient Device (Streamlit)

```bash
cd E:\FAER\CareMate\Vfinal
streamlit run patient_device.py
```

Patient device opens at: `http://localhost:8501`

---

## Staff Login Credentials

All passwords: `hospital123`

| Role | Email | Staff ID |
|------|-------|----------|
| Doctor | troy.stewart@hospital.com | 1006 |
| Doctor | paul.wood@hospital.com | 1008 |
| Nurse | michael.chan@hospital.com | 1001 |
| Nurse | krista.williams.md@hospital.com | 1009 |
| Nutritionist | monica.mcfarland@hospital.com | 1000 |
| Nutritionist | melissa.smith@hospital.com | 1003 |
| Utility | hannah.bailey@hospital.com | 1002 |
| Utility | matthew.preston@hospital.com | 1004 |

---

## Patient Test IDs

| Patient ID | Name | Room |
|------------|------|------|
| 183 | Richard Prince | R-125 |
| 175 | Sharon Duran | R-144 |
| 145 | Geoffrey King | R-106 |
| 130 | Diane (from blood report) | — |

---

## API Endpoints Reference

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Server health check |
| POST | `/auth/login` | Staff login |
| POST | `/chat` | Text message from patient |
| POST | `/voice` | Voice message from patient |

### Patient

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/patients/{id}` | Patient info |
| GET | `/patients/{id}/vitals` | Latest vitals |
| GET | `/patients/{id}/medications` | Medications |
| GET | `/patients/{id}/notes` | Clinical notes |
| GET | `/patients/{id}/history` | Full patient history (lab reports, analysis) |
| GET | `/patients/{id}/history/latest` | Most recent lab report analysis |
| GET | `/patients/{id}/lookup` | Quick name/room lookup |
| GET | `/patients/{id}/doctor-messages` | Unplayed doctor messages |

### Dashboards

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/doctor/queries` | Doctor-intent queries |
| GET | `/nurse/queries` | Nurse-intent queries |
| GET | `/nutrition/queries` | Nutrition-intent queries |
| GET | `/utility/queries` | Utility-intent queries |
| POST | `/doctor/voice-response` | Doctor sends voice to patient |
| POST | `/doctor/text-response` | Doctor sends text to patient |
| POST | `/nurse/upload-document` | Upload patient PDF (triggers IDP) |

### Staff

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/staff/directory` | All staff (filter by `?role=doctor`) |
| GET | `/staff/{id}/assignment` | Staff's assigned patients |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/metrics` | Hospital metrics |
| GET | `/admin/alerts` | Emergency alerts |
| GET | `/admin/users` | All staff users |
| GET | `/admin/activities` | Recent interactions |

---

## IDP Pipeline (Document Processing)

When a PDF is uploaded via `/nurse/upload-document`:

1. **Amazon Textract** extracts text (falls back to pypdf if AWS not configured)
2. **Patient ID** is extracted from the document (e.g. `PID: 130`) — overrides URL parameter
3. **Medical Parser** extracts: medications, diagnoses, vitals, lab results, allergies
4. **MongoDB** patient record is updated with extracted data
5. **Medical Analyzer** flags abnormal values against reference ranges
6. **AI Interpretation** generated via Meditron (or rule-based fallback)
7. **Patient History** entry created in `patient_history` collection
8. **WebSocket** broadcasts `DOCUMENT_PROCESSED` to all dashboards

---

## Intent Routing

Patient messages are classified into:

| Intent | Routed To | AI Handler |
|--------|-----------|------------|
| `emergency` | Doctor dashboard (instant) | Emergency alert |
| `doctor_query` | Doctor dashboard | Acknowledgement only |
| `status_query` | Doctor dashboard | Acknowledgement only |
| `general_conversation` | Patient device | Meditron |
| `nurse_request` | Nurse dashboard | OpenRouter confirmation |
| `nutrition_request` | Nutrition dashboard | OpenRouter confirmation |
| `utility_request` | Utility dashboard | OpenRouter confirmation |

---

## Retraining the Intent Classifier

When you need to improve intent classification accuracy or add new intents:

### Step 1: Add training samples

Edit `E:\FAER\CareMate\Vfinal\ml_model\caremate_big_dataset.csv`:

```csv
text,intent
"Doctor, I need help with my medication",doctor_query
"Can someone help me to the bathroom?",nurse_request
"I'd like to order lunch",nutrition_request
"The AC is not working",utility_request
"I'm having chest pain!",emergency
```

Add at least 50-100 samples per new intent for good accuracy.

### Step 2: Retrain the model

```bash
cd E:\FAER\CareMate\Vfinal\ml_model
python retrain_final.py
```

This will:
1. Load `caremate_big_dataset.csv` (~17,000 samples)
2. Generate SentenceTransformer embeddings
3. Train SVM classifier with cross-validation
4. Save model to `caremate_sentence_transformer_svm.pkl`
5. Print accuracy metrics

### Step 3: Restart the backend

```bash
cd E:\FAER\CareMate\Vfinal
python api.py
```

The new model is loaded automatically on startup.

### Step 4: Test classification

```bash
# Test via API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"183","message":"Doctor, I have a headache"}'
```

Check the `intent` field in the response.

---

## Testing Guide

### Unit Testing

#### Test intent classification
```python
# test_intent_router.py
from intent_router import IntentRouter

router = IntentRouter()

# Test doctor query
result = router.classify("Doctor, I need help")
assert result['intent'] == 'doctor_query'

# Test emergency
result = router.classify("I'm having chest pain!")
assert result['intent'] == 'emergency'

# Test nurse request
result = router.classify("Can someone help me to the bathroom?")
assert result['intent'] == 'nurse_request'
```

#### Test speech layer
```python
# test_speech_layer.py
from speech_layer import SpeechLayer

speech = SpeechLayer()

# Test TTS
audio_path = speech.tts("Hello, how can I help you?", language="en-IN")
assert audio_path.endswith('.mp3')
assert os.path.exists(audio_path)

# Test translation
translated = speech.translate("Hello", target_language="hi-IN")
assert translated is not None
```

### Integration Testing

#### Test voice pipeline end-to-end
```bash
# 1. Start backend
cd E:\FAER\CareMate\Vfinal
python api.py

# 2. Record test audio (or use existing file)
# 3. Send to API
curl -X POST http://localhost:8000/voice \
  -F "file=@test_audio.mp3" \
  -F "patient_id=183"

# 4. Verify response contains:
# - transcript
# - response_text
# - response_audio_url
# - intent
```

#### Test IDP pipeline
```bash
# 1. Upload test PDF
curl -X POST "http://localhost:8000/nurse/upload-document?patient_id=130" \
  -F "file=@test_blood_report.pdf"

# 2. Wait for processing (check logs)
# 3. Verify patient history
curl http://localhost:8000/patients/130/history/latest

# 4. Check for:
# - lab_results extracted
# - abnormal_flags identified
# - ai_interpretation generated
```

#### Test WebSocket events
```javascript
// test_websocket.js
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8000/ws');

ws.on('open', () => {
  console.log('Connected to WebSocket');
});

ws.on('message', (data) => {
  const event = JSON.parse(data);
  console.log('Received event:', event.type);
  console.log('Data:', event.data);
});

// Send test message via API to trigger event
// curl -X POST http://localhost:8000/chat ...
```

### Load Testing

#### Test concurrent voice requests
```bash
# Install Apache Bench
# Windows: Download from Apache website
# Linux: sudo apt-get install apache2-utils
# Mac: brew install ab

# Test 100 requests, 10 concurrent
ab -n 100 -c 10 -p test_payload.json -T application/json \
  http://localhost:8000/chat
```

#### Test WebSocket scalability
```python
# test_websocket_load.py
import asyncio
import websockets

async def connect_client(client_id):
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        print(f"Client {client_id} connected")
        # Keep connection open
        await asyncio.sleep(60)

async def main():
    # Connect 50 concurrent clients
    tasks = [connect_client(i) for i in range(50)]
    await asyncio.gather(*tasks)

asyncio.run(main())
```

### Manual Testing Checklist

#### Voice Pipeline
- [ ] Record voice in English - verify transcription
- [ ] Record voice in Hindi - verify transcription and translation
- [ ] Record voice in Tamil - verify transcription and translation
- [ ] Test emergency keyword detection
- [ ] Test "Doctor," prefix override
- [ ] Verify TTS audio plays correctly
- [ ] Test timeout handling (60s limit)

#### Dashboard Functionality
- [ ] Login as doctor - see only assigned patients
- [ ] Login as nurse - see only assigned patients
- [ ] Login as nutritionist - see all nutrition requests
- [ ] Login as utility - see all maintenance requests
- [ ] Login as admin - see all metrics
- [ ] Verify WebSocket real-time updates
- [ ] Test emergency alert overlay
- [ ] Test doctor voice response
- [ ] Test PDF upload and IDP processing

#### Patient Device
- [ ] Select patient from dropdown
- [ ] Record voice message
- [ ] Verify response audio plays
- [ ] Test text input fallback
- [ ] Check doctor message polling
- [ ] Verify patient name displays correctly

#### IDP Pipeline
- [ ] Upload blood test report - verify lab results extracted
- [ ] Upload MRI scan - verify text extraction
- [ ] Upload X-ray report - verify processing
- [ ] Test patient ID extraction from document
- [ ] Verify abnormal flags identified
- [ ] Check AI interpretation generated
- [ ] Verify patient history updated

#### Error Handling
- [ ] Test with invalid audio file
- [ ] Test with corrupted PDF
- [ ] Test with missing patient ID
- [ ] Test with invalid staff credentials
- [ ] Test with network timeout
- [ ] Verify graceful degradation (Meditron → OpenRouter)
- [ ] Verify fallback (Textract → pypdf)

---

## Supported Languages (Sarvam AI)

| Language | Code | TTS Voice | Status |
|----------|------|-----------|--------|
| English | en-IN | gokul | ✅ Fully supported |
| Hindi | hi-IN | gokul | ✅ Fully supported |
| Bengali | bn-IN | ritu | ✅ Fully supported |
| Gujarati | gu-IN | anushka | ✅ Fully supported |
| Kannada | kn-IN | vidya | ✅ Fully supported |
| Malayalam | ml-IN | priya | ✅ Fully supported |
| Marathi | mr-IN | manisha | ✅ Fully supported |
| Odia | od-IN | neha | ✅ Fully supported |
| Punjabi | pa-IN | simran | ✅ Fully supported |
| Tamil | ta-IN | kavitha | ✅ Fully supported |
| Telugu | te-IN | shreya | ✅ Fully supported |

### Language Detection
- Automatic detection via Sarvam `transcribe` API
- Parallel processing: `translate` (→ English) + `transcribe` (→ native)
- Fallback to English if detection fails

---

## Common Workflows

### Workflow 1: Patient Voice Request

1. **Patient speaks** (e.g., "Doctor, I have a headache")
2. **Patient device** records audio and sends to `/voice` endpoint
3. **Backend** processes:
   - Parallel STT: translate + transcribe
   - Intent classification (SVM)
   - AI response generation (Meditron/OpenRouter)
   - Translation back to patient's language
   - TTS audio generation
4. **WebSocket** broadcasts `NEW_REQUEST` to all dashboards
5. **Doctor dashboard** shows new query in queue
6. **Patient device** plays audio response

**Timeline**: ~8-10 seconds end-to-end

### Workflow 2: Doctor Voice Response

1. **Doctor** clicks patient query in dashboard
2. **Doctor** records voice response
3. **Frontend** sends audio to `/doctor/voice-response`
4. **Backend** saves audio file and creates database entry
5. **Patient device** polls `/patients/{id}/doctor-messages`
6. **Patient device** plays doctor's voice message

**Timeline**: ~2-3 seconds

### Workflow 3: Document Upload and IDP

1. **Nurse** uploads PDF via dashboard
2. **Frontend** sends to `/nurse/upload-document`
3. **Backend** returns immediate success (non-blocking)
4. **IDP pipeline** runs in background:
   - Amazon Textract OCR (or pypdf fallback)
   - Patient ID extraction from document
   - Medical data parsing (labs, vitals, medications)
   - Abnormal value detection
   - AI interpretation generation
   - Patient history entry creation
5. **WebSocket** broadcasts `DOCUMENT_PROCESSED` event
6. **All dashboards** receive update notification
7. **Doctor** views patient history with new analysis

**Timeline**: 10-30 seconds for IDP processing

### Workflow 4: Emergency Alert

1. **Patient** says "I'm having chest pain!"
2. **Intent router** classifies as `emergency`
3. **Backend** immediately:
   - Logs emergency interaction
   - Broadcasts `EMERGENCY_ALERT` via WebSocket
4. **All doctor dashboards** show full-screen alert overlay
5. **Doctor** acknowledges and responds
6. **System** logs emergency response time

**Timeline**: <2 seconds for alert

### Workflow 5: Staff Assignment

1. **Admin** adds new doctor to `staff_directory`
2. **Admin** creates assignment in `staff_assignments`:
   ```javascript
   {
     staff_id: "1010",
     role: "doctor",
     patient_ids: ["183", "175", "145"]
   }
   ```
3. **Doctor** logs in to dashboard
4. **Dashboard** queries `/doctor/queries?staff_id=1010`
5. **Backend** filters queries to assigned patients only
6. **Doctor** sees only their patients' queries

### Workflow 6: Multilingual Interaction

1. **Patient** speaks in Tamil: "எனக்கு தலைவலி இருக்கிறது"
2. **Sarvam STT** parallel processing:
   - `translate`: "I have a headache" (English)
   - `transcribe`: "எனக்கு தலைவலி இருக்கிறது" (Tamil)
3. **Intent router** processes English translation
4. **AI** generates English response: "I understand you have a headache..."
5. **Translation** converts to Tamil: "உங்களுக்கு தலைவலி இருப்பதை நான் புரிந்துகொள்கிறேன்..."
6. **TTS** generates Tamil audio with `kavitha` voice
7. **Patient** hears response in Tamil

**Timeline**: ~10-12 seconds

### Workflow 7: Nutrition Request

1. **Patient** says "I'd like to order lunch"
2. **Intent router** classifies as `nutrition_request`
3. **Backend**:
   - Logs interaction
   - Generates confirmation via OpenRouter
   - Broadcasts to nutrition dashboard
4. **Nutritionist** sees request in queue
5. **Nutritionist** checks patient allergies and restrictions
6. **Nutritionist** prepares meal plan
7. **Nutritionist** marks request as completed

### Workflow 8: Maintenance Request

1. **Patient** says "The AC is not working"
2. **Intent router** classifies as `utility_request`
3. **Backend** logs and broadcasts to utility dashboard
4. **Utility staff** sees request with room number
5. **Utility staff** dispatches technician
6. **Utility staff** marks as in-progress, then completed

---

## WebSocket Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `NEW_REQUEST` | Patient sends message | patient_id, room, intent, message |
| `EMERGENCY_ALERT` | Emergency intent detected | patient_id, room, reason |
| `PROCESSING_STARTED` | Voice processing begins | patient_id, status |
| `DOCUMENT_PROCESSED` | IDP pipeline complete | patient_id, abnormal_flags, ai_interpretation |

---

## Troubleshooting

### Backend Issues

#### Port 8000 already in use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

#### ChromaDB panic error
```bash
# Windows
Remove-Item -Recurse -Force Vfinal\chroma_db

# Linux/Mac
rm -rf Vfinal/chroma_db
```
Then restart the server — ChromaDB will rebuild automatically.

#### Meditron timeout
The Meditron model runs on SageMaker via ngrok. If the ngrok tunnel expires, update `SAGEMAKER_URL` in `.env` with the new URL. The system automatically falls back to OpenRouter if Meditron is unavailable.

#### AWS Textract not working
Verify credentials in `.env`. The system automatically falls back to pypdf if AWS credentials are missing or invalid.

#### SentenceTransformer model download fails
- Check internet connection
- Model downloads automatically on first run (~80MB)
- Cached in `~/.cache/torch/sentence_transformers/`
- Manual download: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

#### MongoDB connection errors
- Verify `MONGO_URI` in `.env`
- Check MongoDB Atlas IP whitelist (allow 0.0.0.0/0 for development)
- Ensure database user has read/write permissions
- Test connection: `mongosh "your_connection_string"`

### Frontend Issues

#### Port 3000/5173 already in use
```bash
npx kill-port 3000
# or
npx kill-port 5173
```

#### WebSocket connection failed
- Ensure backend is running on port 8000
- Check browser console for errors
- Verify CORS settings in `api.py`
- Test WebSocket: `wscat -c ws://localhost:8000/ws`

#### Dashboard shows no data
- Check staff_id in browser localStorage
- Verify staff has assigned patients in `staff_assignments` collection
- Check browser console for API errors
- Verify backend is returning data: `curl http://localhost:8000/doctor/queries`

#### Login fails with valid credentials
- Check `staff_directory` collection has the user
- Verify password matches exactly (case-sensitive)
- Check browser console for API errors
- Test login endpoint: `curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"troy.stewart@hospital.com","password":"hospital123"}'`

### Patient Device Issues

#### Streamlit port 8501 in use
```bash
streamlit run patient_device.py --server.port 8502
```

#### Audio recording not working
- Check browser microphone permissions
- Try alternative interface: `streamlit run chat_interface.py`
- Verify `st-audiorec` package installed: `pip show st-audiorec`
- Test with text input first

#### Patient name shows "Unknown"
- Verify patient_id exists in `patient_lookup` collection
- Check MongoDB connection
- Add patient to lookup:
  ```javascript
  db.patient_lookup.insertOne({
    patient_id: "183",
    name: "Richard Prince",
    room_id: "R-125",
    doctor_id: "1006",
    nurse_id: "1001"
  })
  ```

#### Voice processing takes too long
- Check Sarvam API key is valid
- Verify internet connection
- Check backend logs for timeout errors
- System has 60s timeout with automatic fallback

### IDP Pipeline Issues

#### Document upload fails
- Check file size (max 10MB recommended)
- Verify PDF is not corrupted
- Check `patient_reports/` directory exists and is writable
- Review backend logs for errors

#### IDP processing stuck
- Check AWS credentials if using Textract
- System falls back to pypdf automatically
- Check backend logs for IDP errors
- Verify MongoDB write permissions

#### Lab results not extracted
- Ensure PDF contains text (not just images)
- Check document format matches expected structure
- Review `medical_analyzer.py` parsing logic
- Test with sample blood test report

---

## Advanced Operations

### Database Management

#### View all collections
```javascript
// Connect to MongoDB
mongosh "your_connection_string"

// List collections
show collections

// Count documents
db.patients.countDocuments()
db.interactions.countDocuments()
```

#### Add new staff member
```javascript
db.staff_directory.insertOne({
  staff_id: "1010",
  name: "Dr. Jane Smith",
  email: "jane.smith@hospital.com",
  password: "hospital123",
  role: "doctor",
  shift: "day",
  department: "cardiology"
})

// Assign patients
db.staff_assignments.insertOne({
  staff_id: "1010",
  role: "doctor",
  patient_ids: ["183", "175", "145"],
  assigned_at: new Date()
})
```

#### Add new patient
```javascript
// Add to patients collection
db.patients.insertOne({
  patient_id: "200",
  name: "John Doe",
  dob: "1980-05-15",
  blood_type: "O+",
  allergies: ["Penicillin"],
  medications: ["Aspirin 100mg daily"],
  chronic_conditions: ["Hypertension"]
})

// Add to patient_lookup
db.patient_lookup.insertOne({
  patient_id: "200",
  name: "John Doe",
  room_id: "R-150",
  doctor_id: "1006",
  nurse_id: "1001"
})

// Create active visit
db.visits.insertOne({
  visit_id: "V-200",
  patient_id: "200",
  room_id: "R-150",
  bed_id: "B-150-1",
  doctor_id: "1006",
  nurse_id: "1001",
  status: "ACTIVE",
  admission_date: new Date(),
  vitals: {
    temperature: 98.6,
    blood_pressure: "120/80",
    heart_rate: 72,
    respiratory_rate: 16,
    oxygen_saturation: 98
  }
})
```

### Performance Monitoring

#### Check API response times
```bash
# Test health endpoint
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# curl-format.txt:
time_namelookup:  %{time_namelookup}\n
time_connect:  %{time_connect}\n
time_starttransfer:  %{time_starttransfer}\n
time_total:  %{time_total}\n
```

#### Monitor WebSocket connections
Check backend logs for:
```
New Dashboard Connected. Total: X
Dashboard Disconnected. Total: X
Broadcasting to X dashboards: EVENT_TYPE
```

#### Check cache effectiveness
```bash
# View cache files
ls -lh Vfinal/cache/

# Clear cache
rm -rf Vfinal/cache/*.json
```

### Log Analysis

#### View real-time logs
```bash
# Backend
cd E:\FAER\CareMate\Vfinal
python api.py | tee backend.log

# Frontend
cd E:\FAER\CareMate\Vfinal-frontend
npm run dev | tee frontend.log
```

#### Search logs for errors
```bash
# Windows
findstr /i "error" backend.log

# Linux/Mac
grep -i "error" backend.log
```

#### Common log patterns
- `Voice processing result:` - Voice pipeline completion
- `IDP result for patient` - Document processing completion
- `Broadcasting to X dashboards` - WebSocket events
- `Intent classified:` - Intent router results

### Backup and Restore

#### Backup MongoDB
```bash
# Backup all databases
mongodump --uri="your_connection_string" --out=backup_$(date +%Y%m%d)

# Backup specific database
mongodump --uri="your_connection_string" --db=caremate_db --out=backup_caremate
```

#### Restore MongoDB
```bash
mongorestore --uri="your_connection_string" --dir=backup_20260529
```

#### Backup audio files
```bash
# Windows
xcopy /E /I Vfinal\generated_audio backup\audio

# Linux/Mac
cp -r Vfinal/generated_audio backup/audio
```

#### Backup patient reports
```bash
# Windows
xcopy /E /I Vfinal\patient_reports backup\reports

# Linux/Mac
cp -r Vfinal/patient_reports backup/reports
```

---

## Production Deployment

### Pre-deployment Checklist

- [ ] Replace password auth with JWT tokens
- [ ] Move audio/PDF storage to S3 or cloud storage
- [ ] Set up Redis for distributed caching
- [ ] Configure production MongoDB with replica set
- [ ] Enable HTTPS with SSL certificate
- [ ] Set up monitoring (Sentry, DataDog, CloudWatch)
- [ ] Configure automated backups
- [ ] Add rate limiting (e.g., slowapi)
- [ ] Set up CI/CD pipeline
- [ ] Configure environment-specific .env files
- [ ] Enable logging to external service (e.g., Papertrail)
- [ ] Set up health check monitoring
- [ ] Configure auto-scaling
- [ ] Test disaster recovery procedures
- [ ] Update CORS to specific origins
- [ ] Enable request validation and sanitization
- [ ] Set up API gateway (optional)
- [ ] Configure CDN for static assets

### Environment Variables for Production

```env
# Production MongoDB with replica set
MONGO_URI=mongodb+srv://prod_user:password@prod-cluster.mongodb.net/?retryWrites=true&w=majority
FRONTEND_MONGO_URI=mongodb+srv://prod_user:password@prod-cluster.mongodb.net/?retryWrites=true&w=majority

# Production API keys
SARVAM_API_KEY=sk_prod_...
OPENROUTER_API_KEY=sk-or-v1-prod-...
SAGEMAKER_URL=https://prod-meditron.example.com

# AWS Production
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-south-1

# S3 Storage
S3_BUCKET_AUDIO=caremate-prod-audio
S3_BUCKET_REPORTS=caremate-prod-reports

# Redis Cache
REDIS_URL=redis://prod-redis.example.com:6379

# Security
JWT_SECRET=your_secure_random_secret
CORS_ORIGINS=https://caremate.example.com,https://app.caremate.example.com

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
LOG_LEVEL=INFO

# Production mode
DEVELOPMENT_MODE=false
```

### Deployment Steps

1. **Set up cloud infrastructure**
   - Provision servers (AWS EC2, Google Cloud, Azure)
   - Configure load balancer
   - Set up MongoDB Atlas production cluster
   - Create S3 buckets for storage
   - Set up Redis instance

2. **Deploy backend**
   ```bash
   # Build and deploy
   cd Vfinal
   pip install -r requirements.txt
   gunicorn api:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

3. **Deploy frontend**
   ```bash
   # Build for production
   cd Vfinal-frontend
   npm run build
   
   # Deploy to hosting (Vercel, Netlify, Cloudflare Pages)
   # or serve with nginx
   ```

4. **Configure reverse proxy (nginx)**
   ```nginx
   server {
       listen 80;
       server_name caremate.example.com;
       
       location / {
           proxy_pass http://localhost:3000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
       
       location /api {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
       }
       
       location /ws {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "Upgrade";
       }
   }
   ```

5. **Set up monitoring**
   - Configure Sentry for error tracking
   - Set up uptime monitoring (UptimeRobot, Pingdom)
   - Configure log aggregation (Papertrail, Loggly)
   - Set up performance monitoring (DataDog, New Relic)

6. **Configure automated backups**
   - MongoDB Atlas automated backups
   - S3 versioning and lifecycle policies
   - Database backup scripts with cron jobs

7. **Test production deployment**
   - Run full end-to-end tests
   - Load testing with realistic traffic
   - Disaster recovery drill
   - Security audit

---

## Maintenance Tasks

### Daily
- [ ] Check error logs for critical issues
- [ ] Monitor API response times
- [ ] Verify WebSocket connections are stable
- [ ] Check disk space for audio/PDF storage

### Weekly
- [ ] Review emergency alert patterns
- [ ] Analyze intent classification accuracy
- [ ] Check database query performance
- [ ] Review staff assignment distribution

### Monthly
- [ ] Retrain intent classifier with new samples
- [ ] Update dependencies (security patches)
- [ ] Review and archive old audio files
- [ ] Optimize database indexes
- [ ] Review and update documentation

### Quarterly
- [ ] Full system backup and restore test
- [ ] Security audit and penetration testing
- [ ] Performance optimization review
- [ ] User feedback analysis and feature planning

---

## Support and Contact

For technical support, bug reports, or feature requests:

- **Email**: support@caremate.example.com
- **Documentation**: https://docs.caremate.example.com
- **Issue Tracker**: https://github.com/your-org/caremate/issues

---

## Appendix

### Useful Commands

```bash
# Check Python version
python --version

# Check Node version
node --version

# Check MongoDB connection
mongosh "your_connection_string" --eval "db.adminCommand('ping')"

# Check API health
curl http://localhost:8000/health

# Check frontend build
cd Vfinal-frontend && npm run build

# Run tests (if available)
cd Vfinal && pytest
cd Vfinal-frontend && npm test

# Check disk space
df -h  # Linux/Mac
wmic logicaldisk get size,freespace,caption  # Windows

# Monitor system resources
top  # Linux/Mac
taskmgr  # Windows
```

### Quick Reference

| Component | Port | URL |
|-----------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| Frontend | 3000/5173 | http://localhost:3000 |
| Patient Device | 8501 | http://localhost:8501 |
| Chat Interface | 8501 | http://localhost:8501 |
| MongoDB Atlas | 27017 | mongodb+srv://... |

### File Locations

| Item | Path |
|------|------|
| Environment config | `E:\FAER\CareMate\.env` |
| Backend code | `E:\FAER\CareMate\Vfinal\` |
| Frontend code | `E:\FAER\CareMate\Vfinal-frontend\` |
| Audio files | `E:\FAER\CareMate\Vfinal\generated_audio\` |
| Patient reports | `E:\FAER\CareMate\Vfinal\patient_reports\` |
| ML model | `E:\FAER\CareMate\Vfinal\ml_model\caremate_sentence_transformer_svm.pkl` |
| Training data | `E:\FAER\CareMate\Vfinal\ml_model\caremate_big_dataset.csv` |
| ChromaDB | `E:\FAER\CareMate\Vfinal\chroma_db\` |
| Cache | `E:\FAER\CareMate\Vfinal\cache\` |
