"""
CareMate Intent Classifier — Training Script
=============================================
Run this script whenever you have new training data.

Usage:
    python train_intent_classifier.py
    python train_intent_classifier.py --train data/my_data.csv --test data/my_test.csv
"""

import argparse
import warnings
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import cross_val_score, StratifiedKFold

warnings.filterwarnings("ignore")


# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_TRAIN = "normal_dataset.csv"
DEFAULT_TEST  = "caremate_golden_test.csv"
OUTPUT_MODEL  = "intent_classifier.pkl"


# ── Train ─────────────────────────────────────────────────────────────────────
def train(train_path: str, test_path: str, output_path: str):
    print("\n📂 Loading datasets...")
    train_df = pd.read_csv(train_path).dropna()
    test_df  = pd.read_csv(test_path).dropna()

    print(f"   Train samples : {len(train_df)}")
    print(f"   Test  samples : {len(test_df)}")
    print(f"   Classes       : {sorted(train_df['label'].unique().tolist())}")

    X_train, y_train = train_df["text"], train_df["label"]
    X_test,  y_test  = test_df["text"],  test_df["label"]

    # ── Build pipeline ────────────────────────────────────────────────────────
    print("\n🔧 Building TF-IDF + SVM pipeline...")
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=10000,
            sublinear_tf=True,
            strip_accents="unicode",
            analyzer="word",
            token_pattern=r"\w{1,}",
            min_df=1,
        )),
        ("clf", SVC(
            kernel="linear",
            probability=True,
            C=1.0,
            class_weight="balanced",   # handles class imbalance
        )),
    ])

    # ── Cross-validation ──────────────────────────────────────────────────────
    print("\n📊 Running 5-fold cross-validation on training set...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="accuracy")
    print(f"   CV Accuracy : {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # ── Train on full training set ────────────────────────────────────────────
    print("\n🏋️  Training on full training set...")
    pipeline.fit(X_train, y_train)

    # ── Evaluate on held-out test set ─────────────────────────────────────────
    print("\n🧪 Evaluating on golden test set...")
    preds = pipeline.predict(X_test)
    acc   = accuracy_score(y_test, preds)

    print(f"\n   Test Accuracy : {acc:.4f} ({acc*100:.2f}%)\n")
    print("=== Per-Class Report ===")
    print(classification_report(y_test, preds))

    # ── Save ──────────────────────────────────────────────────────────────────
    joblib.dump(pipeline, output_path)
    print(f"✅ Model saved → {output_path}")
    print(f"   Classes : {pipeline.classes_.tolist()}")

    return pipeline, acc


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CareMate Intent Classifier")
    parser.add_argument("--train",  default=DEFAULT_TRAIN,  help="Path to training CSV")
    parser.add_argument("--test",   default=DEFAULT_TEST,   help="Path to test CSV")
    parser.add_argument("--output", default=OUTPUT_MODEL,   help="Output .pkl path")
    args = parser.parse_args()

    train(args.train, args.test, args.output)
