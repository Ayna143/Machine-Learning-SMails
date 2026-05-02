import json
import numpy as np
from scipy.sparse import hstack, csr_matrix, issparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import MultinomialNB, GaussianNB
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


def _combine_dense_text_and_engineered(X_dense_text, X_engineered):
    """Stack dense semantic embeddings with engineered features."""
    if X_dense_text.ndim != 2:
        raise ValueError('X_dense_text must be 2D')
    eng = np.asarray(X_engineered, dtype=np.float32)
    xtxt = np.asarray(X_dense_text, dtype=np.float32)
    return np.hstack([xtxt, eng])


def _combine_hybrid_features(X_tfidf, X_semantic, X_engineered):
    """
    Combine sparse TF-IDF with dense semantic embeddings and engineered features.
    Semantic vectors are clipped at 0 so MultinomialNB remains valid in hybrid mode.
    """
    sem = np.asarray(X_semantic, dtype=np.float32)
    sem = np.maximum(sem, 0.0)
    sem_sparse = csr_matrix(sem)
    eng_sparse = csr_matrix(np.asarray(X_engineered, dtype=np.float32))
    if issparse(X_tfidf):
        return hstack([X_tfidf, sem_sparse, eng_sparse])
    return np.hstack([np.asarray(X_tfidf), sem, np.asarray(X_engineered)])


def _get_models(*, use_gaussian_nb: bool = False):
    """Return the three models. Use GaussianNB for dense (e.g. embedding) features."""
    nb = (
        GaussianNB(var_smoothing=1e-9)
        if use_gaussian_nb
        else MultinomialNB(alpha=1.0)
    )
    return {
        'Random Forest': RandomForestClassifier(
            n_estimators=100,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        ),
        'Naive Bayes': nb,
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


def train_and_compare(
    X_tfidf,
    X_engineered,
    y,
    dataset_name="Dataset",
    *,
    dense_text_features: bool = False,
    X_semantic=None,
):
    """
    Train RF, NB, and XGBoost on combined features.
    When dense_text_features is True, X_tfidf must be a dense 2D array (embeddings).
    Uses 80-20 split + 3-fold cross-validation (when both classes exist).
    Returns dict of results per model.
    """
    y = np.asarray(y)
    n_classes = len(np.unique(y))

    hybrid_mode = X_semantic is not None

    if hybrid_mode:
        X_combined = _combine_hybrid_features(X_tfidf, X_semantic, X_engineered)
    elif dense_text_features:
        X_combined = _combine_dense_text_and_engineered(X_tfidf, X_engineered)
    else:
        X_combined = _combine_features(X_tfidf, X_engineered)

    split_kw = {'test_size': 0.2, 'random_state': 42}
    if n_classes >= 2:
        split_kw['stratify'] = y
    X_train, X_test, y_train, y_test = train_test_split(X_combined, y, **split_kw)

    models = _get_models(use_gaussian_nb=(dense_text_features and not hybrid_mode))
    if n_classes < 2:
        print(
            f"\n  WARNING — {dataset_name}: labels have only ONE class {np.unique(y)}. "
            "Use label=1 for spam and label=0 for ham. Skipping XGBoost (needs both classes)."
        )
        models.pop('XGBoost', None)

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
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])

        if n_classes >= 2:
            cv_scores = cross_val_score(model, X_combined, y, cv=3, scoring='f1')
            cv_mean, cv_std = cv_scores.mean(), cv_scores.std()
        else:
            cv_scores = np.array([np.nan])
            cv_mean, cv_std = np.nan, np.nan

        report = classification_report(
            y_test,
            y_pred,
            labels=[0, 1],
            target_names=['Ham', 'Spam'],
            zero_division=0,
        )

        results[name] = {
            'accuracy': acc,
            'precision': prec,
            'recall': rec,
            'f1_score': f1,
            'confusion_matrix': cm,
            'cv_f1_mean': float(cv_mean),
            'cv_f1_std': float(cv_std),
            'model': model,
            'report': report,
        }

        print(f"    Accuracy  : {acc:.4f}")
        print(f"    Precision : {prec:.4f}")
        print(f"    Recall    : {rec:.4f}")
        print(f"    F1-Score  : {f1:.4f}")
        if n_classes >= 2:
            print(f"    CV F1     : {cv_mean:.4f} (+/- {cv_std:.4f})")
        else:
            print(f"    CV F1     : n/a (single class)")
        print()

    return results


