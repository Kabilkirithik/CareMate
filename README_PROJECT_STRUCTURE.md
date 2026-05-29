# CareMate — Project Structure Reference

## Root: `E:\FAER\CareMate\`

```
E:\FAER\CareMate\
├── .env                          # All API keys and configuration
├── .gitignore
├── README_OPERATIONS.md          # How to run the system
├── README_PROJECT_STRUCTURE.md   # This file
├── Vfinal/                       # Backend (Python / FastAPI)
└── Vfinal-frontend/              # Frontend (React / TanStack)
```

---

## `Vfinal/` — Backend

### Core Application Files

| File | Purpose |
|------|---------|
| `api.py` | **Main FastAPI server.** All HTTP endpoints, WebSocket manager, dual MongoDB setup. Entry point: `python api.py` |
| `main.py` | **CareMateBackend class.** Orchestrates voice processing pipeline: STT → intent → AI → translate → TTS. Async with thread pool. |
| `speech_layer.py` | **Sarvam AI integration.** Parallel STT (translate + transcribe), translation, TTS with speaker mapping for 11 languages. Includes response caching. |
| `intent_router.py` | **Intent classifier.** Loads SVM model from `ml_model/`. Classifies patient messages into 7 intents. Includes keyword override for doctor-addressed messages. |
| `hospital_tools.py` | **AI tool implementations.** PatientContextTool, MedicalRAGTool, SummaryContextTool, WorkflowActionTool — used by the AI agents. |
| `meditron_client.py` | **Meditron LLM client.** Connects to SageMaker/ngrok endpoint. 25s timeout with smart fallback responses. |
| `openrouter_client.py` | **OpenRouter/Nemotron client.** Used for workflow confirmations and medical analysis fallback. |
| `performance_optimizer.py` | **Caching layer.** Response cache, translation cache, TTS cache, instant response shortcuts for common queries. |

### IDP Pipeline Files

| File | Purpose |
|------|---------|
| `idp_pipeline.py` | **Full IDP pipeline.** Textract OCR → parse → patient ID extraction → MongoDB update → ChromaDB index. Auto-detects patient ID from document. Falls back to pypdf if AWS not configured. |
| `medical_analyzer.py` | **Medical analysis layer.** Flags abnormal lab values against reference ranges, generates AI clinical interpretation, stores structured patient history entry in MongoDB. |
| `rag_pipeline.py` | **ChromaDB RAG.** Indexes patient reports for semantic search. Used by MedicalRAGTool. Gracefully handles ChromaDB unavailability. |

### Patient Interface Files

| File | Purpose |
|------|---------|
| `patient_device.py` | **Streamlit patient device.** Bedside interface for recording voice, receiving doctor messages. Auto-looks up patient name from API. |
| `chat_interface.py` | **Streamlit chat interface.** Alternative patient interface with dropdown patient selection and doctor message polling. |

### Configuration & Data

| File/Folder | Purpose |
|-------------|---------|
| `requirements.txt` | Python dependencies |
| `README.md` | Backend-specific notes |
| `ml_model/` | Intent classifier model and training data |
| `patient_reports/` | Uploaded PDFs stored here |
| `generated_audio/` | TTS audio files served via `/audio/` endpoint |
| `chroma_db/` | ChromaDB persistent storage (auto-created) |
| `cache/` | Response/translation/TTS cache files (auto-created) |
| `rag/` | RAG-related files |

### `ml_model/` — Intent Classifier

| File | Purpose |
|------|---------|
| `caremate_sentence_transformer_svm.pkl` | **Trained SVM model** — loaded by intent_router.py at startup |
| `caremate_big_dataset.csv` | **Training dataset** — 17,000+ labeled samples across 7 intents |
| `retrain_final.py` | **Retrain script** — run this to retrain the model after adding new samples |
| `fix_intent_boundaries.py` | Script used to correct intent boundaries in training data |
| `add_medical_knowledge_samples.py` | Script used to add medical knowledge samples |
| `caremate_intent_dataset_cleaned.csv` | Older small dataset (1,000 samples) — not used for training |
| `caremate_big_dataset_short.csv` | Subset of big dataset |
| `retrain_v3.py`, `retrain_v4.py`, `retrain_v5.py` | Older retrain scripts (superseded by retrain_final.py) |

