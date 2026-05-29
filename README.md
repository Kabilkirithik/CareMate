# CareMate — AI-Powered Hospital Coordination System

> Voice-first · Multilingual · Real-time · Emergency-grade

---

## What is CareMate?

CareMate is an intelligent hospital coordination platform that replaces the traditional nurse call button with a full AI voice assistant. Patients speak in their native language — CareMate transcribes, understands the intent, routes the request to the right staff dashboard, and responds back in the patient's language with synthesized speech.

Every role in the hospital gets a dedicated real-time dashboard: doctors see medical queries, nurses see care requests, nutritionists see meal requests, utility staff see maintenance requests, and admins see the full picture.

---

## Tech Stack

### Backend
| Layer | Technology |
|-------|-----------|
| API Server | **FastAPI** (Python) with Uvicorn ASGI |
| Real-time | **WebSocket** (FastAPI native) |
| Database | **MongoDB Atlas** (dual cluster setup) |
| Speech-to-Text | **Sarvam AI** — `saaras:v3` model (11 Indian languages) |
| Text-to-Speech | **Sarvam AI** — `bulbul:v3` model |
| Translation | **Sarvam AI** translate API |
| Medical LLM | **Meditron** (hosted on AWS SageMaker via ngrok) |
| General LLM | **NVIDIA Nemotron** via **OpenRouter** |
| Intent Classification | **SVM** trained on SentenceTransformer embeddings (`all-MiniLM-L6-v2`) |
| OCR / IDP | **Amazon Textract** (falls back to pypdf) |
| Vector Search | **ChromaDB** (local persistent) with `all-MiniLM-L6-v2` embeddings |
| Caching | In-memory + disk cache (response, translation, TTS) |

### Frontend
| Layer | Technology |
|-------|-----------|
| Framework | **React 19** with **TanStack Start** (SSR) |
| Routing | **TanStack Router** (file-based) |
| Styling | **Tailwind CSS v4** with custom OKLCH color palette |
| Build Tool | **Vite 7** |
| UI Components | **Radix UI** primitives |
| Notifications | **Sonner** toast library |
| Icons | **Lucide React** |
| Language | **TypeScript** |

### Patient Device
| Layer | Technology |
|-------|-----------|
| Interface | **Streamlit** |
| Audio Recording | `st-audiorec` |

### Infrastructure
| Layer | Technology |
|-------|-----------|
| Cloud Database | **MongoDB Atlas** (2 clusters) |
| Speech APIs | **Sarvam AI** (cloud) |
| OCR | **Amazon Textract** (AWS `ap-south-1`) |
| ML Inference | **AWS SageMaker** + ngrok tunnel |
| LLM Routing | **OpenRouter** API |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PATIENT LAYER                            │
│   Streamlit Device (patient_device.py / chat_interface.py)      │
│   Records voice → sends to API → plays audio response           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                      FASTAPI BACKEND (api.py)                   │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Speech Layer│  │Intent Router │  │   IDP Pipeline         │ │
│  │ (Sarvam AI) │  │ (SVM + rules)│  │ Textract → Parser →    │ │
│  │ STT parallel│  │ 7 intents    │  │ Medical Analyzer →     │ │
│  │ TTS + Trans │  │ keyword OVR  │  │ Patient History        │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Meditron   │  │  Nemotron    │  │   Performance Cache    │ │
│  │ (SageMaker) │  │ (OpenRouter) │  │ Response/TTS/Trans     │ │
│  │ Medical LLM │  │ Workflow LLM │  │ Instant responses      │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              MongoDB (Dual Cluster)                       │   │
│  │  caremate_db: patients, visits, documents, history        │   │
│  │  caremate_interaction_db: interactions, staff, messages   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ WebSocket + REST
┌──────────────────────────▼──────────────────────────────────────┐
│                    NEXT.JS FRONTEND DASHBOARDS                   │
│                                                                  │
│  /doctor    /nurse    /nutrition    /utility    /admin           │
│  Voice      Kanban    Meal plans    Maintenance  Metrics         │
│  console    queue     + queries     queue        + alerts        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Features

