import os
import joblib
import numpy as np
from scipy.sparse import hstack, csr_matrix
from .preprocessing import clean_text
from .feature_engineering import extract_features, FEATURE_NAMES, SUSPICIOUS_KEYWORDS

MODEL_FILES = {
    'Random Forest': 'random_forest.pkl',
    'Naive Bayes': 'naive_bayes.pkl',
    'XGBoost': 'xgboost.pkl',
}


class SpamDetector:
    """Loads trained models + vectorizer and classifies emails."""

    def __init__(self, model_dir='models'):
        self.model_dir = model_dir
        vec_path = os.path.join(model_dir, 'tfidf_vectorizer.pkl')

        if not os.path.exists(vec_path):
            raise FileNotFoundError(
                "Trained model not found. Run train_and_evaluate.py first."
            )

        self.vectorizer = joblib.load(vec_path)
        self._model_cache = {}

    def _load_model(self, model_name):
        """Load a model by name, with caching."""
        if model_name in self._model_cache:
            return self._model_cache[model_name]

        fname = MODEL_FILES.get(model_name, 'best_model.pkl')
        path = os.path.join(self.model_dir, fname)

        if not os.path.exists(path):
            path = os.path.join(self.model_dir, 'best_model.pkl')

        model = joblib.load(path)
        self._model_cache[model_name] = model
        return model

    def get_available_models(self):
        """Return list of available model names."""
        available = []
        for name, fname in MODEL_FILES.items():
            if os.path.exists(os.path.join(self.model_dir, fname)):
                available.append(name)
        return available

    def predict(self, email_text, sender='', device='', model_name=None):
        """
        Classify a single email.
        Returns dict with prediction, confidence, feature breakdown, and reasons.
        """
        if model_name is None:
            model_name = 'best'
            model = self._load_model('best')
        else:
            model = self._load_model(model_name)

        cleaned = clean_text(email_text)
        tfidf = self.vectorizer.transform([cleaned])

        feats = extract_features(email_text, sender, device)
        feat_array = np.array([[feats[f] for f in FEATURE_NAMES]])
        combined = hstack([tfidf, csr_matrix(feat_array)])

        prediction = model.predict(combined)[0]

        confidence = None
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(combined)[0]
            confidence = float(max(proba))

        reasons = self._build_reasons(email_text, feats, sender, device)

        return {
            'prediction': 'spam' if prediction == 1 else 'not spam',
            'is_spam': bool(prediction == 1),
            'confidence': confidence,
            'features': feats,
            'reasons': reasons,
            'model_used': model_name,
        }

    def predict_batch(self, texts, model_name=None):
        """Classify a list of emails."""
        return [self.predict(t, model_name=model_name) for t in texts]

    @staticmethod
    def _build_reasons(text, features, sender='', device=''):
        """Generate human-readable explanations."""
        reasons = []
        text_lower = text.lower()

        found_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in text_lower]
        if found_keywords:
            reasons.append(
                f"Contains suspicious keywords: {', '.join(found_keywords[:5])}"
            )
        if features['url_count'] > 2:
            reasons.append(f"Contains {features['url_count']} URLs")
        if features['uppercase_ratio'] > 0.3:
            reasons.append(
                f"High uppercase ratio ({features['uppercase_ratio']:.0%})"
            )
        if features['exclamation_count'] > 3:
            reasons.append(
                f"Excessive exclamation marks ({features['exclamation_count']})"
            )
        if features.get('sender_domain_suspicious'):
            reasons.append(f"Suspicious sender domain: {sender}")
        elif features.get('has_suspicious_domain'):
            reasons.append("Suspicious domain detected in email body")
        if features.get('device_is_automated'):
            reasons.append(f"Sent from automated system: {device}")
        if features.get('device_is_unknown'):
            reasons.append("Sent from unknown device/client")
        if features['has_html']:
            reasons.append("Contains HTML content")
        if features['dollar_sign_count'] > 0:
            reasons.append(
                f"Contains dollar signs ({features['dollar_sign_count']})"
            )
        if not reasons:
            reasons.append("No strong spam indicators found")

        return reasons
