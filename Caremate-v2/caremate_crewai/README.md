# CareMate: Two-Agent Hospital Patient Assistant

A CrewAI-based intelligent patient assistant system designed for hospital environments, emphasizing safety, human oversight, and HIPAA compliance.

## 🏥 Overview

CareMate is a minimal, two-agent agentic AI system that helps patients in hospital settings by:
- Understanding patient requests through natural language
- Classifying intent and urgency
- Enforcing strict hospital policies
- Routing medical requests to appropriate staff
- Providing safe, non-medical assistance
- Maintaining complete audit trails

### Key Features

✅ **Safety-First Design**: No autonomous medical advice  
✅ **Human-in-the-Loop**: Mandatory approval for medical decisions  
✅ **Emergency Detection**: Instant escalation of critical situations  
✅ **Multi-Tool Agents**: Each agent equipped with specialized capabilities  
✅ **HIPAA Compliant**: Full audit logging and data encryption  
✅ **Multilingual Support**: Integration-ready for speech and translation services

## 🏗️ Architecture

### Two-Agent System

#### 1. Patient Intelligence Agent
**Role**: Context analyzer and intent classifier  
**Tools**:
- Patient Record Retrieval
- Context Summarization
- Intent Classification
- Distress Detection
- Memory Management

#### 2. Central Orchestrator & Policy Agent
**Role**: Decision maker and policy enforcer  
**Tools**:
- Policy Evaluation
- Response Generation
- Staff Notification
- Approval Workflow
- Audit Logging

### Process Flow

```
Patient Query → Speech-to-Text → Translation
                      ↓
         Patient Intelligence Agent
           (Context & Classification)
                      ↓
      Orchestrator & Policy Agent
         (Decision & Response)
                      ↓
  Translation → Text-to-Speech → Patient
         ↓
  Staff Dashboard (if approval needed)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10, 3.11, or 3.12
- PostgreSQL 15+
- Redis
- OpenAI API key (or alternative LLM provider)

### Installation

1. **Clone and setup**:
```bash
git clone <repository-url>
cd caremate_crewai
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -e .
```

4. **Configure environment**:
```bash
cp .env.template .env
# Edit .env with your configuration
```

5. **Setup database**:
```bash
# Create PostgreSQL database
createdb caremate_db

# Run migrations (if using Alembic)
alembic upgrade head
```

6. **Run the application**:
```bash
python src/main.py
```

The API will be available at `http://localhost:8000`

## 📖 Usage

### Basic Query Processing

```python
from caremate.crew import CareMateCrew

# Initialize crew
caremate = CareMateCrew()

# Process patient query
result = caremate.process_patient_query(
    query="I need my pain medication",
    hospital_id="PT-12345",
    bed_number="ICU-201"
)

print(result['response_text'])
# Output: "I've notified your nurse about your medication request. 
#          They will be with you shortly to help."
```

### API Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/patient/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Can I have some water?",
    "hospital_id": "PT-12345",
    "bed_number": "Room-305",
    "language": "en"
  }'
```

### Emergency Example

```python
result = caremate.process_patient_query(
    query="I'm having severe chest pain and can't breathe",
    hospital_id="PT-67890",
    bed_number="ER-101"
)

# Automatically escalates to emergency team
# No approval needed - immediate response
```

## 🔧 Configuration

### Key Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=your_key_here
MODEL_NAME=gpt-4-turbo-preview
TEMPERATURE=0.3

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/caremate_db

# Redis (for memory)
REDIS_URL=redis://localhost:6379/0

# CrewAI Settings
CREWAI_VERBOSE=true
CREWAI_MEMORY_ENABLED=true
CREWAI_MAX_ITERATIONS=5
```

See `.env.template` for complete configuration options.

## 🛡️ Safety & Compliance

### Hospital Policies Enforced

1. **No Medical Advice**: System never provides autonomous medical guidance
2. **Medication Approval**: ALL medication requests require nurse approval
3. **Emergency Escalation**: Critical symptoms trigger immediate staff notification
4. **Distress Detection**: Repeated or urgent requests escalate automatically
5. **Audit Trail**: Complete logging of all decisions and actions

### HIPAA Compliance

- ✅ Encrypted data at rest (AES-256)
- ✅ TLS 1.3 for data in transit
- ✅ Immutable audit logs (7-year retention)
- ✅ Access control with role-based permissions
- ✅ PHI de-identification in logs where possible

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Metrics Endpoint

