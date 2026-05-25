from crewai.tools import BaseTool
import json
from pydantic import BaseModel, Field
from typing import Type, Optional, ClassVar
import requests
import base64
import os


# -----------------------------
# Input Schema
# -----------------------------
class OCRSubmissionInput(BaseModel):
    patient_id: str = Field(..., description="Patient ID")
    file_path: str = Field(..., description="Path to image or PDF")
    document_type: Optional[str] = Field(None, description="Optional document type hint")


# -----------------------------
# OCR Submission Tool
# -----------------------------
class OCRSubmissionTool(BaseTool):

    name: str = "OCR Submission Tool"
    description: str = "Submit hospital documents to OCR microservice."

    args_schema: Type[OCRSubmissionInput] = OCRSubmissionInput

    OCR_SERVICE_URL: ClassVar[str] = "http://localhost:8001/ocr/submit"

    def _run(self, patient_id: str, file_path: str, document_type: Optional[str] = None):

        try:

            # Detect file type
            file_extension = os.path.splitext(file_path)[1].lower()

            if file_extension not in [".jpg", ".jpeg", ".png", ".pdf"]:
                return json.dumps({
                    "status": "error",
                    "message": "Unsupported file type. Only images and PDFs allowed."
                })

            # Read file and encode
            with open(file_path, "rb") as f:
                encoded_document = base64.b64encode(f.read()).decode("utf-8")

            payload = {
                "patient_id": patient_id,
                "file_type": file_extension.replace(".", ""),
                "document_base64": encoded_document,
                "document_type": document_type
            }

            response = requests.post(self.OCR_SERVICE_URL, json=payload)

            if response.status_code == 200:
                return json.dumps(response.json())

            return json.dumps({
                "status": "error",
                "message": "OCR submission failed",
                "details": response.text
            })

        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })