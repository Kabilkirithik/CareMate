# CareMate Backend - Project Structure

## 📁 Complete File Organization

```
caremate_backend/
│
├── README.md                      # Complete documentation
├── QUICKSTART.md                  # 10-minute setup guide
├── requirements.txt               # Python dependencies
├── .env.template                  # Environment variables template
│
├── caremate_backend.py           # Main backend application
├── caremate_colab_setup.ipynb    # Google Colab notebook
├── test_system.py                # Comprehensive test suite
│
├── config/
│   ├── __init__.py
│   ├── settings.py               # Configuration management
│   └── constants.py              # System constants
│
├── agents/
│   ├── __init__.py
│   ├── patient_intelligence.py   # Patient Intelligence Agent
│   ├── orchestrator.py           # Orchestrator & Policy Agent
│   └── base.py                   # Base agent configurations
│
├── tools/
│   ├── __init__.py
│   ├── patient_tools.py          # Patient-related tools
│   ├── policy_tools.py           # Policy evaluation tools
│   ├── notification_tools.py     # Staff notification tools
│   └── memory_tools.py           # Memory management tools
│
├── services/
│   ├── __init__.py
│   ├── sarvam_client.py          # Sarvam AI integration
│   ├── gemini_client.py          # Gemini LLM integration
│   └── database.py               # MongoDB operations
│
├── models/
│   ├── __init__.py
│   ├── patient.py                # Patient data models
│   ├── interaction.py            # Interaction models
│   └── response.py               # Response models
│
├── api/
│   ├── __init__.py
│   ├── routes.py                 # FastAPI routes
│   ├── dependencies.py           # API dependencies
│   └── middleware.py             # Custom middleware
│
├── tests/
│   ├── __init__.py
│   ├── test_agents.py            # Agent tests
│   ├── test_tools.py             # Tool tests
│   ├── test_api.py               # API tests
│   └── test_integration.py       # Integration tests
│
├── scripts/
│   ├── create_sample_data.py     # Generate test data
│   ├── reset_database.py         # Database reset utility
│   └── migrate_data.py           # Data migration scripts
│
├── docs/
│   ├── architecture.md           # System architecture
│   ├── api_reference.md          # API documentation
│   ├── deployment.md             # Deployment guide
│   └── troubleshooting.md        # Common issues
│
└── .gitignore                     # Git ignore rules
```

---

## 📄 File Descriptions

### Core Files

#### **caremate_backend.py**
- Complete backend implementation
- Two-agent CrewAI architecture
- FastAPI REST API
- All tools and models integrated
- Ready to run as-is

#### **caremate_colab_setup.ipynb**
- Google Colab notebook for cloud deployment
- Step-by-step setup instructions
- Includes all dependencies
- Auto-configuration scripts

#### **test_system.py**
- Comprehensive test suite
- Tests all components
- Environment validation
- Dependency checking
- Agent and tool verification

---

### Configuration Files

#### **requirements.txt**
```
crewai==0.86.0
crewai-tools==0.17.0
langchain==0.3.14
langchain-google-genai==2.0.8
pymongo==4.10.1
fastapi==0.115.6
uvicorn==0.34.0
pydantic==2.10.5
requests==2.32.3
nest-asyncio==1.6.0
pyngrok==7.2.2
```

#### **.env.template**
```bash
# Copy to .env and fill in values
GEMINI_API_KEY=your_key_here
SARVAM_API_KEY=your_key_here
MONGODB_URI=mongodb://localhost:27017/
OTEL_SDK_DISABLED=true
```

---

### Documentation Files

#### **README.md**
- Complete system documentation
- Architecture overview
- Setup instructions
- API reference
- Security guidelines
- Deployment options
- Troubleshooting guide

#### **QUICKSTART.md**
- 10-minute setup guide
- Step-by-step instructions
- Common issues and solutions
- Testing procedures
- Next steps

---

## 🔧 Component Breakdown

### 1. Two-Agent Architecture

```python
# Agent 1: Patient Intelligence Agent
- Role: Context Analysis
- Tools: 
  * PatientRecordRetrievalTool
  * ContextSummarizationTool
  * IntentClassificationTool
  * DistressDetectionTool
  * MemoryManagementTool

# Agent 2: Central Orchestrator Agent
- Role: Decision Making
- Tools:
  * PolicyEvaluationTool
  * NotificationTool
  * AuditLoggingTool
```

### 2. Data Models

```python
# Patient Context
class PatientContext(BaseModel):
    hospital_id: str
    name: str
    diagnosis: str
    medications: List[str]
    allergies: List[str]

# Intent Analysis
class IntentAnalysis(BaseModel):
    intent_category: IntentCategory
    urgency_level: UrgencyLevel
    is_emergency: bool
    confidence_score: float

# Response Decision
class ResponseDecision(BaseModel):
    can_respond_directly: bool
    requires_approval: bool
    requires_escalation: bool
    response_text: str
```

