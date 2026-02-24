# CareMate CrewAI Technical Specifications

**Version:** 1.0  
**Date:** February 4, 2026  
**System:** CareMate Two-Agent Hospital Assistant  
**Framework:** CrewAI v1.9.3+

---

## 1. Executive Summary

CareMate is a two-agent agentic AI system built on the CrewAI framework, designed specifically for hospital patient care environments. The system emphasizes safety, determinism, and human oversight while providing intelligent patient assistance through natural language interactions.

### Key Design Principles
- **Minimal Agent Architecture**: 2 agents instead of many
- **Safety-First**: No autonomous medical decisions
- **Human-in-the-Loop**: Mandatory approval for medical requests
- **Explainable**: Clear decision trails and audit logs
- **Multi-tool Agents**: Each agent equipped with multiple specialized tools

---

## 2. System Architecture

### 2.1 High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     CareMate System                          │
│                                                              │
│  ┌──────────────────────┐      ┌─────────────────────────┐ │
│  │  Patient Intelligence│      │  Central Orchestrator   │ │
│  │       Agent          │─────▶│   & Policy Agent        │ │
│  │                      │      │                         │ │
│  │  - Context Retrieval │      │  - Policy Enforcement   │ │
│  │  - Intent Analysis   │      │  - Decision Making      │ │
│  │  - Urgency Detection │      │  - Response Generation  │ │
│  │  - Memory Management │      │  - Staff Notification   │ │
│  └──────────────────────┘      └─────────────────────────┘ │
│           │                              │                  │
│           │                              │                  │
│           ▼                              ▼                  │
│  ┌─────────────────────────────────────────────┐           │
│  │         Shared Data Layer                   │           │
│  │  - Patient Records DB                       │           │
│  │  - Interaction Memory                       │           │
│  │  - Hospital Policy Rules                    │           │
│  │  - Audit Logs                               │           │
│  └─────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
         │                                  │
         ▼                                  ▼
┌──────────────────┐              ┌──────────────────┐
│  Staff Dashboard │              │ External Systems │
│  - Approval Queue│              │ - Speech-to-Text │
│  - Notifications │              │ - Text-to-Speech │
│  - Audit Viewer  │              │ - Translation    │
└──────────────────┘              └──────────────────┘
```

### 2.2 Agent Architecture

#### Agent 1: Patient Intelligence Agent
**Role**: Patient context analyzer and intent classifier  
**Autonomy Level**: Information gathering only (no decisions)

**Responsibilities**:
1. Parse translated patient queries
2. Retrieve patient-specific information
3. Classify request intent (medical/non-medical/emergency)
4. Detect distress signals
5. Maintain conversational context

**Tools**:
- PatientRecordRetrievalTool
- ContextSummarizationTool
- IntentClassificationTool
- DistressDetectionTool
- MemoryManagementTool

#### Agent 2: Central Orchestrator & Policy Agent
**Role**: Decision-making and orchestration core  
**Autonomy Level**: Rule-based decision making with human escalation

**Responsibilities**:
1. Evaluate safety and policy constraints
2. Determine response path (auto-respond/escalate/emergency)
3. Generate patient-safe responses
4. Trigger staff notifications
5. Log all decisions for audit

**Tools**:
- PolicyEvaluationTool
- ResponseGenerationTool
- NotificationTool
- ApprovalWorkflowTool
- AuditLoggingTool

---

## 3. CrewAI Implementation Details

### 3.1 Framework Version & Dependencies

```
crewai>=1.9.3
crewai-tools>=0.2.4
pydantic>=2.0.0
python>=3.10,<3.13
langchain-openai>=0.1.0  # or alternative LLM provider
```

### 3.2 Agent Configuration

#### Patient Intelligence Agent Config
```yaml
role: "Patient Context and Intent Analyzer"
goal: "Accurately understand patient needs, context, and urgency without making medical decisions"
backstory: |
  You are a specialized healthcare AI assistant focused on understanding patients.
  You analyze what patients say, retrieve their medical context, and classify their
  requests - but you NEVER make medical decisions or provide medical advice.
  Your job is to prepare complete, accurate information for the decision-making agent.
