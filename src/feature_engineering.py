import re
import numpy as np

SUSPICIOUS_KEYWORDS = [
    'free', 'win', 'winner', 'won', 'urgent', 'act now', 'click here',
    'congratulations', 'prize', 'offer', 'limited', 'deal', 'cash',
    'money', 'credit', 'discount', 'guarantee', 'claim', 'subscribe',
    'unsubscribe', 'verify', 'account', 'bank', 'lottery', 'inheritance',
    'nigerian', 'prince', 'viagra', 'pharmacy', 'order now', 'buy now',
    'risk free', 'no obligation', 'act immediately', 'expire', 'exclusive'
]

SUSPICIOUS_TLDS = ['.xyz', '.top', '.click', '.info', '.bid', '.tk', '.ml', '.ga', '.cf']

# Core text features
TEXT_FEATURE_NAMES = [
    'suspicious_keyword_count',
    'url_count',
    'special_char_count',
    'uppercase_ratio',
    'email_length',
    'has_html',
    'has_suspicious_domain',
    'exclamation_count',
    'dollar_sign_count',
    'digit_ratio',
]

# Sender-derived features
SENDER_FEATURE_NAMES = [
    'sender_domain_suspicious',
    'sender_has_numbers',
    'sender_domain_length',
]

# Device-derived features
DEVICE_FEATURE_NAMES = [
    'device_is_unknown',
    'device_is_mobile',
    'device_is_automated',
]

FEATURE_NAMES = TEXT_FEATURE_NAMES + SENDER_FEATURE_NAMES + DEVICE_FEATURE_NAMES


def extract_text_features(text):
    """Extract content-based, structural, and domain-based features from email text."""
    if not isinstance(text, str):
        text = ""

    text_lower = text.lower()
    total_chars = max(len(text), 1)

    features = {}

    features['suspicious_keyword_count'] = sum(
        1 for kw in SUSPICIOUS_KEYWORDS if kw in text_lower
    )
    features['url_count'] = len(re.findall(r'https?://\S+|www\.\S+', text))
    features['special_char_count'] = len(re.findall(r'[!$%&*#@^~]', text))
    features['uppercase_ratio'] = sum(1 for c in text if c.isupper()) / total_chars

    features['email_length'] = len(text.split())
    features['has_html'] = 1 if re.search(r'<[^>]+>', text) else 0

    domains = re.findall(r'@([\w.-]+)', text)
    has_suspicious = 0
    for domain in domains:
        if any(tld in domain.lower() for tld in SUSPICIOUS_TLDS):
            has_suspicious = 1
            break
        if re.search(r'\d', domain.split('.')[0]):
            has_suspicious = 1
            break
    features['has_suspicious_domain'] = has_suspicious

    features['exclamation_count'] = text.count('!')
    features['dollar_sign_count'] = text.count('$')
    features['digit_ratio'] = sum(1 for c in text if c.isdigit()) / total_chars

    return features


def extract_sender_features(sender):
    """Extract features from the sender email address."""
    features = {
        'sender_domain_suspicious': 0,
        'sender_has_numbers': 0,
        'sender_domain_length': 0,
    }

    if not isinstance(sender, str) or '@' not in sender:
        return features

    parts = sender.strip().lower().split('@')
    local_part = parts[0]
    domain = parts[1] if len(parts) > 1 else ''

    if any(tld in domain for tld in SUSPICIOUS_TLDS):
        features['sender_domain_suspicious'] = 1

    lookalike = ['paypa1', 'amaz0n', 'g00gle', 'app1e', 'micros0ft']
    if any(fake in domain for fake in lookalike):
        features['sender_domain_suspicious'] = 1

    if re.search(r'\d', local_part):
        features['sender_has_numbers'] = 1

    features['sender_domain_length'] = min(len(domain), 50)

    return features


def extract_device_features(device):
    """Extract features from the device / email client string."""
    features = {
        'device_is_unknown': 0,
        'device_is_mobile': 0,
        'device_is_automated': 0,
    }

    if not isinstance(device, str) or not device.strip():
        features['device_is_unknown'] = 1
        return features

    dev = device.strip().lower()

    if dev in ('unknown', '', 'n/a', 'none'):
        features['device_is_unknown'] = 1

    mobile_keywords = ['iphone', 'android', 'ipad', 'mobile', 'samsung']
    if any(kw in dev for kw in mobile_keywords):
        features['device_is_mobile'] = 1

    auto_keywords = ['bot', 'bulk', 'automated', 'mass mail', 'proxy', 'server']
    if any(kw in dev for kw in auto_keywords):
        features['device_is_automated'] = 1

    return features


def extract_features(text, sender='', device=''):
    """Extract all features: text + sender + device."""
    feats = {}
    feats.update(extract_text_features(text))
    feats.update(extract_sender_features(sender))
    feats.update(extract_device_features(device))
    return feats


def extract_features_batch(texts, senders=None, devices=None):
    """Extract features for a list of texts. Returns a 2D numpy array."""
    n = len(texts)
    if senders is None:
        senders = [''] * n
    if devices is None:
        devices = [''] * n

    all_features = []
    for i in range(n):
        feat = extract_features(texts[i], senders[i], devices[i])
        all_features.append([feat[name] for name in FEATURE_NAMES])
    return np.array(all_features, dtype=np.float64)
