#!/usr/bin/env python3
"""
CareMate IDP (Intelligent Document Processing) Pipeline
Uses Amazon Textract for OCR + structured extraction from medical PDFs.
Extracted data is written back to the patient's MongoDB record.
"""
import os
import re
import json
import logging
import boto3
from botocore.exceptions import ClientError
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional

load_dotenv()
logger = logging.getLogger(__name__)

MONGO_URI  = os.getenv("MONGO_URI")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_KEY    = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.getenv("AWS_SECRET_ACCESS_KEY")


# ── Textract client ───────────────────────────────────────────────────────────

def get_textract_client():
    return boto3.client(
        "textract",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
    )


# ── OCR: extract raw text from a local PDF/image file ────────────────────────

def extract_text_with_textract(file_path: str) -> str:
    """
    Sends a local file to Amazon Textract and returns the full extracted text.
    Supports PDF and image files (PNG, JPEG, TIFF).
    """
    logger.info(f"Sending to Textract: {file_path}")

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    client = get_textract_client()

    try:
        response = client.detect_document_text(
            Document={"Bytes": file_bytes}
        )
    except ClientError as e:
        logger.error(f"Textract error: {e}")
        raise

    lines = []
    for block in response.get("Blocks", []):
        if block["BlockType"] == "LINE":
            lines.append(block.get("Text", ""))

    full_text = "\n".join(lines)
    logger.info(f"Textract extracted {len(lines)} lines, {len(full_text)} chars")
    return full_text


# ── IDP Parser: extract structured medical data from raw text ─────────────────