### Voice Pipeline
- Patient speaks in any of 11 Indian languages
- Two parallel Sarvam API calls: `translate` (→ English for AI) + `transcribe` (→ native for language detection)
- AI processes in English, response translated back to patient's language
- TTS generates audio with language-appropriate voice (e.g. `kavitha` for Tamil)
- Full round-trip in ~8–10 seconds

### Intent Routing
Seven intents classified by a fine-tuned SVM on 17,000+ hospital samples:

| Intent | Handler | Dashboard |
|--------|---------|-----------|
| `emergency` | Instant alert | Doctor (all) |
| `doctor_query` | Acknowledgement | Doctor |
| `status_query` | Acknowledgement | Doctor |
| `general_conversation` | Meditron | Patient device |
| `nurse_request` | Nemotron + workflow | Nurse |
| `nutrition_request` | Nemotron + workflow | Nutrition |
| `utility_request` | Nemotron + workflow | Utility |

Keyword override: messages starting with "Doctor," are always `doctor_query` regardless of SVM confidence.

### IDP Pipeline (Document Processing)
When a PDF is uploaded by nurse or admin:
1. **Amazon Textract** performs OCR (handles scanned documents, tables, images)
2. **Patient ID** extracted from document (`PID: 130`) — overrides URL parameter
3. **Medical Parser** extracts: medications, diagnoses, vitals, lab results, allergies
4. **MongoDB** patient record updated with extracted data
5. **Medical Analyzer** flags abnormal values against clinical reference ranges
6. **AI Interpretation** generated (Meditron → OpenRouter → rule-based fallback)
7. **Patient History** entry stored in `patient_history` collection
8. **WebSocket** broadcasts `DOCUMENT_PROCESSED` to all dashboards

### Real-time Communication
- WebSocket connection maintained between backend and all open dashboards
- Events: `NEW_REQUEST`, `EMERGENCY_ALERT`, `PROCESSING_STARTED`, `DOCUMENT_PROCESSED`
- 10-second polling fallback on frontend for missed WebSocket events

### Staff Allocation
- Each doctor is assigned 5–8 patients from `staff_assignments` collection
- Dashboard queries filtered by `staff_id` — doctors only see their patients' queries
- Nutritionists assigned round-robin to all active patients

### Multilingual Support
11 languages via Sarvam AI:

| Language | Code | TTS Voice |
|----------|------|-----------|
| English | en-IN | gokul |
| Hindi | hi-IN | gokul |
| Tamil | ta-IN | kavitha |
| Telugu | te-IN | shreya |
| Kannada | kn-IN | vidya |
| Malayalam | ml-IN | priya |
| Marathi | mr-IN | manisha |
| Gujarati | gu-IN | anushka |
| Bengali | bn-IN | ritu |
| Punjabi | pa-IN | simran |
| Odia | od-IN | neha |

---

## Dashboards

### Doctor Dashboard (`/doctor`)
- Patient query queue filtered to assigned patients only
- Voice console: record and send voice replies to patient device
- Patient summary panel: loads vitals, medications, notes, allergies on click
- Collapsible assigned patients list
- Real-time emergency alerts with overlay

### Nurse Dashboard (`/nurse`)
- Kanban board: New → In Progress → Completed
- OCR document upload (triggers IDP pipeline)
- Filtered to nurse-intent queries only

### Nutrition Dashboard (`/nutrition`)
- Patient nutrition queries
- Meal request management
- Patient health summary with allergies and dietary restrictions

### Utility Dashboard (`/utility`)
- Maintenance request queue with priority indicators
- Patient utility requests
- System status overview

### Admin Dashboard (`/admin`)
- Hospital metrics (patients, active visits, emergencies, staff)
- Emergency alert history
- User management
- Activity feed

---

## Running the System

