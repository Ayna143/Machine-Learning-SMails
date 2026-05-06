import json
import os

import joblib
import numpy as np
from scipy.sparse import hstack, csr_matrix
from dotenv import load_dotenv

from .preprocessing import clean_text
from .embeddings import encode_texts
from .feature_engineering import (
    extract_features,
    extract_features_batch,
    FEATURE_NAMES,
    SUSPICIOUS_KEYWORDS,
)
from .context_llm import analyze_with_gemini
from .sender_analysis import score_sender_risk

load_dotenv()

MODEL_FILES = {
    'Random Forest': 'random_forest.pkl',
    'Naive Bayes': 'naive_bayes.pkl',
    'XGBoost': 'xgboost.pkl',
}

W_ML = 0.4
W_GEMINI = 0.5
W_SENDER = 0.1

def _load_spam_threshold(model_dir):
    env_v = os.environ.get('SPAM_PROBA_THRESHOLD', '').strip()
    if env_v:
        return min(max(float(env_v), 0.01), 0.99)
    cfg_path = os.path.join(model_dir, 'inference_config.json')
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, encoding='utf-8') as f:
                cfg = json.load(f)
            return min(max(float(cfg.get('spam_proba_threshold', 0.45)), 0.01), 0.99)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return 0.45

class SpamDetector:

    def __init__(self, model_dir='models'):
        self.model_dir = model_dir
        emb_path = os.path.join(model_dir, 'embedding_config.json')
        vec_path = os.path.join(model_dir, 'tfidf_vectorizer.pkl')

        self.use_embeddings = os.path.exists(emb_path)
        self.use_tfidf = False
        self.embedding_model_id = None
        self.vectorizer = None

        if self.use_embeddings:
            with open(emb_path, encoding='utf-8') as f:
                cfg = json.load(f)
            self.embedding_model_id = cfg.get('model_id', '').strip() or None
            self.use_tfidf = bool(cfg.get('use_tfidf', False))
            if self.use_tfidf:
                if not os.path.exists(vec_path):
                    raise FileNotFoundError(
                        "Hybrid mode expects models/tfidf_vectorizer.pkl but it is missing."
                    )
                self.vectorizer = joblib.load(vec_path)
        elif os.path.exists(vec_path):
            self.vectorizer = joblib.load(vec_path)
            self.use_tfidf = True
        else:
            raise FileNotFoundError(
                "Trained model not found. Run train_and_evaluate.py first "
                "(expects embedding_config.json or tfidf_vectorizer.pkl)."
            )

        self.spam_proba_threshold = _load_spam_threshold(model_dir)
        self._model_cache = {}
        self._llm_cache = {}

    @staticmethod
    def _predict_label_from_proba(model, proba_row, threshold):
        proba_row = np.asarray(proba_row).reshape(-1)
        classes = np.asarray(model.classes_)
        if len(classes) == 2 and 0 in classes and 1 in classes:
            idx_spam = int(np.where(classes == 1)[0][0])
            p_spam = float(proba_row[idx_spam])
            pred = 1 if p_spam >= threshold else 0
            return pred, p_spam
        pred = int(classes[np.argmax(proba_row)])
        p_best = float(np.max(proba_row))
        return pred, p_best

    def _load_model(self, model_name):
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
        return [name for name, fname in MODEL_FILES.items() if os.path.exists(os.path.join(self.model_dir, fname))]

    def _build_text_matrix(self, texts, senders=None, devices=None):
        texts = [t if isinstance(t, str) else '' for t in texts]
        n = len(texts)
        if senders is None:
            senders = [''] * n
        if devices is None:
            devices = [''] * n

        feat_matrix = extract_features_batch(texts, senders, devices)

        if self.use_embeddings:
            X_emb = encode_texts(
                texts,
                model_id=self.embedding_model_id,
                batch_size=32,
                show_progress=False,
            )
            if self.use_tfidf and self.vectorizer is not None:
                cleaned = [clean_text(t) for t in texts]
                X_tfidf = self.vectorizer.transform(cleaned)
                X_emb_sparse = csr_matrix(np.maximum(np.asarray(X_emb, dtype=np.float32), 0.0))
                combined = hstack([X_tfidf, X_emb_sparse, csr_matrix(feat_matrix)])
            else:
                combined = np.hstack([np.asarray(X_emb, dtype=np.float32), feat_matrix])
        else:
            cleaned = [clean_text(t) for t in texts]
            X_tfidf = self.vectorizer.transform(cleaned)
            combined = hstack([X_tfidf, csr_matrix(feat_matrix)])

        return combined, feat_matrix

    def _ml_predict(self, model, combined):
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(combined)[0]
            pred, p_spam = self._predict_label_from_proba(model, proba, self.spam_proba_threshold)
            confidence = float(np.max(proba))
            ml_spam_score = float(p_spam * 100.0)
        else:
            pred = int(model.predict(combined)[0])
            confidence = None
            ml_spam_score = 100.0 if pred == 1 else 0.0
            p_spam = None
        return pred, confidence, p_spam, ml_spam_score

    @staticmethod
    def _gemini_spam_score(verdict: str, confidence: float) -> float:
        return confidence if verdict == 'spam' else (100.0 - confidence)

    @staticmethod
    def _finalize_weighted(ml_score, gemini_result, sender_result, ml_pred_label):
        sender_score = float(sender_result['score'])
        gemini_ok = bool(gemini_result.get('ok'))
        if gemini_ok:
            g_score = SpamDetector._gemini_spam_score(
                gemini_result['verdict'],
                float(gemini_result['confidence']),
            )
            final_score = (W_ML * ml_score) + (W_GEMINI * g_score) + (W_SENDER * sender_score)
            note = ""
        else:
            g_score = 50.0

            base = (W_ML * ml_score) + (W_SENDER * sender_score)
            final_score = base / (W_ML + W_SENDER)
            note = f"Gemini unavailable ({gemini_result.get('error', 'unknown error')}); used ML+sender fallback."

        final_score = float(min(max(final_score, 0.0), 100.0))
        final_verdict = "Spam" if final_score >= 50.0 else "Ham"

        if not note and final_verdict.lower() != ml_pred_label.lower():
            note = f"ML model predicted {ml_pred_label} but context/sender fusion overrode it."
        elif not note:
            note = "ML, context, and sender signals are aligned."

        return final_verdict, final_score, g_score, note

    def _get_llm_result(self, email_text, sender, llm_enabled=True):
        if not llm_enabled:
            return {
                "verdict": "ham",
                "confidence": 50.0,
                "reason": "Gemini disabled for this call.",
                "ok": False,
                "error": "Gemini disabled",
            }
        key = (email_text, sender)
        if key in self._llm_cache:
            return self._llm_cache[key]
        result = analyze_with_gemini(email_text, sender)
        self._llm_cache[key] = result
        return result

    def predict(self, email_text, sender='', device='', model_name=None, llm_enabled=True):
        if model_name is None:
            model_name = 'best'
            model = self._load_model('best')
        else:
            model = self._load_model(model_name)

        combined, feat_matrix = self._build_text_matrix([email_text], [sender], [device])
        row_feats = {FEATURE_NAMES[j]: float(feat_matrix[0, j]) for j in range(len(FEATURE_NAMES))}

        pred, confidence, p_spam, ml_score = self._ml_predict(model, combined)
        ml_prediction = "Spam" if pred == 1 else "Ham"

        llm = self._get_llm_result(email_text, sender, llm_enabled=llm_enabled)
        sender_result = score_sender_risk(sender, email_text)
        final_verdict, final_score, gemini_score, note = self._finalize_weighted(
            ml_score, llm, sender_result, ml_prediction
        )

        reasons = self._build_reasons(email_text, row_feats, sender, device, is_spam=(pred == 1), use_semantics=self.use_embeddings)
        if llm.get("reason"):
            reasons.append(f"Gemini: {llm['reason']}")
        if sender_result["reasons"]:
            reasons.append("Sender risk: " + "; ".join(sender_result["reasons"][:2]))

        out = {

            'prediction': 'spam' if final_verdict == "Spam" else 'not spam',
            'is_spam': bool(final_verdict == "Spam"),
            'confidence': round(final_score / 100.0, 4),
            'features': row_feats,
            'reasons': reasons,
            'model_used': model_name,
            'semantic_model': self.use_embeddings,
            'spam_proba_threshold': self.spam_proba_threshold,

            'final_verdict': final_verdict,
            'ml_prediction': ml_prediction,
            'gemini_verdict': llm.get('verdict', 'ham').capitalize(),
            'gemini_reason': llm.get('reason', ''),
            'sender_risk': sender_result['risk'],
            'note': note,
            'confidence_score': round(final_score, 2),
            'weights': {'ml': W_ML, 'gemini': W_GEMINI, 'sender': W_SENDER},
            'ml_spam_score': round(ml_score, 2),
            'gemini_spam_score': round(gemini_score, 2),
            'sender_spam_score': round(float(sender_result['score']), 2),
        }
        if p_spam is not None:
            out['spam_probability'] = round(float(p_spam), 4)
        return out

    def predict_batch(self, texts, model_name=None, llm_enabled=False):
        texts = [t if isinstance(t, str) else '' for t in texts]
        if not texts:
            return []
        if model_name is None:
            model_name = 'best'
        out = []
        for txt in texts:
            out.append(self.predict(txt, model_name=model_name, llm_enabled=llm_enabled))
        return out

    @staticmethod
    def _build_reasons(text, features, sender='', device='', *, is_spam=False, use_semantics=False):
        reasons = []
        text_lower = text.lower()

        found_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in text_lower]
        if use_semantics:
            reasons.append(
                "Uses semantic embeddings (overall meaning/context), plus structure — "
                + ("predicted spam by ML layer." if is_spam else "predicted legitimate by ML layer.")
            )
        if found_keywords:
            reasons.append(
                f"Keyword overlap (supporting signal only): {', '.join(found_keywords[:5])}"
            )
        if features.get('url_count', 0) > 2:
            reasons.append(f"Contains {features['url_count']} URLs")
        if features.get('uppercase_ratio', 0) > 0.3:
            reasons.append(f"High uppercase ratio ({features['uppercase_ratio']:.0%})")
        if features.get('exclamation_count', 0) > 3:
            reasons.append(f"Excessive exclamation marks ({features['exclamation_count']})")
        if features.get('sender_domain_suspicious'):
            reasons.append(f"Suspicious sender domain: {sender}")
        elif features.get('has_suspicious_domain'):
            reasons.append("Suspicious domain detected in email body")
        if features.get('device_is_automated'):
            reasons.append(f"Sent from automated system: {device}")
        if features.get('device_is_unknown'):
            reasons.append("Sent from unknown device/client")
        if features.get('has_html'):
            reasons.append("Contains HTML content")
        if features.get('dollar_sign_count', 0) > 0:
            reasons.append(f"Contains dollar signs ({features['dollar_sign_count']})")
        if not reasons:
            reasons.append("No strong spam indicators found")
        return reasons