verbose: true
allow_delegation: false
max_iter: 3
memory: true
```

#### Central Orchestrator Agent Config
```yaml
role: "Healthcare Policy Enforcement and Orchestration Coordinator"
goal: "Ensure all patient interactions comply with hospital policies, route medical requests to staff, and provide safe non-medical assistance"
backstory: |
  You are the central decision-maker for the CareMate system. You enforce strict
  hospital safety policies: NO medical advice, ALL medication requests require
  nurse approval, ALL emergencies escalate immediately. You generate safe, helpful
  responses for non-medical requests and ensure proper staff notification for
  medical needs. Patient safety is your absolute priority.
verbose: true
allow_delegation: false
max_iter: 5
memory: true
```

### 3.3 Task Definitions

#### Task 1: Patient Analysis
```yaml
description: |
  Analyze the patient query: {query}
  
  Steps:
  1. Retrieve patient context using hospital_id: {hospital_id} and bed: {bed_number}
  2. Classify the intent (medical/non-medical/emergency)
  3. Detect any distress signals or urgent keywords
  4. Summarize relevant patient history
  5. Check recent interaction memory
  
  Return structured output with:
  - patient_context: Summary of relevant patient info
  - intent_category: One of [MEDICAL, NON_MEDICAL, EMERGENCY]
  - urgency_level: One of [LOW, MEDIUM, HIGH, CRITICAL]
  - distress_flags: List of detected concerns
  - conversation_history: Recent relevant interactions

expected_output: |
  JSON object containing patient_context, intent_category, urgency_level,
  distress_flags, and conversation_history

agent: patient_intelligence_agent
output_json: PatientAnalysisOutput
```

#### Task 2: Policy Evaluation and Response
```yaml
description: |
  Based on patient analysis from previous task, determine the appropriate action.
  
  Policy Rules:
  - EMERGENCY: Immediately notify emergency staff, skip approval
  - MEDICAL requests: Route to nurse/doctor dashboard for approval
  - Medication requests: ALWAYS require nurse approval
  - NON_MEDICAL: Generate direct response if safe
  - High distress: Escalate even if non-medical
  
  Patient Analysis Input: {task1_output}
  Original Query: {query}
  
  Steps:
  1. Apply policy evaluation rules
  2. Determine response path
  3. Generate appropriate response OR create approval request
  4. Send notifications if needed
  5. Log all decisions to audit trail
  
  Output:
  - response_text: Patient-facing message
  - action_taken: Description of system action
  - requires_approval: Boolean
  - staff_notified: List of staff IDs notified
  - audit_log_id: Reference to log entry

expected_output: |
  JSON object with response_text, action_taken, requires_approval,
  staff_notified, and audit_log_id

agent: orchestrator_policy_agent
output_json: OrchestratorOutput
context: [patient_analysis_task]
```

### 3.4 Process Flow

```
Sequential Process:
1. Patient speaks → Speech-to-Text → Translation to English
2. PatientIntelligenceAgent analyzes (Task 1)
3. OrchestratorAgent decides and acts (Task 2)
4. Response translated back to patient's language
5. Text-to-Speech delivers response
```

---

## 4. Custom Tools Specifications

### 4.1 Patient Intelligence Agent Tools

#### PatientRecordRetrievalTool
```python
Input: hospital_id (str), bed_number (str)
Output: PatientRecord (dict)
  - name: str
  - age: int
  - primary_diagnosis: str
  - medications: List[str]
  - allergies: List[str]
  - restrictions: List[str]
  - primary_nurse_id: str
  - attending_physician_id: str

Logic:
  - Query patient database
  - Return safe, non-diagnostic summary
  - Exclude sensitive details (diagnosis details)
  - Include only necessary context
```

#### ContextSummarizationTool
```python
Input: patient_record (dict), query (str)
Output: context_summary (str)

Logic:
  - Extract relevant portions of patient record
  - Match to query context
  - Create 2-3 sentence summary
  - Avoid medical jargon
  - Focus on immediate needs
```

#### IntentClassificationTool
```python
Input: query (str), patient_context (str)
Output: Intent classification
  - category: MEDICAL | NON_MEDICAL | EMERGENCY
  - confidence: float
  - reasoning: str

Logic:
  - Use LLM-based classification
  - Keywords: "pain", "medication", "doctor" → MEDICAL
  - Keywords: "water", "temperature", "TV" → NON_MEDICAL
  - Keywords: "chest pain", "can't breathe", "help" → EMERGENCY
  - Context-aware classification
```

#### DistressDetectionTool
```python
Input: query (str), tone_indicators (Optional[dict])
Output: DistressSignals
  - distress_detected: bool
  - distress_level: LOW | MEDIUM | HIGH
  - indicators: List[str]
  - recommended_action: str

