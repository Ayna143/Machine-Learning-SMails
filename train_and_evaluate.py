import json
import os
import pandas as pd

from sklearn.model_selection import train_test_split

from src.preprocessing import clean_text, build_tfidf_vectorizer
from src.feature_engineering import extract_features_batch
from src.embeddings import encode_texts, DEFAULT_EMBEDDING_MODEL_ID
from src.model_trainer import (
    train_and_compare,
    save_all_models, save_metrics, print_comparison_table
)

DATASETS_DIR = 'datasets'
MODELS_DIR = 'models'
_DEFAULT_THIRD = os.path.join(DATASETS_DIR, 'spamassassin_public.csv')
CUSTOM_DATASET_PATH = os.environ.get('CUSTOM_DATASET_PATH', _DEFAULT_THIRD)

def _custom_augment_repeat():

    v = os.environ.get('CUSTOM_AUGMENT_REPEAT', '25').strip()
    try:
        n = int(v)
    except ValueError:
        n = 25
    return max(1, n)

def save_inference_config(model_dir):

    thr = float(os.environ.get('SPAM_PROBA_THRESHOLD', '0.45'))
    thr = min(max(thr, 0.01), 0.99)
    rep = _custom_augment_repeat()
    path = os.path.join(model_dir, 'inference_config.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(
            {
                'spam_proba_threshold': thr,
                'custom_augment_repeat': rep,
            },
            f,
            indent=2,
        )
    print(f"  Inference config saved to {path} (P(spam) >= {thr} -> spam)")

def resolve_custom_augment_path():
    env_path = os.environ.get('CUSTOM_AUGMENT_PATH', '').strip()
    if env_path:
        if os.path.isfile(env_path):
            return env_path
        joined = os.path.join(DATASETS_DIR, os.path.basename(env_path))
        if os.path.isfile(joined):
            return joined
    for name in ('custom_spam_augment.csv', 'custom_spam.csv'):
        p = os.path.join(DATASETS_DIR, name)
        if os.path.isfile(p):
            return p
    return None

def _embed_max_samples():

    v = os.environ.get('SM_EMBED_MAX_SAMPLES', '150000').strip().lower()
    if v in ('', '0', 'none', 'full', 'all'):
        return None
    return int(v)

def _use_tfidf_only():
    return os.environ.get('USE_TFIDF_ONLY', '').strip() in ('1', 'true', 'yes')

def stratified_subsample(df, max_rows, random_state=42):

    if max_rows is None or len(df) <= max_rows:
        return df.reset_index(drop=True)
    frac = max_rows / len(df)
    sub, _ = train_test_split(
        df,
        train_size=frac,
        stratify=df['label'],
        random_state=random_state,
    )
    return sub.sample(frac=1, random_state=random_state).reset_index(drop=True)

def load_dataset(path, name):

    print(f"\n  Loading {name} from {path}...")
    df = pd.read_csv(path, encoding='utf-8', on_bad_lines='skip')

    lower_map = {c.lower().strip(): c for c in df.columns}
    text_col = None
    label_col = None
    for cand in ('text', 'message', 'email', 'content', 'v2'):
        if cand in lower_map:
            text_col = lower_map[cand]
            break
    for cand in ('label', 'spam', 'class', 'v1'):
        if cand in lower_map:
            label_col = lower_map[cand]
            break

    if text_col is None or label_col is None:
        raise ValueError(
            f"{name}: required text/label columns not found. Columns: {list(df.columns)}"
        )

    if text_col != 'text':
        df = df.rename(columns={text_col: 'text'})
    if label_col != 'label':
        df = df.rename(columns={label_col: 'label'})

    df = df.dropna(subset=['text', 'label'])

    def _to_label(v):
        s = str(v).strip().lower()
        if s in ('1', 'spam', 'true', 'yes'):
            return 1
        return 0
    df['label'] = df['label'].apply(_to_label).astype(int)

    if 'sender' not in df.columns:
        df['sender'] = ''
    if 'device' not in df.columns:
        df['device'] = ''

    df['sender'] = df['sender'].fillna('').astype(str)
    df['device'] = df['device'].fillna('').astype(str)

    print(f"    Total samples : {len(df)}")
    print(f"    Spam          : {(df['label'] == 1).sum()}")
    print(f"    Ham           : {(df['label'] == 0).sum()}")
    has_sender = (df['sender'] != '').sum()
    has_device = (df['device'] != '').sum()
    if has_sender > 0:
        print(f"    With sender   : {has_sender}")
    if has_device > 0:
        print(f"    With device   : {has_device}")
    return df