class MedicalDocumentParser:
    """
    Parses raw OCR text from medical documents and extracts structured fields:
    - medications
    - diagnoses / conditions
    - lab results
    - vitals
    - allergies
    - doctor notes
    """

    # Regex patterns for common medical document sections
    SECTION_PATTERNS = {
        "diagnosis":    re.compile(r"(?:diagnosis|impression|assessment|condition)[:\s]+(.+?)(?=\n[A-Z]|\Z)", re.I | re.S),
        "medications":  re.compile(r"(?:medication|medicine|drug|prescription|rx)[:\s]+(.+?)(?=\n[A-Z]|\Z)", re.I | re.S),
        "allergies":    re.compile(r"(?:allerg(?:y|ies))[:\s]+(.+?)(?=\n[A-Z]|\Z)", re.I | re.S),
        "vitals":       re.compile(r"(?:vital|bp|blood pressure|pulse|temperature|spo2|oxygen)[:\s]+(.+?)(?=\n[A-Z]|\Z)", re.I | re.S),
        "lab_results":  re.compile(r"(?:lab(?:oratory)?|test result|report|parameter)[:\s]+(.+?)(?=\n[A-Z]|\Z)", re.I | re.S),
        "doctor_notes": re.compile(r"(?:note|remark|comment|plan|advice)[:\s]+(.+?)(?=\n[A-Z]|\Z)", re.I | re.S),
    }

    # Patterns for individual values
    VITAL_PATTERNS = {
        "blood_pressure":    re.compile(r"(?:bp|blood pressure)[:\s]+(\d{2,3}/\d{2,3})", re.I),
        "heart_rate":        re.compile(r"(?:pulse|heart rate|hr)[:\s]+(\d{2,3})\s*(?:bpm)?", re.I),
        "temperature":       re.compile(r"(?:temp(?:erature)?)[:\s]+(\d{2,3}(?:\.\d)?)\s*(?:°?[FC])?", re.I),
        "oxygen_saturation": re.compile(r"(?:spo2|oxygen sat(?:uration)?)[:\s]+(\d{2,3})\s*%?", re.I),
        "weight":            re.compile(r"(?:weight|wt)[:\s]+(\d{2,3}(?:\.\d)?)\s*(?:kg)?", re.I),
        "height":            re.compile(r"(?:height|ht)[:\s]+(\d{3,4}(?:\.\d)?)\s*(?:cm)?", re.I),
    }

    # Common medication line pattern: "Drug Name Dose Frequency"
    MED_LINE_PATTERN = re.compile(
        r"([A-Za-z][A-Za-z\s\-]+?)\s+"
        r"(\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|iu|units?))"
        r"(?:\s+(once|twice|thrice|od|bd|tds|qid|sos|prn|daily|weekly|\d+\s*times?))?",
        re.I
    )

    def parse(self, text: str, patient_id: str) -> dict:
        """
        Parse raw OCR text and return a structured dict of extracted medical data.
        Also attempts to extract the patient ID from the document itself.
        """
        result = {
            "patient_id":            patient_id,  # may be overridden below
            "extracted_patient_id":  None,
            "extracted_at":          datetime.now(),
            "raw_text":              text,
            "medications":           [],
            "diagnoses":             [],
            "allergies":             [],
            "vitals":                {},
            "lab_results":           [],
            "doctor_notes":          "",
        }

        # ── Extract patient ID from document ─────────────────────────────────
        extracted_pid = self._extract_patient_id(text)
        if extracted_pid:
            result["extracted_patient_id"] = extracted_pid
            result["patient_id"] = extracted_pid   # override URL-passed ID
            logger.info(f"Patient ID extracted from document: {extracted_pid} (overrides passed ID: {patient_id})")

        # Extract vitals (individual values)
        for field, pattern in self.VITAL_PATTERNS.items():
            m = pattern.search(text)
            if m:
                result["vitals"][field] = m.group(1).strip()

        # Extract medications
        result["medications"] = self._extract_medications(text)

        # Extract diagnoses
        result["diagnoses"] = self._extract_list_section(text, ["diagnosis", "impression", "assessment", "condition"])

        # Extract allergies
        result["allergies"] = self._extract_list_section(text, ["allerg"])

        # Extract lab results
        result["lab_results"] = self._extract_lab_results(text)

        # Extract doctor notes
        result["doctor_notes"] = self._extract_notes(text)

        logger.info(
            f"Parsed document for patient {result['patient_id']}: "
            f"{len(result['medications'])} meds, "
            f"{len(result['diagnoses'])} diagnoses, "
            f"{len(result['vitals'])} vitals, "
            f"{len(result['lab_results'])} lab results"
        )
        return result

    def _extract_patient_id(self, text: str) -> Optional[str]:
        """
        Extract patient ID from document text.
        Handles common formats: PID, Patient ID, MRN, Reg No, etc.
        """
        patterns = [
            re.compile(r"PID\s*[:\-]\s*(\w+)", re.I),
            re.compile(r"Patient\s*ID\s*[:\-]\s*(\w+)", re.I),
            re.compile(r"Patient\s*No\.?\s*[:\-]\s*(\w+)", re.I),
            re.compile(r"MRN\s*[:\-]\s*(\w+)", re.I),
            re.compile(r"Reg(?:istration)?\s*(?:No\.?|Number)\s*[:\-]\s*(\w+)", re.I),
            re.compile(r"UHID\s*[:\-]\s*(\w+)", re.I),
            re.compile(r"IP\s*No\.?\s*[:\-]\s*(\w+)", re.I),
            re.compile(r"OP\s*No\.?\s*[:\-]\s*(\w+)", re.I),
        ]
        for pattern in patterns:
            m = pattern.search(text)
            if m:
                pid = m.group(1).strip()
                # Validate: must be numeric or alphanumeric, reasonable length
                if pid and 1 <= len(pid) <= 20 and re.match(r'^[A-Za-z0-9\-]+$', pid):
                    return pid
        return None

    def _extract_medications(self, text: str) -> list:
        meds = []
        # Find medication section — stop at next ALL-CAPS section header
        section_match = re.search(
            r"(?:medication|medicine|drug|prescription|rx)[s]?[:\s]*\n(.+?)(?=\n[A-Z][A-Z ]{3,}:|\n\n[A-Z]|\Z)",
            text, re.I | re.S
        )
        section_text = section_match.group(1) if section_match else ""

        if not section_text:
            return []

        for line in section_text.split("\n"):
            line = line.strip().lstrip("•-*1234567890. ")
            if not line or len(line) < 3 or len(line) > 80:
                continue
            # Skip lines that are section headers
            if line.endswith(":") or line.isupper():
                continue
            # Try to parse "Drug Dose Frequency"
            m = self.MED_LINE_PATTERN.match(line)
            if m:
                name = m.group(1).strip()
                dose = m.group(2).strip()
                freq = m.group(3).strip() if m.group(3) else ""
                if len(name) > 2 and not name.isupper():
                    meds.append({"name": name, "dosage": dose, "frequency": freq})
            else:
                # Simple name-only line
                meds.append({"name": line, "dosage": "", "frequency": ""})

        return meds[:20]

    def _extract_list_section(self, text: str, keywords: list) -> list:
        pattern = re.compile(
            r"(?:" + "|".join(keywords) + r")[s]?[:\s]*\n(.+?)(?=\n[A-Z][A-Z ]{3,}:|\n\n[A-Z]|\Z)",
            re.I | re.S
        )
        m = pattern.search(text)
        if not m:
            return []
        section = m.group(1)
        items = []
        for line in re.split(r"[,\n;]", section):
            item = line.strip().lstrip("•-*1234567890. ")
            # Skip section headers, empty lines, and lines that are too long
            if (2 < len(item) < 60
                    and not item.endswith(":")
                    and not item.isupper()
                    and not re.match(r"^\d+[\.\)]\s", item)):
                items.append(item)
        return items[:10]

    def _extract_lab_results(self, text: str) -> list:
        results = []
        # Pattern: "Parameter Name   Value   Unit   Reference Range"
        lab_pattern = re.compile(
            r"([A-Za-z][A-Za-z\s\(\)]+?)\s+"
            r"(\d+(?:\.\d+)?)\s*"
            r"([a-zA-Z/%]+)?\s*"
            r"(?:(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?))?",
            re.I
        )
        # Find lab section
        section_match = re.search(
            r"(?:lab(?:oratory)?|test result|report|parameter)[s]?[:\s]+(.+?)(?=\n\n[A-Z]|\Z)",
            text, re.I | re.S
        )
        section_text = section_match.group(1) if section_match else ""

        for m in lab_pattern.finditer(section_text):
            name = m.group(1).strip()
            value = m.group(2)
            unit = m.group(3) or ""
            ref_low = m.group(4) or ""
            ref_high = m.group(5) or ""
            if len(name) > 2 and len(name) < 50:
                results.append({
                    "parameter": name,
                    "value": value,
                    "unit": unit,
                    "reference_range": f"{ref_low}-{ref_high}" if ref_low else "",
                })
        return results[:30]

    def _extract_notes(self, text: str) -> str:
        m = re.search(
            r"(?:note|remark|comment|plan|advice|recommendation)[s]?[:\s]+(.+?)(?=\n\n[A-Z]|\Z)",
            text, re.I | re.S
        )
        if m:
            return m.group(1).strip()[:500]
        return ""


