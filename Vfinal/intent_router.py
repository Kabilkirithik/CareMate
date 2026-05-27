import joblib
import os
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

class IntentRouter:
    def __init__(self):
        # Determine the correct path regardless of where the script is run from
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, 'ml_model', 'caremate_sentence_transformer_svm.pkl')
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")

        # Load the saved model dict
        model_data = joblib.load(model_path)
        self.svm_model = model_data['model']
        self.st_model_name = model_data.get('model_name', 'all-MiniLM-L6-v2')
        self.intents = model_data.get('intents', [])
        
        # Load embedding model
        self.st_model = SentenceTransformer(self.st_model_name)

    def classify(self, text: str):
        """Classifies the user input into one of the 7 intents."""
        embedding = self.st_model.encode([text])
        prediction = self.svm_model.predict(embedding)[0]
        
        # Get probabilities if available
        try:
            probs = self.svm_model.predict_proba(embedding)[0]
            confidence = max(probs)
        except:
            confidence = 1.0 # Default if probability=False during training

        return {
            "intent": prediction,
            "confidence": float(confidence)
        }

if __name__ == "__main__":
    router = IntentRouter()
    test_text = "I am having severe chest pain"
    print(f"Text: {test_text}")
    print(f"Classification: {router.classify(test_text)}")