def run_pipeline_tfidf(df, dataset_name, vectorizer=None):

    print(f"\n  Preprocessing {dataset_name} (TF-IDF)...")
    df['cleaned'] = df['text'].apply(clean_text)

    if vectorizer is None:
        vectorizer, X_tfidf = build_tfidf_vectorizer(df['cleaned'])
    else:
        X_tfidf = vectorizer.transform(df['cleaned'])

    print(f"  Extracting engineered features (text + sender + device)...")
    X_engineered = extract_features_batch(
        df['text'].tolist(),
        df['sender'].tolist(),
        df['device'].tolist(),
    )

    y = df['label'].values

    results = train_and_compare(
        X_tfidf, X_engineered, y, dataset_name, dense_text_features=False
    )
    return results, vectorizer

def run_pipeline_embeddings(df, dataset_name, vectorizer=None, max_samples_cap=None):

    cap_desc = 'no cap' if max_samples_cap is None else str(max_samples_cap)
    print(f"\n  Hybrid semantic pipeline for {dataset_name} (embed cap: {cap_desc})...")
    df_work = stratified_subsample(df, max_samples_cap)
    if len(df_work) < len(df):
        print(f"    Stratified sample: {len(df)} -> {len(df_work)} rows for embedding speed/memory.")

    print(f"  Building TF-IDF features for {len(df_work)} rows...")
    df_work['cleaned'] = df_work['text'].apply(clean_text)
    if vectorizer is None:
        vectorizer, X_tfidf = build_tfidf_vectorizer(df_work['cleaned'])
    else:
        X_tfidf = vectorizer.transform(df_work['cleaned'])

    texts = df_work['text'].tolist()
    show_bar = len(texts) >= 2000
    print(f"  Encoding {len(texts)} texts with {DEFAULT_EMBEDDING_MODEL_ID}...")
    X_emb = encode_texts(texts, model_id=DEFAULT_EMBEDDING_MODEL_ID, show_progress=show_bar)

    print(f"  Extracting engineered features (text + sender + device)...")
    X_engineered = extract_features_batch(
        texts,
        df_work['sender'].tolist(),
        df_work['device'].tolist(),
    )

    y = df_work['label'].values

    results = train_and_compare(
        X_tfidf,
        X_engineered,
        y,
        dataset_name,
        dense_text_features=False,
        X_semantic=X_emb,
    )
    return results, vectorizer

def run_pipeline(df, dataset_name, vectorizer=None, use_embeddings=True, max_samples_cap=None):
    if use_embeddings:
        results, vectorizer = run_pipeline_embeddings(
            df, dataset_name, vectorizer=vectorizer, max_samples_cap=max_samples_cap
        )
        return results, vectorizer
    return run_pipeline_tfidf(df, dataset_name, vectorizer)

