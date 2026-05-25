"""
caremate_v4/classifier/classifier_client.py
============================================
In-process ML classifier that loads the trained scikit-learn
SVM + TF-IDF pipeline (intent_classifier.pkl) directly —
no HTTP service needed.

Falls back to a lightweight rule-based classifier if the model
file is missing or fails to load.

Label mapping (ML model → single_crew category)
------------------------------------------------
doctor_query        → DOCTOR_QUERY
document_submission → OCR_UPLOAD
emergency           → EMERGENCY          ← handled by emergency_precheck first
general_conversation→ CASUAL_CHAT        ← stays with Patient Agent
nurse_request       → NURSE_REQUEST
nutrition_request   → NUTRITION_REQUEST
status_query        → STATUS_QUERY
utility_request     → UTILITY_REQUEST

Usage
-----
    from caremate_v4.classifier.classifier_client import classify_message, is_classifier_available

    result = classify_message("I need a blanket", patient_id="P-001")
    # → {"category": "UTILITY_REQUEST", "confidence": 0.97, "source": "ml_model"}
"""

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# =============================================================
# PATH — single pipeline .pkl (TF-IDF + SVM in one object)
# =============================================================

_HERE      = Path(__file__).parent                        # caremate_v4/classifier/
_PKL_MODEL = _HERE.parent / "ml_model" / "intent_classifier_v2.pkl"

# =============================================================
# LABEL → CATEGORY MAP
# =============================================================

_LABEL_TO_CATEGORY: dict[str, str] = {
    "doctor_query":         "DOCTOR_QUERY",
    "document_submission":  "OCR_UPLOAD",
    "emergency":            "EMERGENCY",       # precheck fires first; safe fallback
    "general_conversation": "CASUAL_CHAT",     # handled by Patient Agent directly
    "nurse_request":        "NURSE_REQUEST",
    "nutrition_request":    "NUTRITION_REQUEST",
    "status_query":         "STATUS_QUERY",
    "utility_request":      "UTILITY_REQUEST",
}

# =============================================================
# MODEL LOADING (once, at import time)
# =============================================================

_pipeline = None
_ml_ready = False


def _load_model() -> bool:
    """Load the sklearn pipeline from .pkl. Returns True on success."""
    global _pipeline, _ml_ready

    try:
        import joblib  # type: ignore

        if not _PKL_MODEL.exists():
            logger.warning("intent_classifier.pkl not found at %s", _PKL_MODEL)
            return False

        _pipeline = joblib.load(str(_PKL_MODEL))
        _ml_ready = True
        logger.info(
            "✅ ML classifier loaded — classes: %s",
            list(_pipeline.classes_),
        )
        return True

    except Exception as exc:
        logger.warning(
            "ML model load failed (%s) — falling back to rule-based classifier", exc
        )
        return False


_load_model()

# =============================================================
# PUBLIC API
# =============================================================


def is_classifier_available() -> bool:
    """Return True if the ML pipeline loaded successfully."""
    return _ml_ready


def classify_message(
    message: str,
    patient_id: Optional[str] = None,   # kept for logging / future use
    confidence_threshold: float = 0.30,
) -> dict:
    """
    Classify a patient message into a CareMate workflow category.

    Parameters
    ----------
    message              : Raw patient utterance (post-STT text)
    patient_id           : Optional — used for logging only
    confidence_threshold : Minimum ML confidence; falls back to rules below this

    Returns
    -------
    dict with keys:
        category   (str)   — one of the TOOL_INSTRUCTIONS keys in single_crew.py
        confidence (float) — 0.0 – 1.0
        source     (str)   — "ml_model" | "rule_based"
    """
    if not message or not message.strip():
        return {"category": "CASUAL_CHAT", "confidence": 1.0, "source": "rule_based"}

    if _ml_ready:
        result = _classify_ml(message.strip())
        # If ML is confident enough, trust it
        if result["confidence"] >= confidence_threshold:
            return result
        # Otherwise let rules have a go
        rule_result = _classify_rules(message.strip())
        # Return whichever is more confident
        if rule_result["confidence"] >= result["confidence"]:
            return rule_result
        return result
    else:
        return _classify_rules(message.strip())


# =============================================================
# ML PATH
# =============================================================


def _classify_ml(message: str) -> dict:
    """Use the loaded TF-IDF + SVM pipeline (single .pkl object)."""
    try:
        probs      = _pipeline.predict_proba([message])[0]
        classes    = _pipeline.classes_
        scores     = dict(zip(classes, probs))
        label      = max(scores, key=scores.get)
        confidence = float(scores[label])
        category   = _LABEL_TO_CATEGORY.get(label, "NURSE_REQUEST")

        return {
            "category":   category,
            "confidence": round(confidence, 4),
            "source":     "ml_model",
        }

    except Exception as exc:
        logger.warning("ML inference failed (%s) — falling back to rules", exc)
        return _classify_rules(message)


# =============================================================
# RULE-BASED FALLBACK
# =============================================================

_RULES: list[tuple[str, list[str], int]] = [
    ("UTILITY_REQUEST",   ["blanket", "wheelchair", "charger", "housekeeping",
                           "clean", "fan", "light", "bedsheet", "bed sheet",
                           "pillow", "remote", "tv"], 1),
    ("NURSE_REQUEST",     ["nurse", "assist", "assistance", "come here",
                           "need help", "water", "pain", "uncomfortable",
                           "call someone"], 1),
    ("NUTRITION_REQUEST", ["food", "meal", "eat", "hungry", "diet",
                           "breakfast", "lunch", "dinner", "snack", "drink"], 1),
    ("STATUS_QUERY",      ["status", "update", "waiting", "where is",
                           "any news", "yet", "still", "progress", "done yet"], 1),
    ("DOCTOR_QUERY",      ["doctor", "medicine", "medication", "diagnosis",
                           "treatment", "disease", "why do i", "health question",
                           "medical", "prescription"], 1),
    ("OCR_UPLOAD",        ["upload", "report", "document", "scan",
                           "prescription", "record", "file", "submit"], 1),
]


def _classify_rules(message: str) -> dict:
    """Lightweight keyword-scoring fallback classifier."""
    text   = message.lower()
    tokens = set(re.findall(r"\b\w+\b", text))
    scores: dict[str, int] = {}

    for category, keywords, weight in _RULES:
        score = 0
        for kw in keywords:
            if " " in kw:               # multi-word phrase
                if kw in text:
                    score += weight * 2
            elif kw in tokens:
                score += weight
        if score:
            scores[category] = score

    if not scores:
        return {"category": "CASUAL_CHAT", "confidence": 0.6, "source": "rule_based"}

    best       = max(scores, key=scores.get)
    total      = sum(scores.values())
    confidence = round(scores[best] / total, 4) if total else 0.5

    return {
        "category":   best,
        "confidence": confidence,
        "source":     "rule_based",
    }