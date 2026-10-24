import os
import re
import joblib
from config import Config
from ml.preprocessing import clean_text

class ModelManager:
    _instance = None
    
    def __init__(self):
        self.vectorizer = None
        self.category_model = None
        self.priority_model = None
        self.sentiment_model = None
        self.load_models()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ModelManager()
        return cls._instance

    def load_models(self):
        """Loads serialized TF-IDF vectorizer and trained models from disk."""
        if os.path.exists(Config.VECTORIZER_PATH):
            self.vectorizer = joblib.load(Config.VECTORIZER_PATH)
        if os.path.exists(Config.CATEGORY_MODEL_PATH):
            self.category_model = joblib.load(Config.CATEGORY_MODEL_PATH)
        if os.path.exists(Config.PRIORITY_MODEL_PATH):
            self.priority_model = joblib.load(Config.PRIORITY_MODEL_PATH)
        if os.path.exists(Config.SENTIMENT_MODEL_PATH):
            self.sentiment_model = joblib.load(Config.SENTIMENT_MODEL_PATH)

    def is_loaded(self):
        return all([self.vectorizer, self.category_model, self.priority_model, self.sentiment_model])

def check_safety_escalation(text: str) -> tuple[bool, str]:
    """
    Separate safety escalation mechanism for complaints involving immediate physical danger.
    Does not depend solely on ML predictions for safety-critical situations.
    """
    text_lower = text.lower()
    for kw in Config.CRITICAL_SAFETY_KEYWORDS:
        # Match word boundaries or substring in phrases like 'short circuit', 'exposed wire'
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text_lower):
            return True, f"Critical safety risk identified ('{kw}'). Urgency escalated to HIGH."
    return False, ""

def predict_grievance(title: str, description: str) -> dict:
    """
    Runs the complete NLP inference pipeline:
    1. Preprocessing
    2. TF-IDF vectorization
    3. Category prediction & confidence score
    4. Priority prediction + Safety Escalation
    5. Sentiment classification
    """
    manager = ModelManager.get_instance()
    if not manager.is_loaded():
        manager.load_models()
        if not manager.is_loaded():
            raise RuntimeError("ML Models are not initialized. Run ml/train_models.py first.")

    combined_text = f"{title}. {description}"
    cleaned = clean_text(combined_text)

    # Transform text using the trained TF-IDF vectorizer
    X = manager.vectorizer.transform([cleaned])

    # 1. Category Prediction
    cat_pred = manager.category_model.predict(X)[0]
    cat_proba = 0.85
    if hasattr(manager.category_model, 'predict_proba'):
        probas = manager.category_model.predict_proba(X)[0]
        cat_proba = float(max(probas))

    # 2. Priority Prediction
    prio_pred = manager.priority_model.predict(X)[0]
    
    # Safety Escalation Mechanism (Rule-based safety net for physical hazards)
    is_escalated, escalation_reason = check_safety_escalation(combined_text)
    if is_escalated:
        prio_pred = "High"

    # 3. Sentiment Prediction
    sent_pred = manager.sentiment_model.predict(X)[0]

    return {
        'category': cat_pred,
        'confidence': round(cat_proba, 2),
        'priority': prio_pred,
        'is_safety_escalated': is_escalated,
        'escalation_reason': escalation_reason,
        'sentiment': sent_pred
    }
