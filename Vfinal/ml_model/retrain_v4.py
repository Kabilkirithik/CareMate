import pandas as pd
import joblib
import os
from sklearn.svm import SVC
from sentence_transformers import SentenceTransformer

def retrain_v4():
    data_path = 'Vfinal/ml_model/caremate_intent_dataset_cleaned.csv'
    model_output_path = 'Vfinal/ml_model/caremate_sentence_transformer_svm.pkl'
    st_model_name = 'all-MiniLM-L6-v2'

    print("Loading original dataset...")
    df = pd.read_csv(data_path)
    
    # Strip whitespace/commas
    df.columns = [c.strip().strip(',') for c in df.columns]
    
    # Remove document_submission as per requirement
    df = df[df['intent'] != 'document_submission']

    # 1. Add disease info to status_query
    disease_examples = [
        {"text": "can you tell me about diabetes", "intent": "status_query"},
        {"text": "what is hypertension", "intent": "status_query"},
        {"text": "tell me about asthma", "intent": "status_query"},
        {"text": "tell me about arthritis", "intent": "status_query"},
        {"text": "what causes fever", "intent": "status_query"},
        {"text": "explain about pneumonia", "intent": "status_query"},
        {"text": "i want to know about my disease", "intent": "status_query"},
        {"text": "what is my condition", "intent": "status_query"}
    ]
    df_new = pd.concat([df, pd.DataFrame(disease_examples)], ignore_index=True)
    
    # 2. Relabel 'water' to utility_request
    water_mask = (df_new['intent'] == 'nutrition_request') & (df_new['text'].str.contains('water', case=False, na=False))
    df_new.loc[water_mask, 'intent'] = 'utility_request'

    X_text = df_new['text'].astype(str).tolist()
    y = df_new['intent'].astype(str).tolist()

    print(f"Loading SentenceTransformer: {st_model_name}...")
    st_model = SentenceTransformer(st_model_name)

    print("Generating embeddings...")
    X_embeddings = st_model.encode(X_text)

    print("Training SVM model...")
    svm_model = SVC(kernel='linear', C=1.0, probability=True)
    svm_model.fit(X_embeddings, y)

    print(f"Saving updated model to {model_output_path}...")
    joblib.dump({
        'model': svm_model,
        'model_name': st_model_name,
        'intents': sorted(list(set(y)))
    }, model_output_path)
    
    print("Retraining Complete.")

if __name__ == "__main__":
    retrain_v4()
