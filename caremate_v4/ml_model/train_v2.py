"""
CareMate Intent Classifier v2 — Training Script
================================================
Run from ANY directory using either:
    python -m caremate_v4.ml_model.train_v2
    python caremate_v4/ml_model/train_v2.py

Requirements (install once):
    pip install scikit-learn pandas joblib
"""

import pandas as pd
import joblib
import warnings
from pathlib import Path
warnings.filterwarnings("ignore")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, accuracy_score

# Paths are always relative to THIS script file — works from any directory
HERE        = Path(__file__).parent
TRAIN_FILE  = HERE / "caremate_rich_dataset_final.csv"
TEST_FILE   = HERE / "caremate_golden_test.csv"
OUTPUT_FILE = HERE / "intent_classifier_v2.pkl"

print("Step 1 — Loading data...")
train = pd.read_csv(TRAIN_FILE).dropna()
test  = pd.read_csv(TEST_FILE).dropna()
print(f"  Train: {len(train)} samples  |  Test: {len(test)} samples")
print(f"  Classes: {sorted(train['label'].unique())}")

print("\nStep 2 — Building TF-IDF + SVM pipeline...")
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(
        ngram_range=(1, 3),
        max_features=20000,
        sublinear_tf=True,
        min_df=1,
        analyzer='word',
        token_pattern=r'\w{1,}',
    )),
    ('clf', SVC(
        kernel='linear',
        probability=True,
        C=2.0,
        class_weight='balanced',
    )),
])

print("\nStep 3 — Cross-validation (5-fold)...")
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(pipeline, train['text'], train['label'], cv=cv, scoring='accuracy')
print(f"  CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

print("\nStep 4 — Training on full dataset...")
pipeline.fit(train['text'], train['label'])

print("\nStep 5 — Evaluating on golden test set...")
preds = pipeline.predict(test['text'])
acc   = accuracy_score(test['label'], preds)
print(f"  Test Accuracy: {acc:.4f} ({acc*100:.1f}%)")
print()
print(classification_report(test['label'], preds))

print(f"Step 6 — Saving model to {OUTPUT_FILE}...")
joblib.dump(pipeline, OUTPUT_FILE)
print(f"  Done! Replace the old intent_classifier.pkl with {OUTPUT_FILE}")

# Quick sanity test
LABEL_MAP = {
    "doctor_query":"DOCTOR_QUERY","document_submission":"OCR_UPLOAD",
    "emergency":"EMERGENCY","general_conversation":"CASUAL_CHAT",
    "nurse_request":"NURSE_REQUEST","nutrition_request":"NUTRITION_REQUEST",
    "status_query":"STATUS_QUERY","utility_request":"UTILITY_REQUEST",
}
print("\nSanity checks:")
for text in ["Hi","I feel tired","I have chest pain","I want blankets","I want soup"]:
    probs = pipeline.predict_proba([text])[0]
    label = pipeline.classes_[probs.argmax()]
    cat   = LABEL_MAP.get(label)
    conf  = probs.max()
    print(f"  '{text}' → {cat} ({conf:.0%})")