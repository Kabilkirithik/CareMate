"""
CareMate Intent Classifier
==========================
Classifies patient speech text into one of 8 intents and
routes to the correct agent in the CrewAI pipeline.

Intents:
    - general_conversation  → Patient Interaction Agent
    - emergency             → Central Orchestration Agent
    - nurse_request         → Central Orchestration Agent
    - doctor_query          → Central Orchestration Agent
    - nutrition_request     → Central Orchestration Agent
    - utility_request       → Central Orchestration Agent
    - status_query          → Central Orchestration Agent
    - document_submission   → Central Orchestration Agent

Usage:
    from intent_classifier import CareMateClassifier

    classifier = CareMateClassifier()
    result = classifier.predict("I need a blanket please")
    print(result)
    # {
    #     "intent": "utility_request",
    #     "agent": "central_agent",
    #     "confidence": 0.97,
    #     "all_scores": { ... }
    # }
"""

import os
import joblib
from pathlib import Path
from typing import Optional

# ── Routing map ──────────────────────────────────────────────────────────────
AGENT_ROUTING = {
    "general_conversation": "patient_agent",
    "emergency":            "central_agent",
    "nurse_request":        "central_agent",
    "doctor_query":         "central_agent",
    "nutrition_request":    "central_agent",
    "utility_request":      "central_agent",
    "status_query":         "central_agent",
    "document_submission":  "central_agent",
}

# Tool mapping for Central Agent to decide which tool to invoke
TOOL_ROUTING = {
    "emergency":            "emergency_detection_tool",
    "nurse_request":        "nurse_dashboard_tool",
    "doctor_query":         "doctor_voice_interaction_tool",
    "nutrition_request":    "nutritionist_approval_tool",
    "utility_request":      "utility_service_tool",
    "status_query":         "status_tracking_tool",
    "document_submission":  "ocr_submission_tool",
    "general_conversation": None,
}

# ── Classifier class ─────────────────────────────────────────────────────────
class CareMateClassifier:
    """
    ML-based intent classifier for CareMate.
    Loads the trained SVM + TF-IDF pipeline and provides
    a simple predict() interface for the CrewAI pipeline.
    """

    MODEL_PATH = Path(__file__).parent / "intent_classifier.pkl"

    def __init__(self, model_path: Optional[str] = None):
        path = model_path or self.MODEL_PATH
        if not Path(path).exists():
            raise FileNotFoundError(
                f"Model not found at {path}. "
                "Run train_intent_classifier.py first."
            )
        self.pipeline = joblib.load(path)
        self.classes = self.pipeline.classes_.tolist()

    # ── Main predict method ──────────────────────────────────────────────────
    def predict(self, text: str, confidence_threshold: float = 0.3) -> dict:
        """
        Classify text and return routing decision.

        Args:
            text: Raw patient utterance (post-STT output)
            confidence_threshold: Minimum confidence to trust prediction.
                                  Falls back to 'general_conversation' if below.

        Returns:
            {
                "text":        original input,
                "intent":      predicted intent label,
                "agent":       "patient_agent" | "central_agent",
                "tool":        suggested tool name (or None),
                "confidence":  top-class probability,
                "all_scores":  { intent: probability, ... }
            }
        """
        if not text or not text.strip():
            return self._build_result(text, "general_conversation", 1.0, {})

        text = text.strip()
        probs = self.pipeline.predict_proba([text])[0]
        scores = dict(zip(self.classes, probs))
        top_intent = max(scores, key=scores.get)
        top_confidence = scores[top_intent]

        # Fall back to general_conversation if confidence is too low
        if top_confidence < confidence_threshold:
            top_intent = "general_conversation"

        return self._build_result(text, top_intent, top_confidence, scores)

    # ── Batch predict ────────────────────────────────────────────────────────
    def predict_batch(self, texts: list[str]) -> list[dict]:
        """Classify a list of utterances at once."""
        return [self.predict(t) for t in texts]

    # ── Helper ───────────────────────────────────────────────────────────────
    def _build_result(self, text, intent, confidence, all_scores) -> dict:
        return {
            "text":       text,
            "intent":     intent,
            "agent":      AGENT_ROUTING[intent],
            "tool":       TOOL_ROUTING[intent],
            "confidence": round(float(confidence), 4),
            "all_scores": {k: round(float(v), 4) for k, v in all_scores.items()},
        }


# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    clf = CareMateClassifier()

    test_cases = [
        "I cannot breathe properly",           # emergency
        "Can you call the nurse please",        # nurse_request
        "What did the doctor say about my MRI", # doctor_query
        "I want to eat something light",        # nutrition_request
        "I need a blanket",                     # utility_request
        "What is the status of my request",     # status_query
        "Here is my discharge document",        # document_submission
        "How are you today",                    # general_conversation
    ]

    print(f"{'Text':<45} {'Intent':<25} {'Agent':<20} {'Conf':>6}")
    print("-" * 100)
    for t in test_cases:
        r = clf.predict(t)
        print(f"{r['text']:<45} {r['intent']:<25} {r['agent']:<20} {r['confidence']:>6.2%}")
