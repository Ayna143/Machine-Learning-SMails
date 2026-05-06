import os
import io
import zipfile
import tarfile
import requests
import pandas as pd

DATASETS_DIR = os.path.join(os.path.dirname(__file__), 'datasets')

def download_sms_spam():

    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00228/smsspamcollection.zip"
    dest = os.path.join(DATASETS_DIR, 'sms_spam.csv')

    if os.path.exists(dest):
        print(f"  [SMS Spam] Already exists at {dest}")
        return dest

    print("  [SMS Spam] Downloading from UCI...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        with zf.open('SMSSpamCollection') as f:
            df = pd.read_csv(
                f, sep='\t', header=None,
                names=['label', 'text'], encoding='latin-1'
            )

    df['label'] = df['label'].map({'ham': 0, 'spam': 1})
    df.to_csv(dest, index=False)
    print(f"  [SMS Spam] Saved {len(df)} records to {dest}")
    return dest

def download_enron_spam():
    dest = os.path.join(DATASETS_DIR, 'enron_spam.csv')

    if os.path.exists(dest):
        print(f"  [Enron]    Already exists at {dest}")
        return dest

    sources = [
        (
            "bdanalytics GitHub",
            "https://github.com/bdanalytics/Enron-Spam/raw/refs/heads/master/data/emails.csv",
        ),
        (
            "MWiechmann GitHub (zip)",
            "https://github.com/MWiechmann/enron_spam_data/raw/master/enron_spam_data.zip",
        ),
    ]

    df = None
    for label, url in sources:
        try:
            print(f"  [Enron]    Trying {label}...")
            if url.endswith('.zip'):
                resp = requests.get(url, timeout=120)
                resp.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                    csv_name = [n for n in zf.namelist() if n.endswith('.csv')][0]
                    with zf.open(csv_name) as f:
                        df = pd.read_csv(f, encoding='latin-1')
            else:
                resp = requests.get(url, timeout=120)
                resp.raise_for_status()
                df = pd.read_csv(io.StringIO(resp.text), encoding='latin-1')
            print(f"  [Enron]    Success from {label}")
            break
        except Exception as e:
            print(f"  [Enron]    {label} failed: {e}")
            continue

    if df is None:
        raise RuntimeError("Could not download Enron dataset from any source.")

    if 'Spam/Ham' in df.columns:
        df = df.rename(columns={'Spam/Ham': 'label', 'Subject': 'subject', 'Message': 'text'})
    elif 'spam' in [c.lower() for c in df.columns]:
        label_col = [c for c in df.columns if c.lower() == 'spam'][0]
        text_col = [c for c in df.columns if 'message' in c.lower() or 'text' in c.lower()][0]
        df = df.rename(columns={label_col: 'label', text_col: 'text'})

    if df['label'].dtype == object:
        df['label'] = df['label'].str.strip().str.lower().map({'ham': 0, 'spam': 1})

    if 'subject' in df.columns and 'text' in df.columns:
        df['text'] = df['subject'].fillna('') + ' ' + df['text'].fillna('')
    elif 'text' not in df.columns:
        text_candidates = [c for c in df.columns if c.lower() not in ('label', 'spam')]
        df['text'] = df[text_candidates[0]].fillna('')

    df = df[['label', 'text']].dropna(subset=['label'])
    df['label'] = df['label'].astype(int)
    df.to_csv(dest, index=False)
    print(f"  [Enron]    Saved {len(df)} records to {dest}")
    return dest

def download_spamassassin_public():
    dest = os.path.join(DATASETS_DIR, 'spamassassin_public.csv')

    if os.path.exists(dest):
        print(f"  [SpamAssassin] Already exists at {dest}")
        return dest

    archives = [
        (
            0,
            "easy_ham (20021010)",
            "https://spamassassin.apache.org/old/publiccorpus/20021010_easy_ham.tar.bz2",
        ),
        (
            1,
            "spam (20021010)",
            "https://spamassassin.apache.org/old/publiccorpus/20021010_spam.tar.bz2",
        ),
    ]

    rows = []
    print("\n  [SpamAssassin] Downloading public corpus (Apache)...")
    for label, name, url in archives:
        print(f"  [SpamAssassin]   Fetching {name}...")
        resp = requests.get(url, timeout=240)
        resp.raise_for_status()
        with tarfile.open(fileobj=io.BytesIO(resp.content), mode='r:bz2') as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                try:
                    f = tar.extractfile(member)
                except Exception:
                    continue
                if f is None:
                    continue
                raw = f.read()
                try:
                    text = raw.decode('utf-8', errors='replace')
                except Exception:
                    continue
                text = text.strip()
                if len(text) < 30:
                    continue
                rows.append({'text': text, 'label': label})

    if len(rows) < 100:
        raise RuntimeError("SpamAssassin download produced too few rows; check network/archives.")

    df = pd.DataFrame(rows)
    df.to_csv(dest, index=False)
    print(f"  [SpamAssassin] Saved {len(df)} records (spam={(df['label'] == 1).sum()}, ham={(df['label'] == 0).sum()}) to {dest}")
    return dest

def main():
    os.makedirs(DATASETS_DIR, exist_ok=True)
    print("\n  Downloading datasets...\n")
    sms_path = download_sms_spam()
    enron_path = download_enron_spam()
    spam_path = download_spamassassin_public()
    print("\n  All datasets ready.\n")
    return sms_path, enron_path, spam_path

if __name__ == '__main__':
    main()