### 3. API Endpoints

```python
# Core Endpoints
GET  /api/v1/health              # Health check
POST /api/v1/query               # Process patient query
GET  /api/v1/patient/{id}        # Get patient info
GET  /api/v1/interactions/{id}   # Get interaction history
```

### 4. Database Collections

```javascript
// MongoDB Collections
{
  patients: {
    hospital_id, name, age, diagnosis,
    medications, allergies, doctors
  },
  interactions: {
    interaction_id, patient_id, timestamp,
    query_text, intent_analysis, response
  },
  escalations: {
    escalation_id, patient_id, priority,
    status, assigned_to
  },
  audit_logs: {
    event_type, timestamp, data
  }
}
```

---

## 🚀 Deployment Variants

### Development
```bash
# Local with hot reload
uvicorn caremate_backend:app --reload
```

### Production
```bash
# With Gunicorn
gunicorn caremate_backend:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Docker
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY caremate_backend.py .
CMD ["python", "caremate_backend.py"]
```

### Google Colab
```python
# Use caremate_colab_setup.ipynb
# All setup automated in notebook
```

---

## 🔐 Security Considerations

### API Keys
- Never commit `.env` file
- Use secrets management in production
- Rotate keys regularly

### Database
- Use authentication in production
- Enable MongoDB access control
- Encrypt connections (SSL/TLS)

### API
- Implement rate limiting
- Add authentication tokens
- Use HTTPS in production

---

## 📊 Monitoring

### Logging
```python
# All interactions logged to MongoDB
# Audit trail for compliance
# Error tracking enabled
```

### Metrics
```python
# Track:
# - Requests per minute
# - Response times
# - Agent decision distribution
# - Escalation rates
```

---

## 🧪 Testing Strategy

### Unit Tests
```bash
pytest tests/test_agents.py
pytest tests/test_tools.py
```

### Integration Tests
```bash
pytest tests/test_integration.py
```

### System Tests
```bash
python test_system.py
```

### Load Tests
```bash
# Use locust or k6 for load testing
```

---

## 📝 Development Workflow

### 1. Setup
```bash
git clone <repo>
cd caremate_backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.template .env
# Edit .env with API keys
```

### 2. Development
```bash
python caremate_backend.py
# Make changes
# Test with curl or Postman
```

### 3. Testing
```bash
python test_system.py
pytest tests/
```

### 4. Deployment
```bash
# Build Docker image
docker build -t caremate-backend .

# Deploy to cloud
# (See deployment.md for platform-specific guides)
```

---

## 🎯 Key Features Implementation

### Voice Processing
- **Input:** ESP32 → Audio (base64) → Backend
- **STT:** Sarvam AI Saarika model (10+ Indian languages)
- **TTS:** Sarvam AI Bulbul model (natural voices)

### Intelligence
- **Agent 1:** Context + Intent + Urgency analysis
- **Agent 2:** Policy + Decision + Response generation
- **LLM:** Google Gemini 2.0 Flash

### Safety
- **Human-in-Loop:** Mandatory for medical requests
- **Emergency Escalation:** Automatic for critical cases
- **Audit Trail:** Complete logging of all actions

---

## 🔄 Data Flow

```
Patient Speaks
    ↓
ESP32 Records
    ↓
Base64 Audio → Backend
    ↓
Sarvam STT → English Text
    ↓
Agent 1: Intelligence Analysis
    ↓
Agent 2: Policy Decision
    ↓
Gemini LLM → Response Text
    ↓
Sarvam TTS → Audio Response
    ↓
ESP32 Plays Audio
    ↓
Patient Hears Response
    ↓
MongoDB Logs Everything
```

---

## 📚 Additional Resources

### External Documentation
- [CrewAI Docs](https://docs.crewai.com)
- [Sarvam AI API](https://docs.sarvam.ai)
- [Gemini API](https://ai.google.dev/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com)

### Community
- GitHub Issues (for bugs/features)
- Discussion Forum (for questions)
- Email Support (for critical issues)

---

## 🎓 Learning Path

### Beginner
1. Read QUICKSTART.md
2. Run in Google Colab
3. Test basic endpoints
4. Understand agent flow

### Intermediate
1. Study caremate_backend.py
2. Modify agent behaviors
3. Add custom tools
4. Enhance policies

### Advanced
1. Deploy to production
2. Scale with load balancers
3. Add monitoring/alerting
4. Integrate with hospital systems

---

**Version:** 1.0.0  
**Last Updated:** February 5, 2025  
**Maintainer:** FAER Scholar Project Team
