import os
import uuid
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
from main import CareMateBackend
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize FastAPI App
app = FastAPI(title="CareMate AI Production API", description="Hospital Assistant Chat & Voice Backend")

# Initialize Backend Core
backend = CareMateBackend()

# --- Data Models ---

class ChatRequest(BaseModel):
    patient_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    transcript: Optional[str] = None
    response_text: str
    response_audio_url: Optional[str] = None
    intent: str

# --- API Endpoints ---

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Production-grade text chat endpoint."""
    logger.info(f"API Chat Request received for Patient: {request.patient_id}")
    
    try:
        # Process input through the multi-model agent pipeline
        # We also want to capture the intent for the UI
        classification = backend.router.classify(request.message)
        result_text = backend.process_input(request.message, request.patient_id)
        
        # Generate audio for the response
        audio_path = backend.speech.tts(result_text)
        
        return ChatResponse(
            session_id=str(uuid.uuid4()),
            response_text=result_text,
            response_audio_url=audio_path,
            intent=classification['intent']
        )
    except Exception as e:
        logger.error(f"Chat API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice", response_model=ChatResponse)
async def voice_endpoint(patient_id: str, file: UploadFile = File(...)):
    """Production-grade voice interaction endpoint."""
    logger.info(f"API Voice Request received for Patient: {patient_id}")
    
    # Save temporary audio file
    temp_filename = f"temp_{uuid.uuid4()}.mp3"
    temp_path = os.path.join("generated_audio", temp_filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            buffer.write(await file.read())
        
        # Process through the voice pipeline
        result = backend.process_voice_input(temp_path, patient_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        classification = backend.router.classify(result['transcript'])

        return ChatResponse(
            session_id=str(uuid.uuid4()),
            transcript=result['transcript'],
            response_text=result['response_text'],
            response_audio_url=result['response_audio'],
            intent=classification['intent']
        )
    except Exception as e:
        logger.error(f"Voice API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/health")
async def health_check():
    return {"status": "online", "database": "connected", "agents": "ready"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
