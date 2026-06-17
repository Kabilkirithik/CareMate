import os
import re
from dotenv import load_dotenv

load_dotenv()

# Keyword fallback when ML model file is missing (run ml_model/retrain_v5.py to train)
_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("emergency", [
        r"\bemergency\b", r"\bhelp me\b", r"chest pain", r"can't breathe",
        r"cannot breathe", r"severe pain", r"heart attack", r"stroke",
        r"bleeding", r"unconscious", r"code blue",
    ]),
    ("nurse_request", [
        r"\bnurse\b", r"\biv\b", r"bandage", r"injection", r"medication",
        r"painkiller", r"vitals check", r"vital signs", r"blood pressure",
        r"temperature check", r"medicine",
    ]),
    ("nutrition_request", [
        r"\bmeal\b", r"\bfood\b", r"\blunch\b", r"\bdinner\b", r"\bbreakfast\b",
        r"\bhungry\b", r"\beat\b", r"diet", r"nutrition",
        r"dietary", r"snack", r"drink", r"juice",
    ]),
    ("utility_request", [
        r"\bwater\b", r"blanket", r"charger", r"housekeeping", r"wheelchair",
        r"cleaning", r"room service", r"bathroom", r"pillow", r"bed",
        r"maintenance", r"repair", r"broken", r"light",
    ]),
    ("doctor_query", [
        r"\bdoctor\b", r"physician", r"specialist", r"consultation",
        r"\bdr\b", r"\bdr\.\b",
    ]),
    ("status_query", [
        r"how am i", r"my status", r"my condition", r"test results",
        r"lab report", r"when can i go home", r"discharge", r"diagnosis",
        r"what is wrong", r"my results",
    ]),
]


class IntentRouter:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, "ml_model", "caremate_sentence_transformer_svm.pkl")
        self._use_fallback = not os.path.exists(model_path)
        self.svm_model = None
        self.st_model = None

        if self._use_fallback:
            print(
                f"WARNING: ML model not found at {model_path}. "
                "Using keyword fallback. Run: python ml_model/retrain_v5.py"
            )
            return

        import joblib
        from sentence_transformers import SentenceTransformer

        model_data = joblib.load(model_path)
        self.svm_model = model_data["model"]
        self.st_model_name = model_data.get("model_name", "all-MiniLM-L6-v2")
        self.intents = model_data.get("intents", [])
        self.st_model = SentenceTransformer(self.st_model_name)

    def _keyword_classify(self, text: str) -> dict:
        lower = text.lower().strip()
        for intent, patterns in _KEYWORD_RULES:
            for pat in patterns:
                if re.search(pat, lower):
                    return {"intent": intent, "confidence": 0.75}
        return {"intent": "general_conversation", "confidence": 0.6}

    def classify(self, text: str):
        """Classifies the user input into one of the hospital intents."""
        if self._use_fallback:
            return self._keyword_classify(text)

        embedding = self.st_model.encode([text])
        prediction = self.svm_model.predict(embedding)[0]
        try:
            probs = self.svm_model.predict_proba(embedding)[0]
            confidence = max(probs)
        except Exception:
            confidence = 1.0

        intent = str(prediction)
        
        # Post-classification override: if message starts with "doctor" or
        # explicitly addresses the doctor, it must be doctor_query regardless
        # of what the SVM predicted.
        lower = text.lower().strip()
        doctor_address_patterns = [
            r"^doctor[,\s]", r"^dr[,\.\s]", r"\bneed (a |to see a |the )?doctor\b",
            r"\bask (the |my )?doctor\b", r"\bsee (the |my )?doctor\b",
            r"\bspeak (to|with) (the |my )?doctor\b",
            r"\btell (the |my )?doctor\b", r"\bcall (the |my )?doctor\b",
            r"\bwant (the |my )?doctor\b", r"\bsend (the |my )?doctor\b",
        ]
        for pat in doctor_address_patterns:
            if re.search(pat, lower):
                return {"intent": "doctor_query", "confidence": 0.90}

        return {"intent": intent, "confidence": float(confidence)}

if __name__ == "__main__":
    router = IntentRouter()
    test_text = "I am having severe chest pain"
    print(f"Text: {test_text}")
    print(f"Classification: {router.classify(test_text)}")
