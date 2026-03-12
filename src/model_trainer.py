import json
import numpy as np
from scipy.sparse import hstack, csr_matrix, issparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import MultinomialNB
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report
)
import joblib
import os


def _combine_features(X_tfidf, X_engineered):
    """Combine sparse TF-IDF matrix with dense engineered features."""
    eng_sparse = csr_matrix(X_engineered)
    if issparse(X_tfidf):
        return hstack([X_tfidf, eng_sparse])
    return np.hstack([X_tfidf, X_engineered])


def _get_models():
    """Return the three models specified in the research paper."""
    return {
        'Random Forest': RandomForestClassifier(
            n_estimators=100,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        ),
        'Naive Bayes': MultinomialNB(alpha=1.0),
        'XGBoost': XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.15,
            eval_metric='logloss',
            random_state=42,
            n_jobs=1,
            tree_method='hist',
        ),
    }


def train_and_compare(X_tfidf, X_engineered, y, dataset_name="Dataset"):
    """
    Train RF, NB, and XGBoost on combined features.
    Uses 80-20 split + 5-fold cross-validation.
    Returns dict of results per model.
    """
    X_combined = _combine_features(X_tfidf, X_engineered)

    X_train, X_test, y_train, y_test = train_test_split(
        X_combined, y, test_size=0.2, random_state=42, stratify=y
    )

    models = _get_models()
    results = {}

    print(f"\n{'='*60}")
    print(f"  TRAINING & EVALUATION — {dataset_name}")
    print(f"{'='*60}")
    print(f"  Total samples : {X_combined.shape[0]}")
    print(f"  Train samples : {X_train.shape[0]}")
    print(f"  Test samples  : {X_test.shape[0]}")
    print(f"  Feature dims  : {X_combined.shape[1]}")
    print(f"{'='*60}\n")

    for name, model in models.items():
        print(f"  Training {name}...")

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        cm = confusion_matrix(y_test, y_pred)

        cv_scores = cross_val_score(model, X_combined, y, cv=3, scoring='f1')

        results[name] = {
            'accuracy': acc,
            'precision': prec,
            'recall': rec,
            'f1_score': f1,
            'confusion_matrix': cm,
            'cv_f1_mean': cv_scores.mean(),
            'cv_f1_std': cv_scores.std(),
            'model': model,
            'report': classification_report(y_test, y_pred, target_names=['Ham', 'Spam'])
        }

        print(f"    Accuracy  : {acc:.4f}")
        print(f"    Precision : {prec:.4f}")
        print(f"    Recall    : {rec:.4f}")
        print(f"    F1-Score  : {f1:.4f}")
        print(f"    CV F1     : {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
        print()

    return results


def select_best_model(results):
    """Pick the model with the highest F1-score."""
    best_name = max(results, key=lambda k: results[k]['f1_score'])
    return best_name, results[best_name]


def save_all_models(results, vectorizer, model_dir='models'):
    """Save every trained model, the vectorizer, and a metrics JSON."""
    os.makedirs(model_dir, exist_ok=True)

    model_files = {
        'Random Forest': 'random_forest.pkl',
        'Naive Bayes': 'naive_bayes.pkl',
        'XGBoost': 'xgboost.pkl',
    }

    for name, info in results.items():
        fname = model_files.get(name, name.lower().replace(' ', '_') + '.pkl')
        joblib.dump(info['model'], os.path.join(model_dir, fname))

    joblib.dump(vectorizer, os.path.join(model_dir, 'tfidf_vectorizer.pkl'))

    best_name = max(results, key=lambda k: results[k]['f1_score'])
    best_file = model_files[best_name]
    best_path = os.path.join(model_dir, 'best_model.pkl')
    joblib.dump(results[best_name]['model'], best_path)

    print(f"  All models saved to {model_dir}/")
    print(f"  Best model: {best_name} -> best_model.pkl")
    return best_name


def save_metrics(all_results, model_dir='models'):
    """Save evaluation metrics for all datasets/models to JSON."""
    metrics = {}

    for ds_name, results in all_results.items():
        metrics[ds_name] = {}
        for model_name, info in results.items():
            cm = info['confusion_matrix']
            metrics[ds_name][model_name] = {
                'accuracy': round(info['accuracy'], 4),
                'precision': round(info['precision'], 4),
                'recall': round(info['recall'], 4),
                'f1_score': round(info['f1_score'], 4),
                'cv_f1_mean': round(info['cv_f1_mean'], 4),
                'cv_f1_std': round(info['cv_f1_std'], 4),
                'confusion_matrix': cm.tolist(),
            }

    path = os.path.join(model_dir, 'metrics.json')
    with open(path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"  Metrics saved to {path}")


def print_comparison_table(all_results):
    """Pretty-print a comparison table across datasets and models."""
    print(f"\n{'='*80}")
    print("  FINAL MODEL COMPARISON")
    print(f"{'='*80}")
    header = f"  {'Dataset':<20} {'Model':<18} {'Acc':>7} {'Prec':>7} {'Rec':>7} {'F1':>7} {'CV-F1':>7}"
    print(header)
    print(f"  {'-'*74}")

    for ds_name, results in all_results.items():
        for model_name, metrics in results.items():
            row = (
                f"  {ds_name:<20} {model_name:<18} "
                f"{metrics['accuracy']:>7.4f} {metrics['precision']:>7.4f} "
                f"{metrics['recall']:>7.4f} {metrics['f1_score']:>7.4f} "
                f"{metrics['cv_f1_mean']:>7.4f}"
            )
            print(row)
        print()
    print(f"{'='*80}")
