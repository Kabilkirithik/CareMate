#!/usr/bin/env python3
"""
CareMate Medical Analyzer
Processes extracted document data through AI to generate clinical insights
and stores them as structured patient history entries in MongoDB.
"""
import os
import re
import logging
from datetime import datetime
from typing import Optional
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI")

# ── Reference ranges for common lab tests ────────────────────────────────────
LAB_REFERENCE_RANGES = {
    # CBC
    "hemoglobin":           {"male": (13.0, 17.0), "female": (12.0, 15.5), "unit": "g/dL"},
    "hb":                   {"male": (13.0, 17.0), "female": (12.0, 15.5), "unit": "g/dL"},
    "rbc":                  {"male": (4.5, 5.5),   "female": (4.0, 5.0),   "unit": "mill/cumm"},
    "wbc":                  {"both": (4000, 11000), "unit": "cumm"},
    "platelet":             {"both": (150000, 410000), "unit": "cumm"},
    "pcv":                  {"male": (40, 50),      "female": (36, 46),     "unit": "%"},
    "mcv":                  {"both": (83, 101),     "unit": "fL"},
    "mch":                  {"both": (27, 32),      "unit": "pg"},
    "mchc":                 {"both": (32.5, 34.5),  "unit": "g/dL"},
    "rdw":                  {"both": (11.6, 14.0),  "unit": "%"},
    "neutrophils":          {"both": (50, 62),      "unit": "%"},
    "lymphocytes":          {"both": (20, 40),      "unit": "%"},
    "eosinophils":          {"both": (0, 6),        "unit": "%"},
    "monocytes":            {"both": (0, 10),       "unit": "%"},
    "basophils":            {"both": (0, 2),        "unit": "%"},
    # Metabolic
    "glucose":              {"both": (70, 100),     "unit": "mg/dL"},
    "fasting glucose":      {"both": (70, 100),     "unit": "mg/dL"},
    "hba1c":                {"both": (4.0, 5.6),    "unit": "%"},
    "creatinine":           {"male": (0.6, 1.2),    "female": (0.5, 1.1),  "unit": "mg/dL"},
    "urea":                 {"both": (7, 20),       "unit": "mg/dL"},
    "sodium":               {"both": (136, 145),    "unit": "mEq/L"},
    "potassium":            {"both": (3.5, 5.0),    "unit": "mEq/L"},
    "cholesterol":          {"both": (0, 200),      "unit": "mg/dL"},
    "triglycerides":        {"both": (0, 150),      "unit": "mg/dL"},
    "hdl":                  {"both": (40, 60),      "unit": "mg/dL"},
    "ldl":                  {"both": (0, 100),      "unit": "mg/dL"},
    # Liver
    "sgpt":                 {"both": (7, 56),       "unit": "U/L"},
    "alt":                  {"both": (7, 56),       "unit": "U/L"},
    "sgot":                 {"both": (10, 40),      "unit": "U/L"},
    "ast":                  {"both": (10, 40),      "unit": "U/L"},
    "bilirubin":            {"both": (0.1, 1.2),    "unit": "mg/dL"},
    # Thyroid
    "tsh":                  {"both": (0.4, 4.0),    "unit": "mIU/L"},
    "t3":                   {"both": (80, 200),     "unit": "ng/dL"},
    "t4":                   {"both": (5.0, 12.0),   "unit": "ug/dL"},
}