def main():
    sms_path = os.path.join(DATASETS_DIR, 'sms_spam.csv')
    enron_path = os.path.join(DATASETS_DIR, 'enron_spam.csv')
    custom_path = CUSTOM_DATASET_PATH

    use_embed = not _use_tfidf_only()
    max_cap = _embed_max_samples()

    if use_embed and max_cap is not None:
        print(
            f"\n  Using SM_EMBED_MAX_SAMPLES={max_cap} (unset env or use 'full' for all rows — slower, usually more accurate).\n"
        )

    if not os.path.exists(sms_path) or not os.path.exists(enron_path):
        print("  Datasets not found. Running download script...")
        from download_datasets import main as download
        download()

    if not os.path.exists(custom_path):
        if custom_path == _DEFAULT_THIRD or os.path.basename(custom_path) == 'spamassassin_public.csv':
            print("  Third dataset not found. Downloading SpamAssassin Public Corpus...")
            from download_datasets import download_spamassassin_public
            download_spamassassin_public()
        else:
            raise FileNotFoundError(
                f"Custom dataset not found at: {custom_path}\n"
                "Set CUSTOM_DATASET_PATH or add datasets/spamassassin_public.csv (run download_datasets.py)."
            )

    if not os.path.exists(custom_path):
        raise FileNotFoundError(f"Custom dataset still missing after download: {custom_path}")

    sms_df = load_dataset(sms_path, "SMS Spam Collection")
    enron_df = load_dataset(enron_path, "Enron Email Dataset")
    third_name = (
        "SpamAssassin Public Corpus"
        if 'spamassassin' in os.path.basename(custom_path).lower()
        else "Third dataset (custom CSV)"
    )
    third_metrics_key = (
        "SpamAssassin"
        if 'spamassassin' in os.path.basename(custom_path).lower()
        else "Third dataset"
    )
    full_df = load_dataset(custom_path, third_name)

    augment_path = resolve_custom_augment_path()
    augment_df = None
    if augment_path:
        augment_df = load_dataset(augment_path, "Custom augment (your Gmail/spam adds)")
        print(f"    (loaded from: {augment_path})")
        ns = int((augment_df['label'] == 1).sum())
        nh = int((augment_df['label'] == 0).sum())
        if ns == 0 or nh == 0:
            print(
                "\n  *** IMPORTANT: Custom CSV has only one class "
                f"(spam={ns}, ham={nh}). Spam-folder emails MUST use label column = 1 "
                "(not 0). Otherwise training treats them as ham.\n"
            )
    else:
        print(
            "\n  Note: No custom augment file found. Add one of:\n"
            f"    {os.path.join(DATASETS_DIR, 'custom_spam_augment.csv')}\n"
            f"    {os.path.join(DATASETS_DIR, 'custom_spam.csv')}\n"
            "  Or set CUSTOM_AUGMENT_PATH to your CSV path."
        )

    sms_results, _ = run_pipeline(
        sms_df, "SMS Spam Collection", use_embeddings=use_embed, max_samples_cap=max_cap
    )
    enron_results, _ = run_pipeline(
        enron_df, "Enron Email Dataset", use_embeddings=use_embed, max_samples_cap=max_cap
    )
    third_results, _ = run_pipeline(
        full_df, third_name, use_embeddings=use_embed, max_samples_cap=max_cap
    )

    augment_results = None
    if augment_df is not None:
        augment_results, _ = run_pipeline(
            augment_df, "Custom augment", use_embeddings=use_embed, max_samples_cap=max_cap
        )

    print("\n  Combining all datasets for final training...")
    parts = [sms_df, enron_df, full_df]
    if augment_df is not None:
        parts.append(augment_df)
    combined_df = pd.concat(parts, ignore_index=True)
    before = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=['text', 'label'], keep='first')
    dupes = before - len(combined_df)
    if dupes:
        print(f"    Removed {dupes} duplicate rows (same text + label already present).")

    repeat = _custom_augment_repeat()
    if augment_df is not None and repeat > 1:
        aug_unique = augment_df.drop_duplicates(subset=['text', 'label'], keep='first')
        extra = pd.concat([aug_unique] * (repeat - 1), ignore_index=True)
        combined_df = pd.concat([combined_df, extra], ignore_index=True)
        print(
            f"    Custom augment weighted ~{repeat}x "
            f"({len(aug_unique)} unique rows → {len(aug_unique) * repeat} augment-colored rows). "
            f"Set CUSTOM_AUGMENT_REPEAT=1 to disable."
        )

    combined_df = combined_df.sample(frac=1, random_state=42).reset_index(drop=True)

    combined_results, combined_vectorizer = run_pipeline(
        combined_df,
        "Combined (All Datasets)",
        use_embeddings=use_embed,
        max_samples_cap=max_cap,
    )

    all_results = {
        'SMS Spam': sms_results,
        'Enron Email': enron_results,
        third_metrics_key: third_results,
        'Combined': combined_results,
    }
    if augment_results is not None:
        all_results['Custom augment'] = augment_results

    print_comparison_table(all_results)

    emb_id = DEFAULT_EMBEDDING_MODEL_ID if use_embed else None
    best_name = save_all_models(
        combined_results,
        combined_vectorizer,
        MODELS_DIR,
        embedding_model_id=emb_id,
        use_tfidf_with_embeddings=use_embed,
    )
    save_metrics(all_results, MODELS_DIR)
    save_inference_config(MODELS_DIR)

    best_info = combined_results[best_name]
    print(f"\n  Best model (combined): {best_name}")
    print(f"    F1-Score : {best_info['f1_score']:.4f}")
    print(f"    Accuracy : {best_info['accuracy']:.4f}")
    print(f"\n  Classification Report:\n{best_info['report']}")

    if use_embed:
        print("\n  Models use semantic embeddings + engineered features (see models/embedding_config.json).")
    else:
        print("\n  Models use TF-IDF + engineered features (legacy mode).")

    print("\n  Training complete. Run the web app with:  python app.py\n")

if __name__ == '__main__':
    main()
