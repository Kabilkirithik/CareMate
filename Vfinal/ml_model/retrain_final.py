#!/usr/bin/env python3
"""
Final retrain using the full big dataset (17k+ samples).
Fixes misclassification of medical knowledge questions.
"""
import pandas as pd
import joblib
import os
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sentence_transformers import SentenceTransformer

def retrain_final():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Use the BIG dataset, not the cleaned 1000-sample one
    data_path = os.path.join(base_dir, 'caremate_big_dataset.csv')
    model_output_path = os.path.join(base_dir, 'caremate_sentence_transformer_svm.pkl')
    st_model_name = 'all-MiniLM-L6-v2'

    print("Loading big dataset...")
    df = pd.read_csv(data_path)
    df.columns = [c.strip().strip(',') for c in df.columns]
    
    # Remove document_submission if present
    df = df[df['intent'] != 'document_submission']
    
    # Drop rows with NaN text
    df = df.dropna(subset=['text'])
    df['text'] = df['text'].astype(str).str.strip()
    df = df[df['text'].str.len() > 2]  # Remove empty/very short texts
    
    # Relabel 'water' requests to utility_request
    water_mask = (
        (df['intent'] == 'nutrition_request') & 
        (df['text'].str.contains('water', case=False, na=False))
    )
    df.loc[water_mask, 'intent'] = 'utility_request'
    
    print(f"Dataset size: {len(df)}")
    print(f"Intent distribution:\n{df['intent'].value_counts()}\n")

    X_text = df['text'].astype(str).tolist()
    y = df['intent'].astype(str).tolist()

    print(f"Loading SentenceTransformer: {st_model_name}...")
    st_model = SentenceTransformer(st_model_name)

    print("Generating embeddings (this may take a few minutes)...")
    X_embeddings = st_model.encode(X_text, show_progress_bar=True, batch_size=64)

    # Train/test split for evaluation
    X_train, X_test, y_train, y_test = train_test_split(
        X_embeddings, y, test_size=0.1, random_state=42, stratify=y
    )

    print(f"\nTraining SVM on {len(X_train)} samples...")
    svm_model = SVC(kernel='linear', C=1.0, probability=True)
    svm_model.fit(X_train, y_train)

    # Evaluate
    print("\nEvaluating on test set...")
    y_pred = svm_model.predict(X_test)
    print(classification_report(y_test, y_pred))

    # Test specific cases with correct expected intents
    print("\nTesting intent boundaries:")
    test_cases = [
        # General medical knowledge → general_conversation
        ("How to cure diabetes?",               "general_conversation"),
        ("Do you know what diabetes is?",        "general_conversation"),
        ("What is hypertension?",                "general_conversation"),
        ("How to cure it?",                      "general_conversation"),
        ("What are the side effects of this?",   "general_conversation"),
        ("What is the treatment for this?",      "general_conversation"),
        # Personal medication/dose → doctor_query
        ("What is my dosage?",                   "doctor_query"),
        ("What medication am I on?",             "doctor_query"),
        ("Can the doctor change my medication?", "doctor_query"),
        ("Can the doctor come see me?",          "doctor_query"),
        ("I need to speak with my doctor",       "doctor_query"),
        ("Can I get a stronger painkiller?",     "doctor_query"),
        # Other intents
        ("I am bored",                           "general_conversation"),
        ("Can you sing a song?",                 "general_conversation"),
        ("I need water",                         "utility_request"),
        ("I need a nurse",                       "nurse_request"),
        ("I need food",                          "nutrition_request"),
        ("Help me I can't breathe",              "emergency"),
        ("What are my test results?",            "status_query"),
        ("How am I doing?",                      "status_query"),
    ]
    
    for text, expected in test_cases:
        embedding = st_model.encode([text])
        pred = svm_model.predict(embedding)[0]
        probs = svm_model.predict_proba(embedding)[0]
        conf = max(probs)
        status = "✅" if pred == expected else "❌"
        print(f"  {status} '{text}' → {pred} ({conf:.2f}) [expected: {expected}]")

    # Save model
    print(f"\nSaving model to {model_output_path}...")
    joblib.dump({
        'model': svm_model,
        'model_name': st_model_name,
        'intents': sorted(list(set(y)))
    }, model_output_path)
    
    print("\n✅ Retraining complete! Model saved.")

if __name__ == "__main__":
    retrain_final()