---

## `Vfinal-frontend/` — Frontend

### `src/routes/` — Page Components

| File | Route | Role |
|------|-------|------|
| `index.tsx` | `/` | Landing page with hero, features, workflow sections |
| `login.tsx` | `/login` | Staff login with role selection |
| `doctor.tsx` | `/doctor` | Doctor dashboard: query queue, voice console, patient summary |
| `nurse.tsx` | `/nurse` | Nurse dashboard: request queue (kanban), OCR upload |
| `nutrition.tsx` | `/nutrition` | Nutritionist dashboard: meal requests, patient diet plans |
| `utility.tsx` | `/utility` | Utility dashboard: maintenance requests queue |
| `admin.tsx` | `/admin` | Admin dashboard: metrics, alerts, user management |
| `__root.tsx` | — | Root layout with Sonner toasts |

### `src/lib/` — Utilities

| File | Purpose |
|------|---------|
| `api.ts` | **API client class.** All HTTP calls to the backend. Includes `getCurrentUser()` for staff_id filtering. |
| `websocket.ts` | **WebSocket client.** Connects to `/ws`, handles reconnection, event emitter pattern. |
| `roles.ts` | Role definitions and routing paths |
| `session.ts` | localStorage helpers for role persistence |
| `error-page.ts` | Error page utility |

### `src/components/` — Shared Components

| Component | Purpose |
|-----------|---------|
| `dashboard/DashboardShell.tsx` | Sidebar + header wrapper for all dashboards |
| `dashboard/EmergencyAlert.tsx` | Full-screen emergency alert overlay |
| `dashboard/VoiceWave.tsx` | Animated voice waveform visualization |
| `dashboard/OcrUpload.tsx` | PDF upload component (nurse/admin) |
| `dashboard/StaffAssignment.tsx` | Shows staff's assigned patients list |
| `Reveal.tsx` | Scroll-triggered animation + KineticText letter animation |

### `src/hooks/`

| File | Purpose |
|------|---------|
| `useReveal.ts` | IntersectionObserver hook for scroll animations |

### Root Config Files

| File | Purpose |
|------|---------|
| `src/styles.css` | Global CSS: color palette, animations, kinetic text, marquee |
| `src/router.tsx` | TanStack Router setup |
| `src/routeTree.gen.ts` | Auto-generated route tree (do not edit manually) |
| `src/server.ts` | SSR server entry |
| `src/start.ts` | Client entry point |
| `package.json` | Node dependencies |
| `vite.config.ts` | Vite build configuration |
| `tailwind.config.js` | Tailwind CSS configuration |
| `tsconfig.json` | TypeScript configuration |

---

## MongoDB Collections

### `caremate_db` (Core Hospital Data)

| Collection | Contents | Key Fields |
|------------|---------|------------|
| `patients` | Patient demographics, allergies, chronic conditions, medications | patient_id, name, dob, blood_type, allergies, medications, chronic_conditions |
| `visits` | Active/discharged visits with room, bed, assigned doctor/nurse, vitals | visit_id, patient_id, room_id, bed_id, doctor_id, nurse_id, status, vitals, admission_date |
| `rooms` | Room metadata | room_id, floor, wing, capacity, status |
| `beds` | Bed occupancy | bed_id, room_id, patient_id, status |
| `devices` | Bedside device registry | device_id, patient_id, room_id, status, last_active |
| `requests` | Workflow requests (nurse/nutrition/utility/emergency) | request_id, patient_id, request_type, status, priority, created_at |
| `documents` | Uploaded document metadata + IDP processing status + lab results | document_id, patient_id, file_path, status, lab_results, uploaded_at, idp_processed_at |
| `summaries` | Clinical summaries from IDP analysis | summary_id, patient_id, summary_text, created_at |
| `patient_history` | Full structured history entries from IDP pipeline | history_id, patient_id, document_type, lab_results, abnormal_flags, ai_interpretation, created_at |
| `visit_events` | Audit log of all events | event_id, visit_id, event_type, timestamp, details |

### `caremate_interaction_db` (Frontend/Interaction Data)