Logic:
  - Detect repeated requests
  - Identify panic words
  - Analyze request urgency
  - Consider patient condition
```

#### MemoryManagementTool
```python
Input: action (STORE | RETRIEVE), conversation_data (dict)
Output: ConversationHistory | ConfirmationMessage

Logic:
  - Store last 10 interactions per patient
  - Retrieve context for continuity
  - Clear on patient discharge
  - Link to patient session
```

### 4.2 Orchestrator Agent Tools

#### PolicyEvaluationTool
```python
Input: intent (str), urgency (str), patient_context (dict)
Output: PolicyDecision
  - requires_human_approval: bool
  - escalation_level: NONE | NURSE | DOCTOR | EMERGENCY
  - reasoning: str
  - applicable_policies: List[str]

Hospital Policy Rules:
  1. NO autonomous medical advice
  2. ALL medication requests → Nurse approval
  3. EMERGENCY signals → Immediate escalation
  4. Pain level 7+ → Notify nurse
  5. Repeated distress → Escalate
  6. Non-medical requests < approval threshold → Auto-respond
```

#### ResponseGenerationTool
```python
Input: intent (str), patient_context (str), policy_decision (dict)
Output: response_text (str)

Logic:
  - Generate empathetic, clear responses
  - Avoid medical terminology
  - Set proper expectations
  - For approvals: "I've notified your nurse, they'll be with you shortly"
  - For non-medical: Direct helpful answer
  - Always reassuring tone
```

#### NotificationTool
```python
Input: recipient_ids (List[str]), message (str), priority (str)
Output: NotificationConfirmation
  - sent: bool
  - recipient_count: int
  - notification_ids: List[str]
  - timestamp: datetime

Delivery Channels:
  - Dashboard alert
  - Mobile app push notification
  - SMS for critical
  - Email for low priority
```

#### ApprovalWorkflowTool
```python
Input: request_type (str), patient_data (dict), original_query (str)
Output: ApprovalQueueEntry
  - queue_id: str
  - status: PENDING
  - assigned_to: str
  - created_at: datetime
  - expected_response_time: int (minutes)

Logic:
  - Create dashboard entry
  - Route to appropriate staff
  - Set SLA timers
  - Enable approve/reject actions
```

#### AuditLoggingTool
```python
Input: event_type (str), agent_id (str), decision_data (dict)
Output: audit_log_id (str)

Logged Fields:
  - timestamp
  - patient_id
  - query_text
  - intent_classification
  - policy_decision
  - staff_notifications
  - response_generated
  - approval_status
  - agent_chain
  
Storage: Append-only database with HIPAA compliance
```

---

## 5. Data Models (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class PatientRecord(BaseModel):
    hospital_id: str
    bed_number: str
    name: str
    age: int
    primary_diagnosis: str
    medications: List[str]
    allergies: List[str]
    restrictions: List[str]
    primary_nurse_id: str
    attending_physician_id: str

class PatientAnalysisOutput(BaseModel):
    patient_context: str
    intent_category: Literal["MEDICAL", "NON_MEDICAL", "EMERGENCY"]
    urgency_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    distress_flags: List[str]
    conversation_history: List[str]

class PolicyDecision(BaseModel):
    requires_human_approval: bool
    escalation_level: Literal["NONE", "NURSE", "DOCTOR", "EMERGENCY"]
    reasoning: str
    applicable_policies: List[str]

class OrchestratorOutput(BaseModel):
    response_text: str
    action_taken: str
    requires_approval: bool
    staff_notified: List[str]
    audit_log_id: str

class NotificationMessage(BaseModel):
    recipient_ids: List[str]
    message: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AuditLogEntry(BaseModel):
    log_id: str
    timestamp: datetime
    patient_id: str
    query_text: str
    intent_category: str
    policy_decision: PolicyDecision
    response: str
    staff_notified: List[str]
    approval_required: bool
```

---

## 6. Database Schema

