import requests
import json

BASE = 'http://127.0.0.1:5000'

print('=== Test 1: Spam detection (Random Forest) ===')
r = requests.post(f'{BASE}/predict', json={
    'email_text': 'CONGRATULATIONS! You won a FREE prize! Click NOW: http://win-prize.xyz/claim',
    'sender': 'noreply@free-prizes-now.xyz',
    'device': 'Bot Sender',
    'model_name': 'Random Forest'
})
d = r.json()
print(f"  Prediction: {d['prediction']}  Confidence: {d['confidence']:.2f}  Model: {d['model_used']}")
print(f"  Reasons: {d['reasons'][:3]}")

print('\n=== Test 2: Ham detection (XGBoost) ===')
r = requests.post(f'{BASE}/predict', json={
    'email_text': 'Hi Sarah, reminder about our team meeting tomorrow at 10 AM. Bring the project report.',
    'sender': 'john.smith@company.com',
    'device': 'Windows PC (Outlook)',
    'model_name': 'XGBoost'
})
d = r.json()
print(f"  Prediction: {d['prediction']}  Confidence: {d['confidence']:.2f}  Model: {d['model_used']}")

print('\n=== Test 3: Naive Bayes ===')
r = requests.post(f'{BASE}/predict', json={
    'email_text': 'URGENT: Your account has been compromised! Click here to verify: http://fake-bank.xyz',
    'model_name': 'Naive Bayes'
})
d = r.json()
print(f"  Prediction: {d['prediction']}  Confidence: {d['confidence']:.2f}  Model: {d['model_used']}")

print('\n=== Test 4: Model comparison ===')
r = requests.get(f'{BASE}/comparison')
metrics = r.json()
for ds in metrics:
    print(f"  {ds}:")
    for model in metrics[ds]:
        m = metrics[ds][model]
        print(f"    {model}: Acc={m['accuracy']:.4f} F1={m['f1_score']:.4f}")

print('\n=== Test 5: Available models ===')
r = requests.get(f'{BASE}/models_list')
print(f"  {r.json()}")

print('\nAll tests passed!')