class MedicalAnalyzer:
    """
    Analyzes extracted lab results and generates:
    1. Abnormal value flags with clinical significance
    2. AI-generated clinical summary via Meditron/OpenRouter
    3. Structured patient history entry in MongoDB
    """

    def __init__(self):
        self.db = MongoClient(MONGO_URI)["caremate_db"]

    def analyze(self, extracted: dict, patient_id: str) -> dict:
        """
        Full analysis pipeline:
        1. Flag abnormal values
        2. Generate AI clinical summary
        3. Store as patient history entry
        Returns the complete analysis result.
        """
        logger.info(f"Starting medical analysis for patient {patient_id}")

        # Get patient demographics for context
        patient = self.db.patients.find_one({"patient_id": patient_id}, {"_id": 0})
        gender = patient.get("gender", "unknown").lower() if patient else "unknown"
        age    = patient.get("age", 0) if patient else 0

        # Step 1: Flag abnormal values
        flags = self._flag_abnormal_values(extracted.get("lab_results", []), gender)

        # Step 2: Build structured summary
        summary = self._build_structured_summary(extracted, flags, patient, age)

        # Step 3: Generate AI clinical interpretation
        ai_interpretation = self._generate_ai_interpretation(summary, patient)

        # Step 4: Store as patient history
        history_entry = self._store_patient_history(
            patient_id, extracted, flags, summary, ai_interpretation
        )

        result = {
            "patient_id":        patient_id,
            "abnormal_flags":    flags,
            "summary":           summary,
            "ai_interpretation": ai_interpretation,
            "history_id":        history_entry,
        }

        logger.info(
            f"Analysis complete for patient {patient_id}: "
            f"{len(flags)} abnormal values, history entry created"
        )
        return result

    def _flag_abnormal_values(self, lab_results: list, gender: str) -> list:
        """Compare lab values against reference ranges and flag abnormals."""
        flags = []

        for result in lab_results:
            # Clean parameter name — take only the last meaningful line
            raw_param = result.get("parameter", "")
            # Split on newlines and take the last non-empty line
            param_lines = [l.strip() for l in raw_param.split("\n") if l.strip()]
            param = param_lines[-1].lower() if param_lines else raw_param.lower()
            param = param.strip()
            try:
                value = float(re.sub(r"[^\d.]", "", str(result.get("value", ""))))
            except (ValueError, TypeError):
                continue

            # Find matching reference range
            ref = None
            for key in LAB_REFERENCE_RANGES:
                if key in param or param in key:
                    ref = LAB_REFERENCE_RANGES[key]
                    break

            if not ref:
                continue

            # Get range based on gender
            if "male" in ref and gender in ("male", "m"):
                low, high = ref["male"]
            elif "female" in ref and gender in ("female", "f"):
                low, high = ref["female"]
            elif "both" in ref:
                low, high = ref["both"]
            else:
                continue

            unit = ref.get("unit", result.get("unit", ""))

            if value < low:
                severity = "critical" if value < low * 0.7 else "low"
                # Clean parameter name for display
                display_param = param_lines[-1] if param_lines else result.get("parameter", "")
                flags.append({
                    "parameter": display_param,
                    "value":     value,
                    "unit":      unit,
                    "status":    "LOW",
                    "severity":  severity,
                    "reference": f"{low} - {high} {unit}",
                    "deviation": f"{round(((low - value) / low) * 100, 1)}% below normal",
                })
            elif value > high:
                severity = "critical" if value > high * 1.5 else "high"
                display_param = param_lines[-1] if param_lines else result.get("parameter", "")
                flags.append({
                    "parameter": display_param,
                    "value":     value,
                    "unit":      unit,
                    "status":    "HIGH",
                    "severity":  severity,
                    "reference": f"{low} - {high} {unit}",
                    "deviation": f"{round(((value - high) / high) * 100, 1)}% above normal",
                })

        return flags

    def _build_structured_summary(self, extracted: dict, flags: list,
                                   patient: Optional[dict], age: int) -> dict:
        """Build a structured clinical summary from extracted data."""
        critical_flags = [f for f in flags if f.get("severity") == "critical"]
        abnormal_flags = [f for f in flags if f.get("severity") != "critical"]

        return {
            "patient_name":      patient.get("name", "Unknown") if patient else "Unknown",
            "age":               age,
            "gender":            patient.get("gender", "Unknown") if patient else "Unknown",
            "report_date":       extracted.get("extracted_at", datetime.now()).isoformat()
                                 if hasattr(extracted.get("extracted_at"), "isoformat")
                                 else str(extracted.get("extracted_at", "")),
            "total_tests":       len(extracted.get("lab_results", [])),
            "abnormal_count":    len(flags),
            "critical_count":    len(critical_flags),
            "critical_values":   [f"{f['parameter']}: {f['value']} {f['unit']} ({f['status']})"
                                  for f in critical_flags],
            "abnormal_values":   [f"{f['parameter']}: {f['value']} {f['unit']} ({f['status']})"
                                  for f in abnormal_flags],
            "vitals":            extracted.get("vitals", {}),
            "medications":       [m.get("name", "") for m in extracted.get("medications", [])],
            "diagnoses":         extracted.get("diagnoses", []),
            "doctor_notes":      extracted.get("doctor_notes", ""),
        }

    def _generate_ai_interpretation(self, summary: dict, patient: Optional[dict]) -> str:
        """Generate clinical interpretation using Meditron or OpenRouter."""
        # Build a concise prompt
        abnormal_text = ""
        if summary["critical_values"]:
            abnormal_text += f"CRITICAL: {', '.join(summary['critical_values'])}. "
        if summary["abnormal_values"]:
            abnormal_text += f"Abnormal: {', '.join(summary['abnormal_values'][:5])}. "

        conditions = ", ".join(patient.get("chronic_conditions", [])) if patient else ""
        allergies  = ", ".join(patient.get("allergies", [])) if patient else ""

        prompt = (
            f"Patient: {summary['patient_name']}, Age {summary['age']}, {summary['gender']}. "
            f"Chronic conditions: {conditions or 'None'}. "
            f"Lab report summary: {summary['total_tests']} tests, "
            f"{summary['abnormal_count']} abnormal. "
            f"{abnormal_text}"
            f"Vitals: {summary['vitals']}. "
            f"Doctor notes: {summary['doctor_notes'][:100] if summary['doctor_notes'] else 'None'}. "
            f"Provide a brief clinical interpretation (3-4 sentences) and recommended actions. "
            f"Answer:"
        )

        # Try Meditron first
        try:
            from meditron_client import MeditronClient
            client = MeditronClient()
            if client.health_check():
                response = client.generate_response(prompt, max_tokens=120, temperature=0.2)
                # Extract clean response
                if "Answer:" in response:
                    response = response.split("Answer:")[-1].strip()
                # Take first 3 sentences
                sentences = re.split(r'(?<=[.!?])\s', response.strip())
                clean = " ".join(sentences[:3]).strip()
                if len(clean) > 20:
                    logger.info("AI interpretation generated via Meditron")
                    return clean
        except Exception as e:
            logger.warning(f"Meditron unavailable for analysis: {e}")

        # Fallback to OpenRouter
        try:
            from openrouter_client import generate_openrouter_response
            response = generate_openrouter_response(prompt, max_tokens=120)
            if response and len(response) > 20:
                logger.info("AI interpretation generated via OpenRouter")
                return response.strip()
        except Exception as e:
            logger.warning(f"OpenRouter unavailable for analysis: {e}")

        # Rule-based fallback
        return self._rule_based_interpretation(summary)

    def _rule_based_interpretation(self, summary: dict) -> str:
        """Generate a rule-based interpretation when AI is unavailable."""
        parts = []

        if summary["critical_count"] > 0:
            parts.append(
                f"URGENT: {summary['critical_count']} critical value(s) detected — "
                f"immediate medical review required."
            )
        elif summary["abnormal_count"] > 0:
            parts.append(
                f"{summary['abnormal_count']} abnormal value(s) found out of "
                f"{summary['total_tests']} tests performed."
            )
        else:
            parts.append(f"All {summary['total_tests']} test values are within normal range.")

        if summary["critical_values"]:
            parts.append(f"Critical findings: {', '.join(summary['critical_values'][:2])}.")

        if summary["abnormal_values"]:
            parts.append(f"Notable findings: {', '.join(summary['abnormal_values'][:3])}.")

        if summary["doctor_notes"]:
            parts.append(f"Doctor's note: {summary['doctor_notes'][:100]}.")

        parts.append("Please consult the assigned doctor for clinical guidance.")
        return " ".join(parts)

    def _store_patient_history(self, patient_id: str, extracted: dict,
                                flags: list, summary: dict,
                                ai_interpretation: str) -> str:
        """Store the complete analysis as a patient history entry."""
        from uuid import uuid4

        history_id = str(uuid4())

        history_entry = {
            "history_id":        history_id,
            "patient_id":        patient_id,
            "entry_type":        "LAB_REPORT",
            "created_at":        datetime.now(),
            "source":            "IDP_TEXTRACT",

            # Raw extracted data
            "lab_results":       extracted.get("lab_results", []),
            "vitals":            extracted.get("vitals", {}),
            "medications":       extracted.get("medications", []),
            "diagnoses":         extracted.get("diagnoses", []),
            "allergies":         extracted.get("allergies", []),
            "doctor_notes":      extracted.get("doctor_notes", ""),

            # Analysis results
            "abnormal_flags":    flags,
            "critical_count":    summary.get("critical_count", 0),
            "abnormal_count":    summary.get("abnormal_count", 0),
            "total_tests":       summary.get("total_tests", 0),

            # AI interpretation
            "ai_interpretation": ai_interpretation,
            "clinical_summary":  summary,

            # Status
            "reviewed_by_doctor": False,
            "doctor_review_notes": "",
        }

        # Store in patient_history collection
        self.db.patient_history.insert_one(history_entry)

        # Also update the summaries collection (used by RAG and doctor dashboard)
        self.db.summaries.insert_one({
            "patient_id":      patient_id,
            "generated_at":    datetime.now(),
            "source":          "IDP_ANALYSIS",
            "history_id":      history_id,
            "patient_concerns": "",
            "request_history": f"Lab report processed: {summary['total_tests']} tests, "
                               f"{summary['abnormal_count']} abnormal",
            "doctor_notes":    ai_interpretation,
            "critical_flags":  [f["parameter"] for f in flags if f.get("severity") == "critical"],
            "abnormal_flags":  [f["parameter"] for f in flags],
        })

        logger.info(f"Patient history entry created: {history_id} for patient {patient_id}")
        return history_id


# ── Singleton ─────────────────────────────────────────────────────────────────
_analyzer = None

def get_medical_analyzer() -> MedicalAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = MedicalAnalyzer()
    return _analyzer