def select_best_model(results):
    """Pick the model with the highest cross-validated F1 score."""
    best_name = max(results, key=lambda k: results[k]['cv_f1_mean'])
    return best_name, results[best_name]


def save_all_models(
    results,
    vectorizer,
    model_dir='models',
    *,
    embedding_model_id=None,
    use_tfidf_with_embeddings=False,
):
    """
    Save every trained model. Pass embedding_model_id for semantic pipeline (no TF-IDF).
    """
    os.makedirs(model_dir, exist_ok=True)

    model_files = {
        'Random Forest': 'random_forest.pkl',
        'Naive Bayes': 'naive_bayes.pkl',
        'XGBoost': 'xgboost.pkl',
    }

    for name, info in results.items():
        fname = model_files.get(name, name.lower().replace(' ', '_') + '.pkl')
        joblib.dump(info['model'], os.path.join(model_dir, fname))

    emb_cfg_path = os.path.join(model_dir, 'embedding_config.json')
    tfidf_path = os.path.join(model_dir, 'tfidf_vectorizer.pkl')

    if embedding_model_id:
        cfg = {
            'model_id': embedding_model_id,
            'pipeline': 'sentence_transformer',
            'use_tfidf': bool(use_tfidf_with_embeddings),
        }
        with open(emb_cfg_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
        if use_tfidf_with_embeddings and vectorizer is not None:
            joblib.dump(vectorizer, tfidf_path)
        elif os.path.exists(tfidf_path):
            try:
                os.remove(tfidf_path)
            except OSError:
                pass
        print(f"  Embedding config saved to {emb_cfg_path}")
    else:
        joblib.dump(vectorizer, tfidf_path)
        if os.path.exists(emb_cfg_path):
            try:
                os.remove(emb_cfg_path)
            except OSError:
                pass

    def _cv_sort_key(info):
        m = info['cv_f1_mean']
        if m is None or (isinstance(m, float) and np.isnan(m)):
            return -1.0
        return float(m)

    best_name = max(results, key=lambda k: _cv_sort_key(results[k]))
    best_file = model_files[best_name]
    best_path = os.path.join(model_dir, 'best_model.pkl')
    joblib.dump(results[best_name]['model'], best_path)

    print(f"  All models saved to {model_dir}/")
    print(f"  Best model: {best_name} -> best_model.pkl")
    return best_name


def save_metrics(all_results, model_dir='models'):
    """Save evaluation metrics for all datasets/models to JSON."""
    metrics = {}

    def _json_num(x, nd=4):
        if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
            return None
        return round(float(x), nd)

    for ds_name, results in all_results.items():
        metrics[ds_name] = {}
        for model_name, info in results.items():
            cm = info['confusion_matrix']
            metrics[ds_name][model_name] = {
                'accuracy': _json_num(info['accuracy']),
                'precision': _json_num(info['precision']),
                'recall': _json_num(info['recall']),
                'f1_score': _json_num(info['f1_score']),
                'cv_f1_mean': _json_num(info['cv_f1_mean']),
                'cv_f1_std': _json_num(info['cv_f1_std']),
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

    def _fmt_metric(x, width=7):
        if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
            return f"{'n/a':>{width}}"
        return f"{x:>{width}.4f}"

    for ds_name, results in all_results.items():
        for model_name, metrics in results.items():
            row = (
                f"  {ds_name:<20} {model_name:<18} "
                f"{_fmt_metric(metrics['accuracy'])} {_fmt_metric(metrics['precision'])} "
                f"{_fmt_metric(metrics['recall'])} {_fmt_metric(metrics['f1_score'])} "
                f"{_fmt_metric(metrics['cv_f1_mean'])}"
            )
            print(row)
        print()
    print(f"{'='*80}")
