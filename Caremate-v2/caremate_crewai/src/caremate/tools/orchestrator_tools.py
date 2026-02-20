"""
Central Orchestrator Agent Tools
Tools for policy evaluation, response generation, notifications, and audit logging
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
import uuid
from datetime import datetime

from ..models import (
    PolicyDecision,
    NotificationMessage,
    AuditLogEntry,
    ApprovalQueueEntry
)


# ============================================================================
# Tool Input Schemas
# ============================================================================

class PolicyEvaluationInput(BaseModel):
    """Input schema for policy evaluation"""
    intent: str = Field(..., description="Classified intent (MEDICAL/NON_MEDICAL/EMERGENCY)")
    urgency: str = Field(..., description="Urgency level (LOW/MEDIUM/HIGH/CRITICAL)")
    patient_context: Dict[str, Any] = Field(..., description="Patient context information")
    distress_level: str = Field(default="NONE", description="Detected distress level")


class ResponseGenerationInput(BaseModel):
    """Input schema for response generation"""
    intent: str = Field(..., description="Request intent")
    patient_context: str = Field(..., description="Patient context summary")
    policy_decision: Dict[str, Any] = Field(..., description="Policy evaluation result")
    original_query: str = Field(..., description="Original patient query")


class NotificationInput(BaseModel):
    """Input schema for staff notification"""
    recipient_ids: List[str] = Field(..., description="Staff IDs to notify")
    message: str = Field(..., description="Notification message")
    priority: str = Field(..., description="Priority level")
    patient_id: str = Field(..., description="Related patient ID")
    request_type: str = Field(..., description="Type of request")


class ApprovalWorkflowInput(BaseModel):
    """Input schema for approval workflow"""
    request_type: str = Field(..., description="Type of request needing approval")
    patient_data: Dict[str, Any] = Field(..., description="Patient information")
    original_query: str = Field(..., description="Patient's request")
    priority: str = Field(default="MEDIUM", description="Request priority")


class AuditLoggingInput(BaseModel):
    """Input schema for audit logging"""
    event_type: str = Field(..., description="Type of event being logged")
    patient_id: str = Field(..., description="Patient hospital ID")
    query_text: str = Field(..., description="Original query")
    intent_category: str = Field(..., description="Classified intent")
    urgency_level: str = Field(..., description="Urgency level")
    policy_decision: Dict[str, Any] = Field(..., description="Policy decision data")
    response_text: str = Field(..., description="Generated response")
    staff_notified: List[str] = Field(default_factory=list)
    approval_required: bool = Field(...)


# ============================================================================
# Custom Tools for Central Orchestrator Agent
# ============================================================================

class PolicyEvaluationTool(BaseTool):
    name: str = "Policy Evaluation"
    description: str = (
        "Evaluates patient requests against hospital policies. "
        "Determines if human approval is needed, what escalation level is required. "
        "Enforces: NO medical advice, ALL medication requests need nurse, "
        "EMERGENCY signals escalate immediately, pain 7+ notifies nurse."
    )
    args_schema: type[BaseModel] = PolicyEvaluationInput

    def _run(
        self,
        intent: str,
        urgency: str,
        patient_context: Dict[str, Any],
        distress_level: str = "NONE"
    ) -> str:
        """
        Evaluate request against hospital policies.
        """
        # Initialize decision
        requires_approval = False
        escalation_level = "NONE"
        applicable_policies = []
        reasoning_parts = []
        estimated_response_time = 60  # seconds
        
        # Policy 1: EMERGENCY escalation
        if intent == "EMERGENCY" or urgency == "CRITICAL":
            requires_approval = False  # Skip approval for emergencies
            escalation_level = "EMERGENCY"
            applicable_policies.append("EMERGENCY_PROTOCOL")
            reasoning_parts.append("Emergency detected - immediate escalation to emergency staff")
            estimated_response_time = 60
        
        # Policy 2: Medical requests require human approval
        elif intent == "MEDICAL":
            requires_approval = True
            escalation_level = "NURSE"
            applicable_policies.append("MEDICAL_REQUEST_APPROVAL_REQUIRED")
            reasoning_parts.append("Medical request requires nurse approval before response")
            estimated_response_time = 300
            
            # Check if doctor needed (high urgency medical)
            if urgency in ["HIGH", "CRITICAL"]:
                escalation_level = "DOCTOR"
                applicable_policies.append("HIGH_URGENCY_DOCTOR_NOTIFICATION")
                reasoning_parts.append("High urgency medical request escalated to doctor")
                estimated_response_time = 180
        
        # Policy 3: Medication requests always need nurse
        query_lower = patient_context.get("original_query", "").lower()
        if any(word in query_lower for word in ["medication", "medicine", "pill", "drug", "painkiller"]):
            requires_approval = True
            escalation_level = "NURSE"
            applicable_policies.append("MEDICATION_REQUEST_NURSE_REQUIRED")
            reasoning_parts.append("Medication-related request requires mandatory nurse approval")
            estimated_response_time = 300
        
        # Policy 4: High distress escalation
        if distress_level in ["MEDIUM", "HIGH"] and escalation_level == "NONE":
            escalation_level = "NURSE"
            applicable_policies.append("DISTRESS_ESCALATION")
            reasoning_parts.append(f"Patient showing {distress_level} distress - notifying nurse")
            estimated_response_time = 180
        
        # Policy 5: Non-medical requests can auto-respond
        if intent == "NON_MEDICAL" and escalation_level == "NONE":
            requires_approval = False
            applicable_policies.append("NON_MEDICAL_AUTO_RESPONSE")
            reasoning_parts.append("Non-medical request approved for automatic response")
            estimated_response_time = 5
        
        # Build policy decision
        decision = {
            "requires_human_approval": requires_approval,
            "escalation_level": escalation_level,
            "reasoning": ". ".join(reasoning_parts) if reasoning_parts else "Standard processing",
            "applicable_policies": applicable_policies,
            "estimated_response_time": estimated_response_time
        }
        
        return json.dumps(decision, indent=2)


class ResponseGenerationTool(BaseTool):
    name: str = "Response Generation"
    description: str = (
        "Generates patient-facing responses based on intent and policy decisions. "
        "Creates empathetic, clear messages that set appropriate expectations. "
        "Never provides medical advice. For approvals, indicates staff will respond. "
        "For non-medical, provides direct helpful answers."
    )
    args_schema: type[BaseModel] = ResponseGenerationInput

    def _run(
        self,
        intent: str,
        patient_context: str,
        policy_decision: Dict[str, Any],
        original_query: str
    ) -> str:
        """
        Generate appropriate patient response.
        """
        escalation = policy_decision.get("escalation_level", "NONE")
        requires_approval = policy_decision.get("requires_human_approval", False)
        
        # Emergency response
        if escalation == "EMERGENCY":
            response = (
                "I've immediately notified the emergency response team. "
                "Someone will be with you right away. Please stay calm and remain where you are."
            )
        
        # Medical/medication requiring approval
        elif requires_approval and escalation in ["NURSE", "DOCTOR"]:
            staff_type = "nurse" if escalation == "NURSE" else "doctor"
            response = (
                f"I understand you need assistance. I've notified your {staff_type} about your request. "
                f"They will be with you shortly to help. Is there anything else I can assist you with "
                f"while you wait?"
            )
        
        # Non-medical auto-response
        elif intent == "NON_MEDICAL":
            query_lower = original_query.lower()
            
            # Room comfort responses
            if "water" in query_lower:
                response = "I'll let your nurse know you'd like some water. They'll bring it to you shortly."
            elif any(word in query_lower for word in ["temperature", "hot", "cold", "warm"]):
                response = (
                    "I can help with that. I'll notify your nurse to adjust the room temperature. "
                    "In the meantime, would you like an extra blanket?"
                )
            elif any(word in query_lower for word in ["tv", "television"]):
                response = "The TV remote should be on your bedside table. If you can't find it, I'll have your nurse bring you one."
            elif any(word in query_lower for word in ["light", "lights"]):
                response = "You can adjust the lights using the control panel on the side of your bed. Would you like me to have your nurse help you with that?"
            elif any(word in query_lower for word in ["visitor", "family"]):
                response = "Visiting hours are from 10 AM to 8 PM daily. Visitors should check in at the nurse's station."
            elif any(word in query_lower for word in ["time", "what time"]):
                response = f"The current time is {datetime.now().strftime('%I:%M %p')}."
            else:
                # Generic helpful response
                response = (
                    "I've noted your request and will let your nurse know. "
                    "They'll assist you as soon as possible."
                )
        
        # Fallback
        else:
            response = (
                "I've received your request and am coordinating with the care team. "
                "Someone will be with you shortly."
            )
        
        return response


class NotificationTool(BaseTool):
    name: str = "Staff Notification"
    description: str = (
        "Sends notifications to hospital staff (nurses, doctors, emergency team). "
        "Supports multiple channels: dashboard alerts, mobile push, SMS for critical. "
        "Returns confirmation of notifications sent."
    )
    args_schema: type[BaseModel] = NotificationInput

    def _run(
        self,
        recipient_ids: List[str],
        message: str,
        priority: str,
        patient_id: str,
        request_type: str
    ) -> str:
        """
        Send notifications to staff members.
        In production, integrate with hospital notification system.
        """
        try:
            # Determine notification channels based on priority
            channels = ["dashboard"]  # Always show on dashboard
            
            if priority in ["HIGH", "CRITICAL"]:
                channels.append("mobile_push")
            
            if priority == "CRITICAL":
                channels.append("sms")
            
            # Create notification records
            notifications_sent = []
            for recipient_id in recipient_ids:
                notification_id = str(uuid.uuid4())
                
                # TODO: Replace with actual notification service integration
                # e.g., send_push_notification(recipient_id, message)
                #      send_sms(recipient_id, message)
                #      update_dashboard_queue(recipient_id, notification_id)
                
                notifications_sent.append({
                    "notification_id": notification_id,
                    "recipient_id": recipient_id,
                    "channels": channels,
                    "status": "SENT",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return json.dumps({
                "sent": True,
                "recipient_count": len(recipient_ids),
                "notifications": notifications_sent,
                "priority": priority,
                "patient_id": patient_id
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "sent": False,
                "error": str(e),
                "recipient_ids": recipient_ids
            })


class ApprovalWorkflowTool(BaseTool):
    name: str = "Approval Workflow"
    description: str = (
        "Creates entries in the staff approval queue for requests requiring human review. "
        "Routes to appropriate staff member, sets SLA timers, enables approve/reject actions. "
        "Returns queue entry ID and assignment details."
    )
    args_schema: type[BaseModel] = ApprovalWorkflowInput

    def _run(
        self,
        request_type: str,
        patient_data: Dict[str, Any],
        original_query: str,
        priority: str = "MEDIUM"
    ) -> str:
        """
        Create approval queue entry.
        """
        try:
            # Generate unique queue ID
            queue_id = f"APR-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
            
            # Determine assignment based on request type
            if "medication" in request_type.lower():
                assigned_to = patient_data.get("primary_nurse_id", "UNASSIGNED")
            elif priority == "CRITICAL":
                assigned_to = patient_data.get("attending_physician_id", "UNASSIGNED")
            else:
                assigned_to = patient_data.get("primary_nurse_id", "UNASSIGNED")
            
            # Create queue entry
            queue_entry = {
                "queue_id": queue_id,
                "patient_id": patient_data.get("hospital_id"),
                "patient_name": patient_data.get("name", "Unknown"),
                "bed_number": patient_data.get("bed_number"),
                "request_type": request_type,
                "query_text": original_query,
                "context_summary": patient_data.get("context_summary", ""),
                "status": "PENDING",
                "assigned_to": assigned_to,
                "created_at": datetime.utcnow().isoformat(),
                "priority": priority,
                "sla_minutes": {
                    "CRITICAL": 5,
                    "HIGH": 15,
                    "MEDIUM": 30,
                    "LOW": 60
                }.get(priority, 30)
            }
            
            # TODO: Store in database
            # db.approval_queue.insert(queue_entry)
            
            return json.dumps({
                "queue_id": queue_id,
                "status": "CREATED",
                "assigned_to": assigned_to,
                "priority": priority,
                "expected_response_time_minutes": queue_entry["sla_minutes"]
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Failed to create approval entry: {str(e)}",
                "request_type": request_type
            })


class AuditLoggingTool(BaseTool):
    name: str = "Audit Logging"
    description: str = (
        "Records all system decisions and actions to immutable audit trail. "
        "Logs: patient query, intent classification, policy decisions, responses, "
        "staff notifications, approvals. Required for HIPAA compliance and transparency."
    )
    args_schema: type[BaseModel] = AuditLoggingInput

    def _run(
        self,
        event_type: str,
        patient_id: str,
        query_text: str,
        intent_category: str,
        urgency_level: str,
        policy_decision: Dict[str, Any],
        response_text: str,
        staff_notified: List[str],
        approval_required: bool
    ) -> str:
        """
        Create audit log entry.
        """
        try:
            # Generate unique log ID
            log_id = f"LOG-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"
            
            # Create comprehensive audit entry
            audit_entry = {
                "log_id": log_id,
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "patient_id": patient_id,
                "query_text": query_text,
                "intent_category": intent_category,
                "urgency_level": urgency_level,
                "policy_decision": policy_decision,
                "response_text": response_text,
                "staff_notified": staff_notified,
                "approval_required": approval_required,
                "agent_chain": "PatientIntelligenceAgent -> OrchestratorAgent",
                "resolution_status": "COMPLETED" if not approval_required else "PENDING"
            }
            
            # TODO: Store in append-only audit database
            # audit_db.insert(audit_entry)
            # Ensure encryption at rest and integrity checks
            
            # Also send to external audit/monitoring system
            # audit_service.send(audit_entry)
            
            return log_id
            
        except Exception as e:
            # Audit logging failure is critical - should trigger alert
            error_log_id = f"ERROR-{str(uuid.uuid4())[:8]}"
            # TODO: Trigger critical alert for audit logging failure
            return error_log_id