### 6.1 Patient Records Table
```sql
CREATE TABLE patient_records (
    id SERIAL PRIMARY KEY,
    hospital_id VARCHAR(50) UNIQUE NOT NULL,
    bed_number VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    age INT,
    primary_diagnosis TEXT,
    medications JSONB,
    allergies JSONB,
    restrictions JSONB,
    primary_nurse_id VARCHAR(50),
    attending_physician_id VARCHAR(50),
    admission_date TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 6.2 Conversation Memory Table
```sql
CREATE TABLE conversation_memory (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    session_id VARCHAR(100),
    query_text TEXT,
    response_text TEXT,
    intent_category VARCHAR(20),
    timestamp TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (patient_id) REFERENCES patient_records(hospital_id)
);
```

### 6.3 Audit Logs Table
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    log_id VARCHAR(100) UNIQUE NOT NULL,
    patient_id VARCHAR(50),
    query_text TEXT,
    intent_category VARCHAR(20),
    urgency_level VARCHAR(20),
    policy_decision JSONB,
    response_text TEXT,
    staff_notified JSONB,
    approval_required BOOLEAN,
    agent_chain TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (patient_id) REFERENCES patient_records(hospital_id)
);
```

### 6.4 Approval Queue Table
```sql
CREATE TABLE approval_queue (
    id SERIAL PRIMARY KEY,
    queue_id VARCHAR(100) UNIQUE NOT NULL,
    patient_id VARCHAR(50),
    request_type VARCHAR(50),
    query_text TEXT,
    status VARCHAR(20) DEFAULT 'PENDING',
    assigned_to VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES patient_records(hospital_id)
);
```

---

## 7. Configuration & Environment

### 7.1 Environment Variables
```bash
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key
MODEL_NAME=gpt-4-turbo-preview  # or gpt-4o
TEMPERATURE=0.3  # Low for deterministic medical responses

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/caremate
REDIS_URL=redis://localhost:6379/0

# Hospital System Integration
HOSPITAL_SYSTEM_API_URL=https://hospital.example.com/api
HOSPITAL_API_KEY=your_hospital_api_key

# External Services
SPEECH_TO_TEXT_API=azure_speech_api
TEXT_TO_SPEECH_API=azure_tts_api
TRANSLATION_API=azure_translator_api

# Notification Services
NOTIFICATION_SERVICE_URL=https://notifications.example.com
SMS_PROVIDER_API_KEY=your_sms_key
EMAIL_SMTP_SERVER=smtp.example.com

# Security
ENCRYPTION_KEY=your_encryption_key
AUDIT_LOG_RETENTION_DAYS=2555  # 7 years for HIPAA

# CrewAI Settings
CREWAI_VERBOSE=true
CREWAI_MEMORY_ENABLED=true
CREWAI_MAX_ITERATIONS=5
```

### 7.2 Hospital Policy Configuration (policies.yaml)
```yaml
medical_approval_required:
  - medication_request
  - pain_management
  - procedure_inquiry
  - symptom_assessment

auto_response_allowed:
  - room_comfort
  - meal_request
  - visitor_information
  - tv_control
  - basic_questions

emergency_keywords:
  critical:
    - "chest pain"
    - "can't breathe"
    - "severe bleeding"
    - "unconscious"
  high:
    - "severe pain"
    - "dizzy"
    - "confused"
    - "vomiting blood"

escalation_rules:
  pain_level_7_plus: "NURSE"
  repeated_request_3_times: "NURSE"
  emergency_keyword: "EMERGENCY"
  medication_request: "NURSE"
  
response_sla:
  emergency: 60  # seconds
  high_urgency: 300  # 5 minutes
  medium_urgency: 900  # 15 minutes
  low_urgency: 1800  # 30 minutes
```

---

## 8. Security & Compliance

### 8.1 HIPAA Compliance
- All patient data encrypted at rest (AES-256)
- TLS 1.3 for data in transit
- Audit logs immutable and retained for 7 years
- Access controls: Role-based with least privilege
- PHI de-identification in logs where possible

### 8.2 Safety Constraints
- Medical advice detection and blocking
- Hallucination mitigation through structured outputs
- Response validation against policies
- Human-in-the-loop for all medical decisions
- Emergency override protocols

### 8.3 Rate Limiting
```python
# Per patient
max_requests_per_minute: 10
max_requests_per_hour: 60

# System-wide
max_concurrent_patient_sessions: 100
max_llm_tokens_per_day: 1000000
```

---

## 9. Deployment Architecture

### 9.1 Infrastructure
```
Production Environment:
- Container: Docker
- Orchestration: Kubernetes
- Load Balancer: NGINX
- Database: PostgreSQL 15+ (primary + replica)
- Cache: Redis Cluster
- Message Queue: RabbitMQ
- Monitoring: Prometheus + Grafana
```