| Collection | Contents | Key Fields |
|------------|---------|------------|
| `interactions` | All patient interactions with intent classification | interaction_id, patient_id, patient_name, room_id, type (TEXT/VOICE), message, transcript, intent, timestamp |
| `patient_lookup` | Fast lookup: patient_id → name, room, doctor_id, nurse_id | patient_id, name, room_id, doctor_id, nurse_id |
| `staff_directory` | Staff credentials (email, password, role, shift) | staff_id, name, email, password, role, shift, department |
| `staff_assignments` | Staff → assigned patient IDs mapping | staff_id, role, patient_ids (array), assigned_at |
| `doctor_messages` | Voice/text messages from doctors to patients | message_id, patient_id, audio_url, text, sent_at, played, file_size |

---

## Data Flow Summary

```
Patient speaks (Tamil)
    │
    ▼
Sarvam STT (parallel: translate + transcribe)
    │
    ├── English text → Intent Router (SVM)
    └── Native text → Language detection
                │
                ▼
        Intent classified
                │
    ┌───────────┼───────────────────┐
    │           │                   │
emergency  general_conv      nurse/nutrition/
    │       (Meditron)        utility/doctor
    │           │                   │
    ▼           ▼                   ▼
Alert sent  AI response      Workflow logged
    │           │            + Confirmation
    └───────────┴───────────────────┘
                │
                ▼
        Translate back (Sarvam)
                │
                ▼
        TTS audio (Sarvam Bulbul:v3)
                │
                ▼
        Response to patient + WebSocket to dashboards
```

---

## Key Design Decisions

- **Parallel STT**: translate + transcribe run simultaneously, halving STT latency
- **Intent override**: Messages starting with "Doctor," are always `doctor_query` regardless of SVM
- **Patient ID from document**: IDP extracts PID from PDF (e.g. `PID: 130`) and overrides URL parameter
- **Non-blocking IDP**: Document upload returns 200 immediately; IDP runs as async background task
- **Graceful degradation**: ChromaDB failure → RAG skipped; Textract failure → pypdf fallback; Meditron timeout → keyword fallback
- **Dual MongoDB**: Core hospital data in `caremate_db`, interaction/frontend data in `caremate_interaction_db`
- **Audio validation**: File size checks prevent empty/corrupt uploads
- **Timeout protection**: 60s voice processing timeout with fallback response
- **WebSocket broadcasting**: All dashboards receive real-time updates simultaneously

---

## API Endpoint Categories

### Authentication
- `POST /auth/login` - Staff login with email/password
- `POST /auth/logout` - Logout (clears session)

### Patient Communication
- `POST /chat` - Text message from patient
- `POST /voice` - Voice message from patient (multipart/form-data)

### Patient Data
- `GET /patients/{id}` - Full patient record with active visit
- `GET /patients/{id}/vitals` - Latest vital signs
- `GET /patients/{id}/medications` - Current medications
- `GET /patients/{id}/notes` - Clinical notes and summaries
- `GET /patients/{id}/history` - Lab reports and analysis (last 20)
- `GET /patients/{id}/history/latest` - Most recent lab analysis
- `GET /patients/{id}/lookup` - Quick name/room lookup
- `GET /patients/{id}/doctor-messages` - Unplayed doctor voice messages
- `GET /patients/{id}/document-status` - IDP processing status

### Doctor Dashboard
- `GET /doctor/queries?staff_id={id}` - Queries for assigned patients only
- `POST /doctor/voice-response` - Send voice message to patient
- `POST /doctor/text-response` - Send text message to patient

### Nurse Dashboard
- `GET /nurse/queries?staff_id={id}` - Nurse requests for assigned patients
- `POST /nurse/upload-document` - Upload PDF (triggers IDP pipeline)
- `GET /nurse/documents` - All uploaded documents
- `GET /nurse/assignments` - Active patient assignments

### Nutrition Dashboard
- `GET /nutrition/queries?staff_id={id}` - Nutrition requests
- `GET /nutrition/plans` - Patient diet plans with allergies
- `GET /nutrition/meals` - Meal request queue
- `GET /nutrition/alerts` - Allergy alerts

### Utility Dashboard
- `GET /utility/queries?staff_id={id}` - Maintenance requests
- `GET /utility/maintenance` - Maintenance queue
- `GET /utility/systems` - System status overview

