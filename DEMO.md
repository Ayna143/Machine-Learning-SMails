# Demo Script (for presentation)

## 1) Start the app

```bash
python app.py
```

Open: `http://127.0.0.1:5000`

## 2) Single Check (Email/Text)

- Go to **Home → Check Email**
- Paste a clear spam example:

```
CONGRATULATIONS! You won a prize! Click now: http://win-prize.xyz/claim
```

- Click **Check for Spam**
- Mention in your talk:
  - The app returns **prediction + confidence**
  - It also shows **feature-based reasons** (URLs, suspicious keywords, etc.)
  - “Recent History” is stored locally (no accounts)

## 3) Image Scan (OCR)

- Go to **Image Scan**
- Upload a screenshot of a spam message or email
- Click **Scan Image**
- Mention:
  - OCR extracts text first, then runs the same spam classifier

## 4) Import Dataset (Batch)

- Go to **Import Dataset**
- Upload a CSV with a `text` column (optional `label`)
- Mention:
  - If labels are present (0/1), the app computes **accuracy**
  - It displays a preview table of predictions

## 5) About (Model Comparison)

- Scroll to **About**
- Show:
  - dataset tabs
  - metrics chart
  - table (accuracy/precision/recall/f1)
  - confusion matrices

## Quick talking points
- Datasets: **SMS Spam**, **Enron Email**, and a **custom dataset**
- Models: Random Forest / Naive Bayes / XGBoost
- Best model chosen by **F1-score**
- No user accounts needed for classroom presentation scope