### 9.2 Scaling Strategy
- Horizontal: Multiple CrewAI instances behind load balancer
- Vertical: GPU instances for faster LLM inference
- Database: Read replicas for patient record queries
- Cache: Redis for frequent patient context lookups

### 9.3 Disaster Recovery
- RPO: 15 minutes (Recovery Point Objective)
- RTO: 30 minutes (Recovery Time Objective)
- Backup: Continuous replication + hourly snapshots
- Failover: Automated to standby region

---

## 10. Testing Strategy

### 10.1 Unit Tests
- Individual tool functionality
- Pydantic model validation
- Database operations
- Policy rule evaluation

### 10.2 Integration Tests
- Agent-to-agent communication
- Task output validation
- End-to-end patient query flow
- External API integrations

### 10.3 Safety Tests
- Medical advice detection accuracy (>99%)
- Emergency detection recall (>99.9%)
- Policy compliance verification
- Adversarial prompt testing

### 10.4 Performance Tests
- Response time: <2 seconds for non-medical
- Response time: <5 seconds for medical (to dashboard)
- Concurrent users: 100+ patients simultaneously
- System uptime: 99.9% SLA

---

## 11. Monitoring & Observability

### 11.1 Key Metrics
```
Performance Metrics:
- Average response time
- Agent iteration count
- LLM token usage
- Database query performance

Quality Metrics:
- Intent classification accuracy
- Policy compliance rate
- False emergency rate
- Patient satisfaction score

Safety Metrics:
- Medical advice false positives
- Emergency detection accuracy
- Human override frequency
```

### 11.2 Alerting
```
Critical Alerts:
- Emergency detection failure
- System downtime > 1 minute
- Database connection loss
- Audit log write failure

Warning Alerts:
- Response time > 5 seconds
- Intent classification confidence < 80%
- Staff approval backlog > 10 items
- LLM token quota at 80%
```

---

## 12. Future Enhancements

### Phase 2 Features
1. Multi-language direct support (no translation)
2. Voice emotion detection integration
3. Predictive patient needs (ML-based)
4. Integration with EHR systems (Epic, Cerner)

### Phase 3 Features
1. Automated medication timing reminders
2. Post-discharge follow-up agent
3. Family communication portal
4. Advanced analytics dashboard

---

## 13. Development Timeline

**Phase 1: Core Implementation (8 weeks)**
- Week 1-2: Environment setup, database schema
- Week 3-4: Custom tools development
- Week 5-6: Agent configuration and integration
- Week 7-8: Testing and refinement

**Phase 2: Integration & Testing (4 weeks)**
- Week 9-10: Hospital system integration
- Week 11-12: End-to-end testing, security audit

**Phase 3: Pilot Deployment (4 weeks)**
- Week 13-14: Single ward pilot
- Week 15-16: Monitoring, optimization, feedback

**Phase 4: Full Rollout (4 weeks)**
- Week 17-20: Multi-ward deployment, training, documentation

---

## 14. Success Criteria

### Technical KPIs
- System uptime: >99.9%
- Response accuracy: >95%
- Emergency detection: >99.9% recall
- Medical advice false positive rate: <0.1%

### Business KPIs
- Nurse call reduction: 30%
- Patient satisfaction increase: 20%
- Response time improvement: 50%
- Staff approval time: <5 minutes average

### Safety KPIs
- Zero medical advice incidents
- 100% emergency escalation success
- Zero HIPAA violations
- 100% audit trail completeness

---

## Appendix A: Glossary

- **Intent**: The categorized purpose of a patient's request
- **Urgency**: The time-sensitive nature of a request
- **Escalation**: Routing a request to human staff
- **Policy**: A hospital-defined rule enforced by the system
- **Audit Trail**: Complete record of system decisions and actions
- **Human-in-the-Loop**: Required human approval for decisions
- **Tool**: A specialized function used by an agent
- **Task**: A defined work unit for an agent
- **Crew**: The collection of agents working together

---

## Appendix B: Contact & Support

**Technical Lead**: [Your Name]  
**Project Manager**: [PM Name]  
**Hospital Liaison**: [Hospital Contact]  
**Support Email**: caremate-support@hospital.org  
**Emergency Contact**: +1-XXX-XXX-XXXX

---

**Document Version Control**  
- v1.0 - February 4, 2026 - Initial specification
- Future updates will be tracked in Git repository

**Approval**  
- [ ] Technical Lead
- [ ] Hospital IT Director  
- [ ] Medical Director  
- [ ] Compliance Officer
