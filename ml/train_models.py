import os
import sys

# Ensure project root is in python path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import json
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix

from ml.preprocessing import clean_text
from config import Config

def train_all_models():
    print("==================================================================")
    print("      INTELLIGENT STUDENT GRIEVANCE RESOLUTION SYSTEM - ML TRAINING")
    print("==================================================================")
    
    # 1. Load Dataset
    dataset_path = os.path.join(Config.BASE_DIR, 'datasets', 'grievances.csv')
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at {dataset_path}. Please run generate_dataset.py first.")
    
    df = pd.read_csv(dataset_path)
    print(f"Loaded dataset: {len(df)} samples.")
    
    # 2. Preprocess Text
    print("Preprocessing complaint text...")
    df['cleaned_text'] = df['text'].apply(lambda x: clean_text(x, remove_stopwords=True))
    
    # 3. Train/Test Split (fixed random seed for reproducibility)
    RANDOM_SEED = 42
    train_df, test_df = train_test_split(df, test_size=0.25, random_state=RANDOM_SEED, stratify=df['category'])
    print(f"Training samples: {len(train_df)}, Testing samples: {len(test_df)}")

    # 4. Feature Extraction - TF-IDF Vectorizer
    # Fit vectorizer only on training data to avoid data leakage
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_features=5000,
        sublinear_tf=True
    )
    X_train = vectorizer.fit_transform(train_df['cleaned_text'])
    X_test = vectorizer.transform(test_df['cleaned_text'])

    # Save Vectorizer
    os.makedirs(Config.MODELS_DIR, exist_ok=True)
    joblib.dump(vectorizer, Config.VECTORIZER_PATH)
    print(f"Saved TF-IDF Vectorizer to: {Config.VECTORIZER_PATH}")

    metrics_report = {}

    # -------------------------------------------------------------------
    # MODEL 1: Grievance Category Prediction (Logistic Regression)
    # -------------------------------------------------------------------
    print("\n------------------------------------------------------------------")
    print("1. Training Grievance Category Model (Logistic Regression)...")
    cat_y_train = train_df['category']
    cat_y_test = test_df['category']

    cat_clf = LogisticRegression(max_iter=1000, C=3.0, class_weight='balanced', random_state=RANDOM_SEED)
    cat_clf.fit(X_train, cat_y_train)
    cat_preds = cat_clf.predict(X_test)

    cat_acc = accuracy_score(cat_y_test, cat_preds)
    cat_prec, cat_rec, cat_f1, _ = precision_recall_fscore_support(cat_y_test, cat_preds, average='weighted', zero_division=0)
    cat_report = classification_report(cat_y_test, cat_preds, zero_division=0, output_dict=True)
    cat_cm = confusion_matrix(cat_y_test, cat_preds, labels=sorted(cat_clf.classes_)).tolist()

    print(f"Category Model Accuracy:  {cat_acc * 100:.2f}%")
    print(f"Category Weighted F1:     {cat_f1:.4f}")
    joblib.dump(cat_clf, Config.CATEGORY_MODEL_PATH)
    print(f"Saved Category Model to: {Config.CATEGORY_MODEL_PATH}")

    metrics_report['category_model'] = {
        'model_name': 'Logistic Regression (Balanced) with TF-IDF',
        'accuracy': round(cat_acc, 4),
        'weighted_precision': round(cat_prec, 4),
        'weighted_recall': round(cat_rec, 4),
        'weighted_f1': round(cat_f1, 4),
        'classes': list(cat_clf.classes_),
        'confusion_matrix': cat_cm,
        'report': cat_report
    }

    # -------------------------------------------------------------------
    # MODEL 2: Priority Prediction (Linear SVM with probability calibration)
    # -------------------------------------------------------------------
    print("\n------------------------------------------------------------------")
    print("2. Training Priority Prediction Model (Linear SVM)...")
    prio_y_train = train_df['priority']
    prio_y_test = test_df['priority']

    # Using CalibratedClassifierCV around LinearSVC for calibrated class probabilities
    base_svm = LinearSVC(C=1.2, class_weight='balanced', random_state=RANDOM_SEED, max_iter=3000)
    prio_clf = CalibratedClassifierCV(estimator=base_svm, cv=3)
    prio_clf.fit(X_train, prio_y_train)
    prio_preds = prio_clf.predict(X_test)

    prio_acc = accuracy_score(prio_y_test, prio_preds)
    prio_prec, prio_rec, prio_f1, _ = precision_recall_fscore_support(prio_y_test, prio_preds, average='weighted', zero_division=0)
    prio_report = classification_report(prio_y_test, prio_preds, zero_division=0, output_dict=True)
    prio_cm = confusion_matrix(prio_y_test, prio_preds, labels=sorted(prio_clf.classes_)).tolist()

    print(f"Priority Model Accuracy:  {prio_acc * 100:.2f}%")
    print(f"Priority Weighted F1:     {prio_f1:.4f}")
    joblib.dump(prio_clf, Config.PRIORITY_MODEL_PATH)
    print(f"Saved Priority Model to: {Config.PRIORITY_MODEL_PATH}")

    metrics_report['priority_model'] = {
        'model_name': 'Linear SVM (Calibrated) with TF-IDF',
        'accuracy': round(prio_acc, 4),
        'weighted_precision': round(prio_prec, 4),
        'weighted_recall': round(prio_rec, 4),
        'weighted_f1': round(prio_f1, 4),
        'classes': list(prio_clf.classes_),
        'confusion_matrix': prio_cm,
        'report': prio_report
    }

    # -------------------------------------------------------------------
    # MODEL 3: Sentiment Prediction (Calibrated Linear SVM)
    # -------------------------------------------------------------------
    print("\n------------------------------------------------------------------")
    print("3. Training Sentiment Analysis Model (Calibrated Linear SVM)...")
    sent_y_train = train_df['sentiment']
    sent_y_test = test_df['sentiment']

    base_svm_sent = LinearSVC(C=1.2, class_weight='balanced', random_state=RANDOM_SEED, max_iter=3000)
    sent_clf = CalibratedClassifierCV(estimator=base_svm_sent, cv=3)
    sent_clf.fit(X_train, sent_y_train)
    sent_preds = sent_clf.predict(X_test)

    sent_acc = accuracy_score(sent_y_test, sent_preds)
    sent_prec, sent_rec, sent_f1, _ = precision_recall_fscore_support(sent_y_test, sent_preds, average='weighted', zero_division=0)
    sent_report = classification_report(sent_y_test, sent_preds, zero_division=0, output_dict=True)
    sent_cm = confusion_matrix(sent_y_test, sent_preds, labels=sorted(sent_clf.classes_)).tolist()

    print(f"Sentiment Model Accuracy: {sent_acc * 100:.2f}%")
    print(f"Sentiment Weighted F1:    {sent_f1:.4f}")
    joblib.dump(sent_clf, Config.SENTIMENT_MODEL_PATH)
    print(f"Saved Sentiment Model to: {Config.SENTIMENT_MODEL_PATH}")

    metrics_report['sentiment_model'] = {
        'model_name': 'Linear SVM (Calibrated) with TF-IDF',
        'accuracy': round(sent_acc, 4),
        'weighted_precision': round(sent_prec, 4),
        'weighted_recall': round(sent_rec, 4),
        'weighted_f1': round(sent_f1, 4),
        'classes': list(sent_clf.classes_),
        'confusion_matrix': sent_cm,
        'report': sent_report
    }

    metrics_report['disclaimer'] = (
        "Evaluation performed on held-out 25% test split of synthetic educational dataset. "
        "Synthetic data evaluation demonstrates pipeline validity but does not guarantee identical accuracy "
        "on diverse real-world student complaints."
    )

    # Save metrics report
    metrics_path = os.path.join(Config.MODELS_DIR, 'model_metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics_report, f, indent=4)
    print(f"\nSaved evaluation metrics report to: {metrics_path}")
    print("==================================================================")
    print("               ALL MODELS TRAINED SUCCESSFULLY")
    print("==================================================================")

if __name__ == '__main__':
    train_all_models()
