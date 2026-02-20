"""
CareMate Data Models
Pydantic models for type safety and validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class PatientRecord(BaseModel):
    """Complete patient record from hospital system"""
    hospital_id: str = Field(..., description="Unique hospital patient identifier")
    bed_number: str = Field(..., description="Current bed assignment")
    name: str = Field(..., description="Patient name")
    age: int = Field(..., ge=0, le=150, description="Patient age")
    primary_diagnosis: str = Field(..., description="Primary diagnosis (non-sensitive summary)")
    medications: List[str] = Field(default_factory=list, description="Current medications")
    allergies: List[str] = Field(default_factory=list, description="Known allergies")
    restrictions: List[str] = Field(default_factory=list, description="Activity/dietary restrictions")
    primary_nurse_id: str = Field(..., description="Assigned primary nurse ID")
    attending_physician_id: str = Field(..., description="Attending physician ID")
    admission_date: Optional[datetime] = None
    language_preference: str = Field(default="en", description="Patient's preferred language")


class PatientAnalysisOutput(BaseModel):
    """Output from Patient Intelligence Agent"""
    patient_context: str = Field(..., description="Summarized relevant patient information")
    intent_category: Literal["MEDICAL", "NON_MEDICAL", "EMERGENCY"] = Field(
        ..., description="Classified intent of patient request"
    )
    urgency_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        ..., description="Urgency level of the request"
    )
    distress_flags: List[str] = Field(
        default_factory=list, description="Detected distress indicators"
    )
    conversation_history: List[str] = Field(
        default_factory=list, description="Recent relevant interactions"
    )
    confidence_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in classification"
    )


class PolicyDecision(BaseModel):
    """Decision output from policy evaluation"""
    requires_human_approval: bool = Field(..., description="Whether human approval is needed")
    escalation_level: Literal["NONE", "NURSE", "DOCTOR", "EMERGENCY"] = Field(
        ..., description="Level of staff escalation required"
    )
    reasoning: str = Field(..., description="Explanation for the decision")
    applicable_policies: List[str] = Field(
        default_factory=list, description="Hospital policies that apply"
    )
    estimated_response_time: int = Field(
        default=300, description="Expected response time in seconds"
    )


class OrchestratorOutput(BaseModel):
    """Final output from Central Orchestrator Agent"""
    response_text: str = Field(..., description="Patient-facing response message")
    action_taken: str = Field(..., description="Description of system action")
    requires_approval: bool = Field(..., description="Whether staff approval is pending")
    staff_notified: List[str] = Field(
        default_factory=list, description="Staff IDs that were notified"
    )
    audit_log_id: str = Field(..., description="Reference to audit log entry")
    approval_queue_id: Optional[str] = Field(
        None, description="ID if added to approval queue"
    )


class NotificationMessage(BaseModel):
    """Notification to be sent to staff"""
    recipient_ids: List[str] = Field(..., description="Staff member IDs to notify")
    message: str = Field(..., description="Notification message content")
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        ..., description="Notification priority level"
    )
    patient_id: str = Field(..., description="Related patient ID")
    request_type: str = Field(..., description="Type of patient request")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    notification_channels: List[str] = Field(
        default_factory=lambda: ["dashboard"], description="Delivery channels"
    )


class AuditLogEntry(BaseModel):
    """Complete audit trail entry"""
    log_id: str = Field(..., description="Unique log identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    patient_id: str = Field(..., description="Patient hospital ID")
    query_text: str = Field(..., description="Original patient query")
    intent_category: str = Field(..., description="Classified intent")
    urgency_level: str = Field(..., description="Assessed urgency")
    policy_decision: PolicyDecision = Field(..., description="Policy evaluation result")
    response_text: str = Field(..., description="Generated response")
    staff_notified: List[str] = Field(default_factory=list)
    approval_required: bool = Field(...)
    agent_chain: str = Field(..., description="Agent execution path")
    resolution_status: Literal["COMPLETED", "PENDING", "ESCALATED"] = Field(
        default="PENDING"
    )


class ApprovalQueueEntry(BaseModel):
    """Entry in staff approval queue"""
    queue_id: str = Field(..., description="Unique queue entry ID")
    patient_id: str = Field(..., description="Patient hospital ID")
    patient_name: str = Field(..., description="Patient name for display")
    bed_number: str = Field(..., description="Bed number")
    request_type: str = Field(..., description="Type of request")
    query_text: str = Field(..., description="Original patient request")
    context_summary: str = Field(..., description="Relevant patient context")
    status: Literal["PENDING", "APPROVED", "REJECTED"] = Field(default="PENDING")
    assigned_to: str = Field(..., description="Staff ID assigned to review")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(default="MEDIUM")


class DistressSignals(BaseModel):
    """Output from distress detection"""
    distress_detected: bool = Field(..., description="Whether distress was detected")
    distress_level: Literal["NONE", "LOW", "MEDIUM", "HIGH"] = Field(
        default="NONE", description="Level of detected distress"
    )
    indicators: List[str] = Field(
        default_factory=list, description="Specific distress indicators found"
    )
    recommended_action: str = Field(
        default="", description="Recommended system action"
    )


class ConversationTurn(BaseModel):
    """Single conversation turn for memory"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    query: str = Field(..., description="Patient query")
    response: str = Field(..., description="System response")
    intent: str = Field(..., description="Classified intent")
    resolved: bool = Field(default=False, description="Whether request was fulfilled")


class SystemHealthMetrics(BaseModel):
    """System health and performance metrics"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    active_sessions: int = Field(default=0)
    average_response_time_ms: float = Field(default=0.0)
    pending_approvals: int = Field(default=0)
    emergency_escalations_today: int = Field(default=0)
    llm_tokens_used_today: int = Field(default=0)
    system_uptime_percent: float = Field(default=100.0, ge=0.0, le=100.0)