### Prerequisites
- Python 3.10+ with pip
- Node.js 18+ with npm
- MongoDB Atlas account (or local MongoDB)
- API keys: Sarvam AI, OpenRouter, AWS (optional for Textract)

### 1. Configure environment
Create or edit `E:\FAER\CareMate\.env`:

```env
# MongoDB (Required)
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
FRONTEND_MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/

# Sarvam AI (Required for voice)
SARVAM_API_KEY=sk_your_sarvam_key

# OpenRouter (Required for AI)
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_key

# Meditron SageMaker (Optional - falls back to OpenRouter)
SAGEMAKER_URL=https://your-ngrok-url.ngrok-free.dev

# AWS Textract (Optional - falls back to pypdf)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-south-1

# Development mode
DEVELOPMENT_MODE=false
```

### 2. Install backend dependencies
```bash
cd E:\FAER\CareMate\Vfinal
pip install -r requirements.txt
```

> **Note**: First run downloads SentenceTransformer model (~80MB) — takes ~30 seconds

### 3. Start backend API server
```bash
cd E:\FAER\CareMate\Vfinal
python api.py
```
Server starts at: **http://localhost:8000**

API documentation: **http://localhost:8000/docs**

### 4. Install frontend dependencies
```bash
cd E:\FAER\CareMate\Vfinal-frontend
npm install
```

### 5. Start frontend dashboard
```bash
cd E:\FAER\CareMate\Vfinal-frontend
npm run dev
```
Dashboard opens at: **http://localhost:3000** (or port 5173)

### 6. Start patient device (optional)
```bash
cd E:\FAER\CareMate\Vfinal
streamlit run patient_device.py
```
Patient interface opens at: **http://localhost:8501**

Alternative chat interface:
```bash
streamlit run chat_interface.py
```

---

## Quick Test

1. Open frontend at http://localhost:3000
2. Login with: `troy.stewart@hospital.com` / `hospital123`
3. Open patient device at http://localhost:8501
4. Select patient ID `183` (Richard Prince)
5. Record a voice message: "Doctor, I have a headache"
6. Check doctor dashboard for the new query

---

## Project Structure

```
E:\FAER\CareMate\
├── .env                          # API keys and config
├── README.md                     # This file
├── README_OPERATIONS.md          # Detailed operations guide
├── README_PROJECT_STRUCTURE.md   # File-by-file reference
│
├── Vfinal/                       # Python backend
│   ├── api.py                    # FastAPI server (entry point)
│   ├── main.py                   # Voice processing pipeline
│   ├── speech_layer.py           # Sarvam AI STT/TTS/Translation
│   ├── intent_router.py          # SVM intent classifier
│   ├── hospital_tools.py         # AI tool implementations
│   ├── meditron_client.py        # Meditron LLM client
│   ├── openrouter_client.py      # OpenRouter/Nemotron client
│   ├── performance_optimizer.py  # Caching layer
│   ├── idp_pipeline.py           # IDP: Textract + parsing
│   ├── medical_analyzer.py       # Lab analysis + patient history
│   ├── rag_pipeline.py           # ChromaDB vector search
│   ├── patient_device.py         # Streamlit patient interface
│   ├── chat_interface.py         # Streamlit chat interface
│   ├── requirements.txt
│   └── ml_model/
│       ├── caremate_sentence_transformer_svm.pkl   # Trained model
│       ├── caremate_big_dataset.csv                # 17k+ training samples
│       └── retrain_final.py                        # Retrain script
│
└── Vfinal-frontend/              # React frontend
    └── src/
        ├── routes/               # Page components
        │   ├── index.tsx         # Landing page
        │   ├── login.tsx         # Staff login
        │   ├── doctor.tsx        # Doctor dashboard
        │   ├── nurse.tsx         # Nurse dashboard
        │   ├── nutrition.tsx     # Nutrition dashboard
        │   ├── utility.tsx       # Utility dashboard
        │   └── admin.tsx         # Admin dashboard
        ├── components/           # Shared UI components
        ├── lib/
        │   ├── api.ts            # Backend API client
        │   └── websocket.ts      # WebSocket client
        └── styles.css            # Global styles + color palette
```

