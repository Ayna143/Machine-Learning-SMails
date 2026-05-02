# SpamSense — Spam & Ham Detector (Student Project)

SpamSense is a Flask web app that detects **spam vs ham** using a context-aware hybrid pipeline:
- **ML layer**: TF-IDF + sentence embeddings (`all-MiniLM-L6-v2`) + engineered features
- **LLM context layer**: Gemini (`gemini-1.5-flash`) for intent/deception analysis
- **Sender risk layer**: sender-domain and intent mismatch heuristics
- **Final weighted fusion**: ML 40% + Gemini 50% + Sender 10%

Core ML models:
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

### Optional: Gemini context layer setup (`.env`)

Create a `.env` file in project root:

```bash
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TIMEOUT_SECONDS=20
```

If `GEMINI_API_KEY` is missing or Gemini fails, SpamSense **fails open**:
it still returns a final verdict using ML + sender risk and adds a fallback note.

### Get a free Gemini API key (Google AI Studio)

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with Google.
3. Open **Get API key** / **API keys**.
4. Click **Create API key** (or create in an existing GCP project).
5. Copy the key and place it in `.env` as `GEMINI_API_KEY=...`.
6. Restart the app after updating `.env`.

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
- trains and compares models on hybrid features
- writes `models/metrics.json` (used by the About page)
- saves models in `models/` (including `best_model.pkl`)
- writes:
  - `models/embedding_config.json`
  - `models/inference_config.json` (spam threshold + training knobs)

## Project structure (high-level)
- `app.py`: Flask backend (API + page)
- `templates/index.html`: UI
- `static/css/style.css`: UI styling
- `static/js/main.js`: UI logic (tabs, requests, charts, history)
- `src/`: preprocessing, feature engineering, training, prediction
- `src/context_llm.py`: Gemini context analysis (strict JSON parsing, fail-open)
- `src/sender_analysis.py`: sender risk scoring
- `datasets/`: training datasets (SMS, Enron, custom)
- `models/`: trained models + metrics

## Demo
See `DEMO.md`.

