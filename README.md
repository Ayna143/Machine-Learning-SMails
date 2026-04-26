# SpamSense — Spam & Ham Detector (Student Project)

SpamSense is a Flask web app that detects **spam vs ham** using Machine Learning (TF‑IDF + engineered features) with 3 models:
- Random Forest
- Naive Bayes
- XGBoost

It supports:
- **Single check** (paste email/text)
- **Image scan** (OCR then classify)
- **Batch import** (CSV/TXT/TSV)
- **About → Model comparison** (metrics + confusion matrices)

## Requirements
- Python 3.9+ (Anaconda is OK)
- (Optional) Tesseract OCR installed and on PATH (for better OCR)

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the web app

```bash
python app.py
```

Open:
- `http://127.0.0.1:5000`

## Train / re-train models (optional)

If `models/` already contains `.pkl` files, you can skip training.

```bash
python train_and_evaluate.py
```

This script:
- loads datasets in `datasets/`
- trains and compares models
- writes `models/metrics.json` (used by the About page)
- saves models in `models/` (including `best_model.pkl`)

## Project structure (high-level)
- `app.py`: Flask backend (API + page)
- `templates/index.html`: UI
- `static/css/style.css`: UI styling
- `static/js/main.js`: UI logic (tabs, requests, charts, history)
- `src/`: preprocessing, feature engineering, training, prediction
- `datasets/`: training datasets (SMS, Enron, custom)
- `models/`: trained models + metrics

## Demo
See `DEMO.md`.