### Admin Dashboard
- `GET /admin/metrics` - Hospital-wide metrics
- `GET /admin/alerts` - Emergency alert history
- `GET /admin/users` - All staff users
- `GET /admin/activities` - Recent interactions (last 20)

### Staff Management
- `GET /staff/directory?role={role}` - Staff directory (filter by role)
- `GET /staff/{id}/assignment` - Staff's assigned patients

### System
- `GET /health` - Server health check
- `GET /audio/{filename}` - Serve generated audio files
- `WebSocket /ws` - Real-time dashboard updates

---

## WebSocket Event Types

| Event Type | Trigger | Payload Fields |
|------------|---------|----------------|
| `NEW_REQUEST` | Patient sends message | patient_id, patient_name, room, intent, message, timestamp |
| `EMERGENCY_ALERT` | Emergency intent detected | patient_id, patient_name, room, reason, timestamp |
| `PROCESSING_STARTED` | Voice processing begins | patient_id, patient_name, room, message, status, timestamp |
| `PROCESSING_TIMEOUT` | Voice processing exceeds 60s | patient_id, patient_name, room, message, status, timestamp |
| `DOCUMENT_PROCESSED` | IDP pipeline completes | patient_id, patient_name, room, document_id, updated_fields, abnormal_flags, critical_count, ai_interpretation, history_id, status, timestamp |

---

## File Storage Structure

```
E:\FAER\CareMate\Vfinal\
├── generated_audio/          # TTS output and doctor voice messages
│   ├── resp_*.mp3            # Patient responses
│   ├── dr_*.mp3              # Doctor voice messages
│   └── *.mp3                 # Other audio files
│
├── patient_reports/          # Uploaded PDFs
│   ├── rep_*.pdf             # Nurse-uploaded reports
│   ├── blood_test_*.pdf      # Generated blood test reports
│   ├── lab_report_*.pdf      # Lab reports
│   ├── mri_scan_*.pdf        # MRI scans
│   ├── radiology_report_*.pdf # Radiology reports
│   └── x_ray_*.pdf           # X-ray reports
│
├── chroma_db/                # ChromaDB vector database
│   └── chroma.sqlite3        # Persistent storage
│
└── cache/                    # Performance cache (auto-created)
    ├── response_cache.json
    ├── translation_cache.json
    └── tts_cache.json
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGO_URI` | Yes | - | MongoDB connection string for core hospital data |
| `FRONTEND_MONGO_URI` | No | Uses MONGO_URI | MongoDB for interaction/staff data |
| `SARVAM_API_KEY` | Yes | - | Sarvam AI API key for STT/TTS/Translation |
| `OPENROUTER_API_KEY` | Yes | - | OpenRouter API key for Nemotron LLM |
| `SAGEMAKER_URL` | No | - | Meditron endpoint (falls back to OpenRouter) |
| `AWS_ACCESS_KEY_ID` | No | - | AWS credentials for Textract |
| `AWS_SECRET_ACCESS_KEY` | No | - | AWS secret key |
| `AWS_REGION` | No | ap-south-1 | AWS region for Textract |
| `DEVELOPMENT_MODE` | No | false | Enable development features |

---

## Troubleshooting Guide

### Backend Issues

**Port 8000 already in use**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

**ChromaDB panic error**
```bash
# Windows
Remove-Item -Recurse -Force Vfinal\chroma_db

# Linux/Mac
rm -rf Vfinal/chroma_db
```
Restart server — ChromaDB rebuilds automatically.

**SentenceTransformer download fails**
- Check internet connection
- Manually download model: `sentence-transformers/all-MiniLM-L6-v2`
- Place in `~/.cache/torch/sentence_transformers/`

**Meditron timeout**
- Update `SAGEMAKER_URL` in `.env` with fresh ngrok URL
- System automatically falls back to OpenRouter

**AWS Textract not working**
- Verify credentials in `.env`
- Check AWS region is `ap-south-1`
- System falls back to pypdf automatically

### Frontend Issues

**Port 3000/5173 already in use**
```bash
# Kill process on port
npx kill-port 3000
```

**WebSocket connection failed**
- Ensure backend is running on port 8000
- Check CORS settings in `api.py`
- Verify no firewall blocking WebSocket

