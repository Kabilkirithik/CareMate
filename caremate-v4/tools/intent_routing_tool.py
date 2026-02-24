# intent_routing_tool.py

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Dict, Tuple
import re


# -------------------------------------------------
# Input Schema
# -------------------------------------------------
class IntentInput(BaseModel):
    text: str = Field(..., description="Patient spoken text in English")


# -------------------------------------------------
# Hybrid Intent Routing Tool
# -------------------------------------------------
class IntentRoutingTool(BaseTool):

    name: str= "IntentRoutingTool"
    description: str = (
        "Hybrid intent classifier for CareMate. "
        "Uses heuristic scoring with semantic fallback."
    )

    args_schema: Type[BaseModel] = IntentInput

    # -------------------------------------------------
    # MAIN TOOL EXECUTION
    # -------------------------------------------------
    async def _run(self, **kwargs):

        text = kwargs["text"].lower()

        intent, confidence = self.hybrid_intent_detection(text)

        return {
            "intent": intent,
            "confidence": confidence
        }

    # -------------------------------------------------
    # HYBRID INTENT ENGINE
    # -------------------------------------------------
    def hybrid_intent_detection(self, text: str) -> Tuple[str, float]:

        # Step 1 — Heuristic scoring
        scores = self.heuristic_intent_scoring(text)

        # Step 2 — Find best intent
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        # Normalize confidence
        confidence = min(best_score / 3.0, 1.0)

        # Step 3 — Semantic fallback if low confidence
        if confidence < 0.4:
            semantic_intent = self.semantic_fallback(text)
            return semantic_intent, 0.5

        return best_intent, round(confidence, 2)

    # -------------------------------------------------
    # HEURISTIC SCORING LAYER (FAST)
    # -------------------------------------------------
    def heuristic_intent_scoring(self, text: str) -> Dict[str, int]:

        scores = {
            "CASUAL_CHAT": 0,
            "NURSE_REQUEST": 0,
            "DOCTOR_QUERY": 0,
            "NUTRITION_REQUEST": 0,
            "UTILITY_REQUEST": 0,
            "STATUS_QUERY": 0
        }

        # Normalize text
        tokens = re.findall(r"\b\w+\b", text)

        # ---------------- Nurse Patterns ----------------
        nurse_patterns = [
            "help", "assist", "come", "check", "support",
            "pain", "need someone", "call nurse"
        ]

        # ---------------- Doctor Patterns ----------------
        doctor_patterns = [
            "disease", "medicine", "diagnosis", "treatment",
            "why", "health", "problem", "doctor"
        ]

        # ---------------- Nutrition Patterns ----------------
        nutrition_patterns = [
            "food", "eat", "meal", "hungry", "diet"
        ]

        # ---------------- Utility Patterns ----------------
        utility_patterns = [
            "blanket", "clean", "wheelchair", "charger",
            "fan", "light", "bed sheet"
        ]

        # ---------------- Status Patterns ----------------
        status_patterns = [
            "status", "update", "did they", "waiting",
            "where are they", "any response"
        ]

        # Heuristic scoring
        for word in tokens:

            if word in nurse_patterns:
                scores["NURSE_REQUEST"] += 1

            if word in doctor_patterns:
                scores["DOCTOR_QUERY"] += 1

            if word in nutrition_patterns:
                scores["NUTRITION_REQUEST"] += 1

            if word in utility_patterns:
                scores["UTILITY_REQUEST"] += 1

            if word in status_patterns:
                scores["STATUS_QUERY"] += 1

        # Casual fallback if nothing matched
        if all(v == 0 for v in scores.values()):
            scores["CASUAL_CHAT"] = 1

        return scores

    # -------------------------------------------------
    # SEMANTIC FALLBACK (LIGHTWEIGHT)
    # -------------------------------------------------
    def semantic_fallback(self, text: str) -> str:
        """
        Lightweight semantic routing.
        This is NOT heavy AI — just meaning-based rules.
        Can later be replaced with embeddings or LLM.
        """

        # Health concern expressions
        if "feel" in text or "wrong" in text or "uncomfortable" in text:
            return "DOCTOR_QUERY"

        # Asking someone to come
        if "someone" in text or "come here" in text:
            return "NURSE_REQUEST"

        # Waiting or follow-up
        if "still waiting" in text or "yet" in text:
            return "STATUS_QUERY"

        return "CASUAL_CHAT"