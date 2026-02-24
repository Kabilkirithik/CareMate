"""
CareMate Main Application
FastAPI server for the CareMate system
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv
import logging

from caremate.crew import CareMateCrew
from caremate.models import (
    PatientAnalysisOutput,
    OrchestratorOutput
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CareMate API",
    description="Two-Agent Hospital Patient Assistant API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize CrewAI crew
caremate_crew = CareMateCrew()


# ============================================================================
# Request/Response Models
# ============================================================================

class PatientQueryRequest(BaseModel):
    """Request model for patient query"""
    query: str
    hospital_id: str
    bed_number: str
    language: Optional[str] = "en"


class PatientQueryResponse(BaseModel):
    """Response model for patient query"""
    success: bool
    response_text: str
    action_taken: str
    requires_approval: bool
    staff_notified: list[str]
    audit_log_id: str
    patient_analysis: Optional[Dict[str, Any]] = None
    orchestrator_output: Optional[Dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    environment: str


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=HealthCheckResponse)
async def root():
    """Root endpoint - health check"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }


@app.post("/api/v1/patient/query", response_model=PatientQueryResponse)
async def process_patient_query(request: PatientQueryRequest):
    """
    Process a patient query through the CareMate crew
    
    This is the main endpoint for patient interactions.
    In production, this would be called after speech-to-text and translation.
    """
    try:
        logger.info(f"Processing query for patient {request.hospital_id} in bed {request.bed_number}")
        
        # Process through CrewAI
        result = caremate_crew.process_patient_query(
            query=request.query,
            hospital_id=request.hospital_id,
            bed_number=request.bed_number
        )
        
        # Extract results (structure depends on CrewAI output format)
        # This is a simplified version - adjust based on actual CrewAI output
        return PatientQueryResponse(
            success=True,
            response_text=result.get("response_text", "I apologize, I encountered an error."),
            action_taken=result.get("action_taken", "Query processed"),
            requires_approval=result.get("requires_approval", False),
            staff_notified=result.get("staff_notified", []),
            audit_log_id=result.get("audit_log_id", ""),
            patient_analysis=result.get("patient_analysis"),
            orchestrator_output=result.get("orchestrator_output")
        )
        
    except Exception as e:
        logger.error(f"Error processing patient query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@app.post("/api/v1/patient/voice-query")
async def process_voice_query(
    hospital_id: str,
    bed_number: str,
    language: str = "en",
    background_tasks: BackgroundTasks = None
):
    """
    Process a voice query (with speech-to-text and translation)
    
    In production, this would:
    1. Receive audio input
    2. Convert to text via Azure Speech
    3. Translate to English if needed
    4. Process through CareMate crew
    5. Translate response back
    6. Convert to speech
    """
    # TODO: Implement full voice pipeline
    return {
        "status": "not_implemented",
        "message": "Voice query processing to be implemented with Azure Speech Services"
    }


@app.get("/api/v1/patient/{hospital_id}/history")
async def get_patient_history(hospital_id: str):
    """
    Retrieve conversation history for a patient
    """
    # TODO: Implement history retrieval from memory store
    return {
        "hospital_id": hospital_id,
        "history": [],
        "message": "History retrieval to be implemented"
    }


@app.get("/api/v1/staff/approval-queue")
async def get_approval_queue(staff_id: Optional[str] = None):
    """
    Get pending approval requests for staff dashboard
    """
    # TODO: Implement approval queue retrieval
    return {
        "queue": [],
        "count": 0,
        "message": "Approval queue to be implemented"
    }


@app.post("/api/v1/staff/approval/{queue_id}/approve")
async def approve_request(queue_id: str, staff_id: str, notes: Optional[str] = None):
    """
    Approve a pending patient request
    """
    # TODO: Implement approval workflow
    return {
        "queue_id": queue_id,
        "status": "approved",
        "approved_by": staff_id,
        "message": "Approval workflow to be implemented"
    }


@app.post("/api/v1/staff/approval/{queue_id}/reject")
async def reject_request(queue_id: str, staff_id: str, reason: str):
    """
    Reject a pending patient request
    """
    # TODO: Implement rejection workflow
    return {
        "queue_id": queue_id,
        "status": "rejected",
        "rejected_by": staff_id,
        "reason": reason,
        "message": "Rejection workflow to be implemented"
    }


@app.get("/api/v1/metrics")
async def get_metrics():
    """
    Get system metrics for monitoring
    """
    # TODO: Implement metrics collection
    return {
        "active_sessions": 0,
        "pending_approvals": 0,
        "emergency_escalations_today": 0,
        "average_response_time_ms": 0
    }


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("CareMate API starting up...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"CrewAI version: {os.getenv('CREWAI_VERSION', 'unknown')}")
    
    # TODO: Initialize database connections
    # TODO: Initialize Redis connection
    # TODO: Warm up LLM models
    
    logger.info("CareMate API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("CareMate API shutting down...")
    
    # TODO: Close database connections
    # TODO: Close Redis connection
    # TODO: Flush audit logs
    
    logger.info("CareMate API shut down successfully")


# ============================================================================
# Run Application
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