**Dashboard shows no data**
- Check staff_id in localStorage
- Verify staff has assigned patients in `staff_assignments` collection
- Check browser console for API errors

### Patient Device Issues

**Streamlit port 8501 in use**
```bash
streamlit run patient_device.py --server.port 8502
```

**Audio recording not working**
- Check browser microphone permissions
- Try alternative: `streamlit run chat_interface.py`
- Verify `st-audiorec` package installed

**Patient name shows "Unknown"**
- Verify patient_id exists in `patient_lookup` collection
- Check MongoDB connection
- Run database sync script if available

---

## Performance Tuning

### Backend Optimization
- **Increase thread pool**: Modify `ThreadPoolExecutor` max_workers in `main.py`
- **Enable response caching**: Set `DEVELOPMENT_MODE=false` in `.env`
- **Reduce timeout**: Lower `timeout=60.0` in voice endpoint for faster failures
- **Batch WebSocket broadcasts**: Group multiple events before broadcasting

### Frontend Optimization
- **Build for production**: `npm run build` (minifies and optimizes)
- **Enable lazy loading**: Split routes with React.lazy()
- **Reduce polling interval**: Increase from 10s to 30s in dashboard components
- **Cache API responses**: Use TanStack Query's caching features

### Database Optimization
- **Add indexes**: Create indexes on frequently queried fields
  ```javascript
  db.interactions.createIndex({ patient_id: 1, timestamp: -1 })
  db.staff_assignments.createIndex({ staff_id: 1 })
  db.patient_lookup.createIndex({ patient_id: 1 })
  ```
- **Limit query results**: Use `.limit()` on all queries
- **Project only needed fields**: Use projection to reduce data transfer

---

## Development Workflow

### Adding a New Intent

1. Add samples to `ml_model/caremate_big_dataset.csv`
2. Retrain model: `python ml_model/retrain_final.py`
3. Update intent handling in `main.py` → `process_input()`
4. Add dashboard endpoint in `api.py`
5. Create frontend route in `src/routes/`
6. Test with patient device

### Adding a New Dashboard

1. Create route file: `src/routes/newrole.tsx`
2. Add API endpoint: `GET /newrole/queries` in `api.py`
3. Update `src/lib/roles.ts` with new role
4. Add staff with new role to `staff_directory` collection
5. Create staff assignments in `staff_assignments` collection

### Modifying IDP Pipeline

1. Edit extraction logic in `idp_pipeline.py`
2. Update medical analyzer in `medical_analyzer.py`
3. Modify patient history schema in MongoDB
4. Update frontend to display new fields
5. Test with sample PDF upload

---

## Testing Checklist

- [ ] Backend health check: `curl http://localhost:8000/health`
- [ ] Staff login with all roles
- [ ] Patient voice message end-to-end
- [ ] Doctor voice response to patient
- [ ] PDF upload and IDP processing
- [ ] WebSocket real-time updates
- [ ] Emergency alert flow
- [ ] Intent classification accuracy
- [ ] Multilingual voice (test 3+ languages)
- [ ] Dashboard filtering by staff_id
- [ ] Patient history display
- [ ] Audio file playback

---

## Deployment Checklist

- [ ] Replace password auth with JWT
- [ ] Move audio/PDF to S3 or cloud storage
- [ ] Set up Redis for caching
- [ ] Configure production MongoDB with replica set
- [ ] Enable HTTPS with SSL certificate
- [ ] Set up monitoring (Sentry, DataDog, CloudWatch)
- [ ] Configure backup strategy
- [ ] Add rate limiting (e.g., slowapi)
- [ ] Set up CI/CD pipeline
- [ ] Configure environment-specific .env files
- [ ] Enable logging to external service
- [ ] Set up health check monitoring
- [ ] Configure auto-scaling
- [ ] Test disaster recovery procedures

---

## Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **TanStack Router**: https://tanstack.com/router/latest
- **Sarvam AI API**: https://docs.sarvam.ai/
- **OpenRouter**: https://openrouter.ai/docs
- **ChromaDB**: https://docs.trychroma.com/
- **MongoDB Atlas**: https://www.mongodb.com/docs/atlas/
- **Streamlit**: https://docs.streamlit.io/