# ── MongoDB updater: write extracted data back to patient record ──────────────

class PatientRecordUpdater:
    """
    Updates the patient's MongoDB record with data extracted from the document.
    Uses $set for vitals and $addToSet/$push for lists to avoid duplicates.
    """

    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client["caremate_db"]

    def update_patient_record(self, patient_id: str, extracted: dict) -> dict:
        """
        Merges extracted document data into the patient's existing record.
        Returns a summary of what was updated.
        """
        patient = self.db.patients.find_one({"patient_id": patient_id})
        if not patient:
            logger.error(f"Patient {patient_id} not found in MongoDB")
            return {"error": f"Patient {patient_id} not found"}

        updates = {}
        summary = {"patient_id": patient_id, "updated_fields": []}

        # 1. Update vitals in the active visit
        if extracted.get("vitals"):
            visit = self.db.visits.find_one({"patient_id": patient_id, "status": "ACTIVE"})
            if visit:
                vitals_update = {f"vitals.{k}": v for k, v in extracted["vitals"].items()}
                self.db.visits.update_one(
                    {"patient_id": patient_id, "status": "ACTIVE"},
                    {"$set": vitals_update}
                )
                summary["updated_fields"].append("vitals")
                logger.info(f"Updated vitals for patient {patient_id}: {extracted['vitals']}")

        # 2. Add new medications (avoid duplicates by name)
        if extracted.get("medications"):
            existing_meds = patient.get("medications", [])
            existing_names = {m.get("name", "").lower() for m in existing_meds if isinstance(m, dict)}
            new_meds = [
                m for m in extracted["medications"]
                if m.get("name", "").lower() not in existing_names
            ]
            if new_meds:
                self.db.patients.update_one(
                    {"patient_id": patient_id},
                    {"$push": {"medications": {"$each": new_meds}}}
                )
                summary["updated_fields"].append(f"medications (+{len(new_meds)})")
                logger.info(f"Added {len(new_meds)} medications for patient {patient_id}")

        # 3. Add new diagnoses to chronic_conditions
        if extracted.get("diagnoses"):
            existing_conditions = [c.lower() for c in patient.get("chronic_conditions", [])]
            new_conditions = [
                d for d in extracted["diagnoses"]
                if d.lower() not in existing_conditions
            ]
            if new_conditions:
                self.db.patients.update_one(
                    {"patient_id": patient_id},
                    {"$addToSet": {"chronic_conditions": {"$each": new_conditions}}}
                )
                summary["updated_fields"].append(f"chronic_conditions (+{len(new_conditions)})")

        # 4. Add new allergies
        if extracted.get("allergies"):
            existing_allergies = [a.lower() for a in patient.get("allergies", [])]
            new_allergies = [
                a for a in extracted["allergies"]
                if a.lower() not in existing_allergies
            ]
            if new_allergies:
                self.db.patients.update_one(
                    {"patient_id": patient_id},
                    {"$addToSet": {"allergies": {"$each": new_allergies}}}
                )
                summary["updated_fields"].append(f"allergies (+{len(new_allergies)})")

        # 5. Store lab results in documents collection
        if extracted.get("lab_results"):
            # Find the most recent document for this patient and update it
            latest_doc = self.db.documents.find_one(
                {"patient_id": patient_id},
                sort=[("uploaded_at", -1)]
            )
            if latest_doc:
                self.db.documents.update_one(
                    {"_id": latest_doc["_id"]},
                    {"$set": {
                        "lab_results": extracted["lab_results"],
                        "extracted_at": extracted["extracted_at"],
                    }}
                )
            summary["updated_fields"].append(f"lab_results ({len(extracted['lab_results'])} entries)")

        # 6. Store doctor notes in summaries
        if extracted.get("doctor_notes"):
            self.db.summaries.insert_one({
                "patient_id": patient_id,
                "generated_at": extracted["extracted_at"],
                "source": "IDP_TEXTRACT",
                "patient_concerns": "",
                "request_history": "",
                "doctor_notes": extracted["doctor_notes"],
                "raw_text_snippet": extracted["raw_text"][:500],
            })
            summary["updated_fields"].append("doctor_notes")

        # 7. Mark document as fully processed
        latest_doc = self.db.documents.find_one(
            {"patient_id": patient_id},
            sort=[("uploaded_at", -1)]
        )
        if latest_doc:
            self.db.documents.update_one(
                {"_id": latest_doc["_id"]},
                {"$set": {"status": "PROCESSED", "idp_processed_at": datetime.now()}}
            )

        logger.info(f"Patient {patient_id} record updated: {summary['updated_fields']}")
        return summary