```bash
curl http://localhost:8000/api/v1/metrics
```

Returns:
- Active patient sessions
- Pending approval count
- Emergency escalations today
- Average response time

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=caremate --cov-report=html

# Run specific test
pytest tests/test_patient_intelligence_tools.py
```

## 📁 Project Structure

```
caremate_crewai/
├── src/
│   ├── caremate/
│   │   ├── __init__.py
│   │   ├── crew.py                    # Main CrewAI configuration
│   │   ├── models.py                  # Pydantic data models
│   │   ├── config/
│   │   │   ├── agents.yaml           # Agent configurations
│   │   │   └── tasks.yaml            # Task configurations
│   │   └── tools/
│   │       ├── patient_intelligence_tools.py
│   │       └── orchestrator_tools.py
│   └── main.py                        # FastAPI application
├── tests/
│   ├── test_agents.py
│   ├── test_tools.py
│   └── test_integration.py
├── docs/
│   └── CAREMATE_TECHNICAL_SPECS.md   # Complete technical specs
├── pyproject.toml                     # Project configuration
├── .env.template                      # Environment variables template
└── README.md
```

## 🔌 Integration Points

### Speech-to-Text Integration

```python
# Example with Azure Speech Services
from caremate.crew import CareMateCrew

caremate = CareMateCrew()

result = caremate.process_with_translation(
    voice_input=audio_data,  # Raw audio or transcribed text
    hospital_id="PT-12345",
    bed_number="ICU-201",
    patient_language="es"  # Spanish
)
# Automatically handles translation both ways
```

### Hospital EHR Integration

Update `patient_intelligence_tools.py`:

```python
def _fetch_from_database(self, hospital_id: str, bed_number: str):
    # Replace with actual EHR API call
    response = requests.get(
        f"{HOSPITAL_API_URL}/patients/{hospital_id}",
        headers={"Authorization": f"Bearer {HOSPITAL_API_KEY}"}
    )
    return response.json()
```

## 🎯 Use Cases

### ✅ Non-Medical Requests (Auto-Handled)
- "Can I have some water?"
- "The room is too cold"
- "Can you turn on the TV?"
- "What time is it?"

### ⚕️ Medical Requests (Nurse Approval Required)
- "I need my pain medication"
- "Can I see the doctor?"
- "My incision hurts"
- "I feel dizzy"

### 🚨 Emergencies (Immediate Escalation)
- "I'm having chest pain"
- "I can't breathe"
- "I think I'm having a stroke"
- "Severe bleeding"

## 📈 Performance

### Benchmarks (Target)

- **Response Time**: <2s for non-medical, <5s for medical
- **Emergency Detection**: >99.9% recall
- **Medical Advice False Positive**: <0.1%
- **System Uptime**: 99.9% SLA

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run code formatting
black src/ tests/
ruff check src/ tests/

# Run type checking
mypy src/
```

## 📄 License

Proprietary - Hospital Internal Use Only

## 📞 Support

- **Technical Issues**: Create an issue in the repository
- **Security Concerns**: security@caremate.hospital (immediate attention)
- **General Questions**: support@caremate.hospital

## 🗺️ Roadmap

### Phase 2 (Q2 2026)
- [ ] Multi-language direct support (no translation layer)
- [ ] Voice emotion detection
- [ ] Predictive patient needs
- [ ] EHR system integration (Epic, Cerner)

### Phase 3 (Q3 2026)
- [ ] Medication timing reminders
- [ ] Post-discharge follow-up
- [ ] Family communication portal
- [ ] Advanced analytics dashboard

## 📚 Additional Resources

- [Complete Technical Specifications](docs/CAREMATE_TECHNICAL_SPECS.md)
- [CrewAI Documentation](https://docs.crewai.com)
- [HIPAA Compliance Guide](docs/HIPAA_COMPLIANCE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## ⚖️ Important Notices

**Medical Disclaimer**: CareMate is an assistive technology tool designed to facilitate communication and coordination within hospital settings. It does NOT provide medical diagnoses, treatment recommendations, or replace professional medical judgment. All medical decisions must be made by qualified healthcare professionals.

**Data Privacy**: This system processes Protected Health Information (PHI) and must be deployed in accordance with HIPAA regulations and hospital data governance policies.

---

**Version**: 1.0.0  
**Last Updated**: February 4, 2026  
**Framework**: CrewAI v1.9.3+