---

## Design Principles

- **Voice-first**: Every interaction is designed for voice. Text is secondary.
- **Mobile-first**: Touch targets, minimal UI, works on tablets and phones.
- **Graceful degradation**: Every AI component has a fallback. The system never crashes on a model failure.
- **Non-blocking**: Document processing, AI inference, and TTS run asynchronously. The patient always gets an immediate acknowledgement.
- **Secure multi-tenancy**: Each staff member sees only their assigned patients. ChromaDB queries are filtered by patient_id.
- **Hospital-safe colors**: Trust Blue (#0B3C5D), Calm Teal (#328CC1), Health Green (#2EC4B6), Crimson Red (#D90429) for emergencies. See [COLOR_PALETTE.md](COLOR_PALETTE.md) for complete design system.

---

## Performance Optimizations

### Caching Strategy
- **Response Cache**: Common queries cached for instant responses
- **Translation Cache**: Frequently translated phrases stored
- **TTS Cache**: Generated audio files reused for identical text
- **Instant Responses**: Predefined responses for greetings and acknowledgments

### Parallel Processing
- **Dual STT**: `translate` and `transcribe` APIs called simultaneously
- **Background IDP**: Document processing runs async, doesn't block upload response
- **Thread Pool**: Voice processing uses executor for CPU-bound tasks
- **WebSocket Broadcasting**: Real-time updates to all connected dashboards

### Timeout Protection
- **Voice Processing**: 60-second timeout with fallback response
- **Meditron LLM**: 25-second timeout with OpenRouter fallback
- **Textract**: Falls back to pypdf on timeout or missing credentials

---

## Security Features

- **Password Authentication**: Staff login with email/password (bcrypt recommended for production)
- **Role-Based Access**: Each dashboard filtered by staff role and assignments
- **Patient Assignment**: Doctors/nurses only see their assigned patients
- **CORS Protection**: Configurable allowed origins
- **Input Validation**: Pydantic models validate all API inputs
- **Audio Validation**: File size and format checks prevent malicious uploads

---

## Monitoring & Logging

All operations logged with timestamps:
- Voice processing pipeline stages
- Intent classification results
- AI model responses and fallbacks
- WebSocket connections and broadcasts
- IDP pipeline progress
- Error traces with full stack

Logs viewable in console during development.

---

## Known Limitations

1. **Meditron Dependency**: Requires ngrok tunnel to SageMaker (tunnel expires periodically)
2. **ChromaDB Persistence**: Local storage only — not suitable for distributed deployment
3. **Audio Storage**: Files stored on disk — consider S3 for production
4. **No Authentication Tokens**: Simple password auth — implement JWT for production
5. **Single Server**: No load balancing or horizontal scaling
6. **Language Detection**: Relies on Sarvam transcribe — may misdetect similar languages

---

## Future Enhancements

- [ ] JWT authentication with refresh tokens
- [ ] Redis caching layer for distributed deployment
- [ ] S3 storage for audio and PDF files
- [ ] Real-time vitals monitoring integration
- [ ] Mobile app for patient device (React Native)
- [ ] Video consultation integration
- [ ] Prescription generation and e-signature
- [ ] Insurance claim automation
- [ ] Multi-hospital support with tenant isolation
- [ ] Advanced analytics dashboard with Recharts

---

## Contributing

This is a production-ready prototype. For deployment:

1. Replace password auth with JWT
2. Move audio/PDF storage to S3
3. Use Redis for caching
4. Add rate limiting
5. Enable HTTPS
6. Set up monitoring (Sentry, DataDog)
7. Configure backup strategy for MongoDB

---

## License

Proprietary — FAER CareMate Project

---

## Support

For technical issues or questions, contact the development team.