# ── Main IDP Pipeline ─────────────────────────────────────────────────────────

class IDPPipeline:
    """
    Full IDP pipeline:
    1. OCR via Amazon Textract
    2. Parse structured medical data
    3. Update patient MongoDB record
    4. Re-index ChromaDB for RAG
    """

    def __init__(self):
        self.parser  = MedicalDocumentParser()
        self.updater = PatientRecordUpdater()

    def process_document(self, file_path: str, patient_id: str) -> dict:
        """
        Full pipeline: file → Textract → parse → MongoDB update → ChromaDB index
        Returns a summary of what was extracted and updated.
        """
        logger.info(f"IDP Pipeline starting for patient {patient_id}, file: {file_path}")
        result = {
            "patient_id": patient_id,
            "file": os.path.basename(file_path),
            "status": "processing",
            "ocr_chars": 0,
            "updated_fields": [],
            "error": None,
        }

        try:
            # Step 1: OCR
            raw_text = extract_text_with_textract(file_path)
            result["ocr_chars"] = len(raw_text)

            if not raw_text.strip():
                result["status"] = "empty_document"
                result["error"] = "Textract returned no text"
                return result

            # Step 2: Parse (may override patient_id from document)
            extracted = self.parser.parse(raw_text, patient_id)

            # Use the patient ID found in the document if different
            actual_patient_id = extracted["patient_id"]
            if actual_patient_id != patient_id:
                logger.info(f"Using document patient ID '{actual_patient_id}' instead of URL patient ID '{patient_id}'")
                result["patient_id"] = actual_patient_id
                result["original_patient_id"] = patient_id

                # Update the document record in MongoDB to correct patient ID
                from pymongo import MongoClient
                db = MongoClient(MONGO_URI)["caremate_db"]
                db.documents.update_one(
                    {"patient_id": patient_id, "status": "INDEXED"},
                    {"$set": {"patient_id": actual_patient_id, "corrected_from": patient_id}},
                    sort=[("uploaded_at", -1)] if False else None  # use find+update
                )
                # Proper way without sort in update_one
                latest = db.documents.find_one({"patient_id": patient_id}, sort=[("uploaded_at", -1)])
                if latest:
                    db.documents.update_one(
                        {"_id": latest["_id"]},
                        {"$set": {"patient_id": actual_patient_id, "corrected_from": patient_id}}
                    )

            # Step 3: Update MongoDB with correct patient ID
            update_summary = self.updater.update_patient_record(actual_patient_id, extracted)
            result["updated_fields"] = update_summary.get("updated_fields", [])

            # Step 4: Medical Analysis — flag abnormals, AI interpretation, patient history
            try:
                from medical_analyzer import get_medical_analyzer
                analyzer = get_medical_analyzer()
                analysis = analyzer.analyze(extracted, actual_patient_id)
                result["abnormal_flags"]    = analysis.get("abnormal_flags", [])
                result["ai_interpretation"] = analysis.get("ai_interpretation", "")
                result["history_id"]        = analysis.get("history_id", "")
                result["critical_count"]    = analysis.get("summary", {}).get("critical_count", 0)
                logger.info(
                    f"Medical analysis complete: {len(result['abnormal_flags'])} abnormal flags, "
                    f"history_id={result['history_id']}"
                )
            except Exception as e:
                logger.warning(f"Medical analysis failed (non-critical): {e}")

            # Step 4: Re-index ChromaDB (non-critical — skip if it fails)
            try:
                from rag_pipeline import CareMateRAG
                rag = CareMateRAG()
                rag.index_reports()
                result["rag_indexed"] = True
            except Exception as e:
                logger.warning(f"ChromaDB re-index skipped (non-critical): {e}")
                result["rag_indexed"] = False

            result["status"] = "success"
            logger.info(f"IDP Pipeline complete for patient {patient_id}: {result}")

        except Exception as e:
            logger.error(f"IDP Pipeline error: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def process_document_fallback(self, file_path: str, patient_id: str) -> dict:
        """
        Fallback pipeline using pypdf when Textract is unavailable.
        """
        logger.info(f"Using pypdf fallback for patient {patient_id}")
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            raw_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            return {"status": "error", "error": str(e)}

        extracted = self.parser.parse(raw_text, patient_id)
        actual_patient_id = extracted["patient_id"]
        update_summary = self.updater.update_patient_record(actual_patient_id, extracted)

        # Medical analysis
        try:
            from medical_analyzer import get_medical_analyzer
            analyzer = get_medical_analyzer()
            analysis = analyzer.analyze(extracted, actual_patient_id)
        except Exception as e:
            logger.warning(f"Medical analysis failed in fallback: {e}")
            analysis = {}

        return {
            "patient_id":        actual_patient_id,
            "status":            "success_fallback",
            "ocr_chars":         len(raw_text),
            "updated_fields":    update_summary.get("updated_fields", []),
            "abnormal_flags":    analysis.get("abnormal_flags", []),
            "ai_interpretation": analysis.get("ai_interpretation", ""),
            "history_id":        analysis.get("history_id", ""),
            "note":              "Used pypdf fallback (Textract unavailable)",
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
_pipeline = None

def get_idp_pipeline() -> IDPPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = IDPPipeline()
    return _pipeline


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python idp_pipeline.py <pdf_path> <patient_id>")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO)
    pipeline = IDPPipeline()
    result = pipeline.process_document(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2, default=str))
