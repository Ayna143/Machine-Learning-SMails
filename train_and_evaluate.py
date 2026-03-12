"""
Main training script — orchestrates the full ML pipeline:
  1. Load datasets  (SMS Spam, Enron, Custom Full)
  2. Preprocess text
  3. Extract features  (text + sender + device)
  4. Train & compare   Random Forest, Naive Bayes, XGBoost
  5. Save ALL models + metrics
"""

import os
import pandas as pd
import numpy as np

from src.preprocessing import clean_text, build_tfidf_vectorizer
from src.feature_engineering import extract_features_batch
from src.model_trainer import (
    train_and_compare, select_best_model,
    save_all_models, save_metrics, print_comparison_table
)

DATASETS_DIR = 'datasets'
MODELS_DIR = 'models'


def load_dataset(path, name):
    """Load a CSV dataset. Required column: text, label. Optional: sender, device."""
    print(f"\n  Loading {name} from {path}...")
    df = pd.read_csv(path, encoding='utf-8', on_bad_lines='skip')
    df = df.dropna(subset=['text', 'label'])
    df['label'] = df['label'].astype(int)

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


def run_pipeline(df, dataset_name, vectorizer=None):
    """
    Full pipeline: preprocess → feature engineering → train & compare.
    Returns results dict and fitted vectorizer.
    """
    print(f"\n  Preprocessing {dataset_name}...")
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

    results = train_and_compare(X_tfidf, X_engineered, y, dataset_name)
    return results, vectorizer


def main():
    sms_path = os.path.join(DATASETS_DIR, 'sms_spam.csv')
    enron_path = os.path.join(DATASETS_DIR, 'enron_spam.csv')
    full_path = os.path.join(DATASETS_DIR, 'email_spam_full.csv')

    if not os.path.exists(sms_path) or not os.path.exists(enron_path):
        print("  Datasets not found. Running download script...")
        from download_datasets import main as download
        download()

    if not os.path.exists(full_path):
        print("  Full dataset not found. Running generator...")
        from generate_dataset import main as generate
        generate()

    # --- Load all datasets ---
    sms_df = load_dataset(sms_path, "SMS Spam Collection")
    enron_df = load_dataset(enron_path, "Enron Email Dataset")
    full_df = load_dataset(full_path, "Custom Email Dataset")

    # --- Run pipeline on each dataset independently ---
    sms_results, _ = run_pipeline(sms_df, "SMS Spam Collection")
    enron_results, _ = run_pipeline(enron_df, "Enron Email Dataset")

    # --- Combined dataset for the final production model ---
    print("\n  Combining all datasets for final training...")
    combined_df = pd.concat([sms_df, enron_df, full_df], ignore_index=True)
    combined_df = combined_df.sample(frac=1, random_state=42).reset_index(drop=True)
    combined_results, combined_vectorizer = run_pipeline(
        combined_df, "Combined (All Datasets)"
    )

    # --- Print comparison table ---
    all_results = {
        'SMS Spam': sms_results,
        'Enron Email': enron_results,
        'Combined': combined_results,
    }
    print_comparison_table(all_results)

    # --- Save ALL models + metrics ---
    best_name = save_all_models(
        combined_results, combined_vectorizer, MODELS_DIR
    )
    save_metrics(all_results, MODELS_DIR)

    best_info = combined_results[best_name]
    print(f"\n  Best model (combined): {best_name}")
    print(f"    F1-Score : {best_info['f1_score']:.4f}")
    print(f"    Accuracy : {best_info['accuracy']:.4f}")
    print(f"\n  Classification Report:\n{best_info['report']}")

    print("\n  Training complete. Run the web app with:  python app.py\n")


if __name__ == '__main__':
    main()
