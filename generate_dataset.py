import random
import csv
import os

random.seed(42)

LEGIT_DOMAINS = [
    'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'company.com',
    'university.edu', 'workplace.org', 'techcorp.com', 'salesteam.com',
    'school.edu', 'hospital.org', 'bank.com', 'government.gov',
    'consulting.com', 'lawfirm.com', 'accounting.com', 'media.com',
]

SPAM_DOMAINS = [
    'free-prizes-now.xyz', 'totallylegit123.top', 'claim-reward.click',
    'discount-meds.info', 'win-big-today.bid', 'cashprize.tk',
    'urgent-alert.ml', 'verify-account.ga', 'lucky-winner.cf',
    'promo-deals99.xyz', 'security-update.top', 'offer-expire.click',
    'no-reply-bank.info', 'support-paypa1.com', 'amaz0n-verify.net',
    'free-gift-cards.biz', 'crypto-invest.xyz', 'insurance-deal.top',
]

LEGIT_FIRST_NAMES = [
    'john', 'sarah', 'michael', 'emma', 'david', 'maria', 'james', 'anna',
    'robert', 'jennifer', 'william', 'patricia', 'carlos', 'linda', 'ahmed',
    'yuki', 'chen', 'priya', 'alex', 'olivia', 'daniel', 'sophia', 'mark',
    'rachel', 'kevin', 'nicole', 'brian', 'karen', 'jason', 'melissa',
    'paul', 'ashley', 'steven', 'laura', 'andrew', 'diana', 'chris', 'grace',
]

LEGIT_LAST_NAMES = [
    'smith', 'johnson', 'williams', 'brown', 'jones', 'garcia', 'miller',
    'davis', 'martinez', 'wilson', 'anderson', 'taylor', 'thomas', 'lee',
    'chen', 'patel', 'kim', 'santos', 'lopez', 'clark', 'walker', 'hall',
]

SPAM_SENDERS = [
    'noreply', 'admin', 'support', 'info', 'promo', 'deals', 'winner',
    'notification', 'alert', 'security', 'update', 'prize', 'offer',
    'helpdesk', 'verify', 'customer-service', 'reward', 'lucky',
]

DEVICES = [
    'iPhone (iOS Mail)', 'Android (Gmail App)', 'Windows PC (Outlook)',
    'MacOS (Apple Mail)', 'Windows PC (Thunderbird)', 'Web (Gmail)',
    'Web (Yahoo Mail)', 'Web (Outlook.com)', 'iPad (iOS Mail)',
    'Android (Samsung Mail)', 'Linux (Thunderbird)', 'Windows PC (Gmail Web)',
    'MacOS (Gmail Web)', 'iPhone (Gmail App)', 'Android (Outlook App)',
    'Windows PC (Windows Mail)', 'Chromebook (Gmail Web)',
]

SPAM_DEVICES = [
    'Unknown', 'Bulk Mailer', 'Web (Unknown Client)', 'Automated System',
    'Unknown', 'Mass Mail Server', 'Web (Proxy)', 'Unknown',
    'Bot Sender', 'Unknown', 'Automated System', 'Unknown',
]

HAM_TEMPLATES = [
    "Hi {name}, just a reminder about our meeting tomorrow at {time}. Please bring the {doc} report. Thanks!",
    "Hey {name}, are you free for lunch today? I was thinking we could try that new {food} place on {street}.",
    "Dear {name}, please find attached the {doc} for your review. Let me know if you have any questions. Best regards.",
    "Hi team, the deadline for the {project} project has been moved to {date}. Please update your schedules accordingly.",
    "Good morning {name}, I wanted to follow up on our conversation about the {topic}. When would be a good time to discuss further?",
    "Hi {name}, thank you for your email. I will review the {doc} and get back to you by {day}. Regards.",
    "Dear {name}, your appointment has been confirmed for {date} at {time}. Please arrive 15 minutes early.",
    "{name}, can you send me the updated {doc} file? I need it for the presentation on {day}.",
    "Hi everyone, attached is the agenda for our weekly {topic} meeting. See you at {time}.",
    "Dear {name}, welcome to {company}! Your employee ID is ready. Please visit HR on your first day.",
    "Hi {name}, I hope you're doing well. I wanted to check in about the {project} project status.",
    "Hey {name}, happy birthday! Wishing you a great day. Let's catch up soon over {food}.",
    "Dear {name}, your order #{order_num} has been shipped and will arrive by {date}. Track it at our website.",
    "Hi {name}, the quarterly {doc} report is now available. Please review it before our meeting on {day}.",
    "Good afternoon {name}, I'm writing to confirm your reservation for {date} at {time}. See you then!",
    "Hi {name}, I noticed you were absent today. Hope everything is okay. Let me know if you need anything.",
    "Dear {name}, thank you for applying. We have received your application for the {position} position and will be in touch.",
    "Hi {name}, please remember to submit your {doc} by end of day {day}. Thank you.",
    "{name}, the new {topic} policy has been updated. Please review the attached document at your convenience.",
    "Hey {name}, do you want to carpool to the {event} on {day}? Let me know!",
    "Dear {name}, your subscription has been renewed. Your next billing date is {date}. Thank you for being a member.",
    "Hi {name}, I just finished reviewing the {doc}. Great work! A few minor suggestions are in the comments.",
    "Good morning team, please note that the office will be closed on {date} for {event}. Plan accordingly.",
    "Hi {name}, attached is the invoice for {month}. Payment is due by {date}. Let me know if you have questions.",
    "{name}, could you please forward the {doc} to the {topic} committee? They need it before {day}.",
    "Dear {name}, we are pleased to inform you that your {doc} has been approved. Congratulations!",
    "Hi {name}, the {topic} workshop has been rescheduled to {date}. Please update your calendar.",
    "Hey {name}, great presentation today! The team really liked your ideas about {topic}.",
    "Dear {name}, this is a reminder that your password will expire in 7 days. Please update it through the company portal.",
    "Hi {name}, I'll be out of office from {date} to {date2}. {name2} will handle any urgent matters.",
    "Dear Professor {name}, I have a question about the {topic} assignment due on {day}. Could I visit during office hours?",
    "Hi {name}, the results from the {topic} survey are in. I'll share the summary in tomorrow's meeting.",
    "Good evening {name}, just wanted to say thank you for helping with the {project} project. Really appreciate it.",
    "Dear {name}, your flight confirmation for {date} is attached. Check-in opens 24 hours before departure.",
    "{name}, the {topic} training session will be held on {day} at {time}. Registration is required.",
    "Hi {name}, we need to discuss the budget for Q{quarter}. Can we schedule a call this week?",
    "Dear {name}, your medical test results are ready. Please log in to the patient portal or call our office.",
    "Hi {name}, the team lunch is this {day} at {time}. We're going to {food} restaurant. Let me know if you can make it.",
    "Hey {name}, I found that article about {topic} you were looking for. I'll forward it to you.",
    "Dear {name}, your library books are due on {date}. Please return or renew them to avoid late fees.",
    "Hi {name}, I've updated the shared {doc} with the latest numbers. Please take a look when you get a chance.",
    "Dear parents, this is a reminder that parent-teacher conferences are scheduled for {date} from {time} to 5 PM.",
    "Hi {name}, the {topic} seminar was really informative. I took notes and can share them with you if interested.",
    "{name}, are we still on for the {event} this weekend? Let me know so I can make arrangements.",
    "Dear {name}, your package has been delivered to the front desk. Please pick it up at your convenience.",
    "Hi {name}, just checking if you received my previous email about the {topic}. Please let me know.",
    "Good morning {name}, I wanted to share some feedback on the {project}. Overall it looks great with a few tweaks needed.",
    "Dear {name}, enclosed is the contract for your review. Please sign and return by {date}.",
    "Hi {name}, the office printer on the 3rd floor is fixed now. Sorry for the inconvenience.",
    "Hey {name}, do you have the notes from yesterday's {topic} class? I missed it due to a doctor's appointment.",
]

SPAM_TEMPLATES = [
    "CONGRATULATIONS {name}! You have been selected as a WINNER of our ${amount} PRIZE! Click here NOW to claim: {url}",
    "URGENT: Your account has been compromised! Verify your identity immediately at {url} or your account will be suspended.",
    "You won't believe this! Make ${amount} per week working from home. No experience needed! Sign up: {url}",
    "FREE {product} for the first 100 people! Limited time offer. Act NOW before it expires! {url}",
    "Dear customer, your {bank} account needs immediate verification. Click here to confirm: {url} URGENT!",
    "EXCLUSIVE OFFER: Buy {product} at 90% OFF! Only {num} left in stock. Order NOW: {url}",
    "Hey {name}, I have ${amount} that I need to transfer. I will give you 30% if you help. Reply urgently.",
    "Your {device_name} has been infected with {num} viruses! Download our FREE antivirus NOW: {url}",
    "FINAL WARNING: Your subscription expires TODAY! Renew now to avoid losing access: {url}",
    "Congratulations! You've been pre-approved for a ${amount} loan with 0% interest! Apply now: {url}",
    "ATTENTION: You have an unclaimed inheritance of ${amount} from a distant relative. Contact us immediately.",
    "LIMITED TIME: Get FREE {product} samples! Just pay shipping of $4.99. Claim here: {url}",
    "Your {bank} account has suspicious activity. Verify your credentials NOW to prevent fraud: {url}",
    "WIN a brand new {product}! Enter our giveaway for FREE. Click to participate: {url}",
    "BREAKING: Secret method to lose {num} pounds in {num2} days! Doctors don't want you to know! {url}",
    "Dear valued customer, you are eligible for a CASH BACK reward of ${amount}. Claim before {date}: {url}",
    "ACT NOW! Free {product} worth ${amount}! No strings attached! Visit: {url}",
    "URGENT NOTICE: Your {bank} card ending in {card_digits} has been blocked. Unblock here: {url}",
    "Hello, I am a {title} from {country}. I have a business proposal worth ${amount}. Please reply for details.",
    "YOU WON'T BELIEVE THIS DEAL! {product} for only ${small_amount}! Regular price ${amount}! Order: {url}",
    "WARNING: {num} people in your area are viewing your profile! See who: {url}",
    "Get RICH quick! Invest ${small_amount} in crypto and earn ${amount} in {num} days! Start now: {url}",
    "FREE TRIAL: Premium {product} subscription. No credit card required! Sign up: {url}",
    "Your package is waiting! We tried to deliver but no one was home. Reschedule: {url}",
    "EXCLUSIVE: {celebrity} reveals secret to making ${amount}/month! Learn how: {url}",
    "Hi {name}, please verify your email address to claim your ${amount} gift card: {url}",
    "DISCOUNT ALERT: {num}% off all {product}! Today only! Use code FREE{num2}: {url}",
    "Dear {name}, you have {num} unread messages from attractive singles in your area! View now: {url}",
    "IMPORTANT: Your {bank} account statement is ready. Download it here: {url} (contains malware attachment)",
    "Make money online! Earn ${amount} daily with our proven system. No skills needed! Join: {url}",
    "FLASH SALE: Buy 1 Get 3 FREE on all {product}! Hurry, offer ends in {num} hours: {url}",
    "ALERT: Someone tried to log into your account from {country}. Secure your account: {url}",
    "Free {product} giveaway! We're giving away {num} units to celebrate our anniversary! Enter: {url}",
    "YOU HAVE BEEN SELECTED for a special government grant of ${amount}. Apply now: {url}",
    "Dear friend, I am writing to you because I need your urgent assistance to transfer ${amount} from {country}.",
    "LAST CHANCE! Your reward of ${amount} expires in 24 hours! Claim it now: {url}",
    "Shocking: {celebrity} uses this one trick to stay young! Try it FREE: {url}",
    "CONGRATULATIONS! Your email was selected in our online lottery! Prize: ${amount}. Claim: {url}",
    "Hi, we noticed your {bank} payment failed. Update your billing info immediately: {url}",
    "FREE MONEY! Get ${amount} deposited into your account today! No payback required! Apply: {url}",
    "URGENT: IRS notice - you owe ${amount} in back taxes. Pay immediately to avoid arrest: {url}",
    "Amazing investment opportunity! Double your money in {num} days guaranteed! Start: {url}",
    "Your computer is running slow! Speed it up 500% with our FREE software: {url}",
    "Dear {name}, you have won a {product} in our promotional draw! Confirm your shipping address: {url}",
    "BREAKING NEWS: Earn ${amount} per hour from your phone! Thousands already joined: {url}",
]

NAMES = ['John', 'Sarah', 'Mike', 'Emma', 'David', 'Lisa', 'Chris', 'Anna',
         'Tom', 'Rachel', 'Kevin', 'Diana', 'Mark', 'Sophie', 'James', 'Maria']
TIMES = ['9:00 AM', '10:00 AM', '10:30 AM', '11:00 AM', '1:00 PM', '2:00 PM',
         '2:30 PM', '3:00 PM', '4:00 PM', '4:30 PM']
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
DATES = ['March 5', 'March 10', 'March 15', 'March 20', 'April 1', 'April 8',
         'April 15', 'April 22', 'May 1', 'May 10']
DOCS = ['quarterly sales', 'budget', 'project proposal', 'performance review',
        'marketing plan', 'financial', 'research', 'progress', 'annual',
        'compliance', 'inventory', 'status update', 'expense']
FOODS = ['Italian', 'Japanese', 'Mexican', 'Thai', 'Chinese', 'Indian', 'Korean',
         'Mediterranean', 'Vietnamese', 'burger']
STREETS = ['Main Street', '5th Avenue', 'Oak Drive', 'Pine Road', 'Market Street']
PROJECTS = ['Alpha', 'Beta', 'Phoenix', 'Horizon', 'Summit', 'Eclipse', 'Atlas']
TOPICS = ['data analytics', 'machine learning', 'cybersecurity', 'marketing strategy',
          'product development', 'customer feedback', 'supply chain', 'HR policy',
          'sustainability', 'cloud migration', 'budget planning', 'quality assurance']
COMPANIES = ['TechCorp', 'GlobalSoft', 'InnovateCo', 'DigitalEdge', 'CloudSync']
EVENTS = ['conference', 'workshop', 'team building', 'seminar', 'training session']
POSITIONS = ['Software Engineer', 'Data Analyst', 'Marketing Manager', 'Project Lead',
             'Research Assistant', 'IT Support', 'Business Analyst']
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June']
PRODUCTS = ['iPhone 16', 'Samsung Galaxy', 'Nike shoes', 'Ray-Ban sunglasses',
            'iPad Pro', 'MacBook', 'AirPods', 'Rolex watch', 'luxury handbag',
            'designer wallet', 'smart TV', 'gaming laptop', 'fitness tracker']
BANKS = ['PayPal', 'Chase Bank', 'Bank of America', 'Wells Fargo', 'Citibank',
         'HSBC', 'Capital One', 'American Express']
AMOUNTS = ['1,000,000', '500,000', '250,000', '100,000', '50,000', '10,000',
           '5,000', '2,500', '75,000', '150,000']
SMALL_AMOUNTS = ['9.99', '19.99', '29.99', '49.99', '99', '199', '4.99']
URLS = ['http://claim-prize-now.xyz/win', 'http://verify-account.top/login',
        'http://free-offer.click/get', 'http://urgent-update.info/act',
        'http://exclusive-deal.bid/buy', 'http://winner-selected.tk/claim',
        'http://secure-bank.ml/verify', 'http://promo-special.ga/offer',
        'http://limited-time.cf/deal', 'http://act-now-win.xyz/prize',
        'https://bit.ly/3xFAKE1', 'https://t.co/fakelink99']
COUNTRIES = ['Nigeria', 'Ghana', 'South Africa', 'United Kingdom', 'Russia',
             'China', 'India', 'Brazil']
CELEBRITIES = ['Elon Musk', 'Jeff Bezos', 'Oprah', 'Dr. Oz', 'Kim Kardashian']
TITLES = ['Prince', 'Barrister', 'Minister', 'General', 'Ambassador']
DEVICE_NAMES = ['iPhone', 'MacBook', 'Windows PC', 'Android phone', 'laptop']
CARD_DIGITS = ['4521', '8832', '1199', '3347', '6678', '9901', '2244']
QUARTERS = ['1', '2', '3', '4']

def fill_ham(template):
    return template.format(
        name=random.choice(NAMES),
        name2=random.choice(NAMES),
        time=random.choice(TIMES),
        day=random.choice(DAYS),
        date=random.choice(DATES),
        date2=random.choice(DATES),
        doc=random.choice(DOCS),
        food=random.choice(FOODS),
        street=random.choice(STREETS),
        project=random.choice(PROJECTS),
        topic=random.choice(TOPICS),
        company=random.choice(COMPANIES),
        event=random.choice(EVENTS),
        position=random.choice(POSITIONS),
        month=random.choice(MONTHS),
        order_num=random.randint(100000, 999999),
        quarter=random.choice(QUARTERS),
    )

def fill_spam(template):
    return template.format(
        name=random.choice(NAMES),
        amount=random.choice(AMOUNTS),
        small_amount=random.choice(SMALL_AMOUNTS),
        url=random.choice(URLS),
        product=random.choice(PRODUCTS),
        bank=random.choice(BANKS),
        num=random.randint(2, 50),
        num2=random.randint(5, 30),
        date=random.choice(DATES),
        country=random.choice(COUNTRIES),
        celebrity=random.choice(CELEBRITIES),
        title=random.choice(TITLES),
        device_name=random.choice(DEVICE_NAMES),
        card_digits=random.choice(CARD_DIGITS),
    )

def make_legit_sender():
    first = random.choice(LEGIT_FIRST_NAMES)
    last = random.choice(LEGIT_LAST_NAMES)
    domain = random.choice(LEGIT_DOMAINS)
    patterns = [
        f"{first}.{last}@{domain}",
        f"{first}{last[0]}@{domain}",
        f"{first}_{last}@{domain}",
        f"{first[0]}{last}@{domain}",
    ]
    return random.choice(patterns)

def make_spam_sender():
    name = random.choice(SPAM_SENDERS)
    domain = random.choice(SPAM_DOMAINS)
    patterns = [
        f"{name}@{domain}",
        f"{name}{random.randint(1,999)}@{domain}",
        f"{name}-{random.choice(['team','service','dept'])}@{domain}",
    ]
    return random.choice(patterns)

def generate_dataset(total=500, spam_ratio=0.35):

    num_spam = int(total * spam_ratio)
    num_ham = total - num_spam
    rows = []

    for _ in range(num_ham):
        template = random.choice(HAM_TEMPLATES)
        text = fill_ham(template)
        sender = make_legit_sender()
        device = random.choice(DEVICES)
        rows.append({'text': text, 'label': 0, 'sender': sender, 'device': device})

    for _ in range(num_spam):
        template = random.choice(SPAM_TEMPLATES)
        text = fill_spam(template)
        sender = make_spam_sender()
        device = random.choice(SPAM_DEVICES + DEVICES[:4])
        rows.append({'text': text, 'label': 1, 'sender': sender, 'device': device})

    random.shuffle(rows)
    return rows

def main():

    dest = os.path.join('datasets', 'generated_sample_emails.csv')
    rows = generate_dataset(total=500, spam_ratio=0.35)

    with open(dest, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['text', 'label', 'sender', 'device'])
        writer.writeheader()
        writer.writerows(rows)

    spam_count = sum(1 for r in rows if r['label'] == 1)
    ham_count = len(rows) - spam_count
    print(f"\n  Dataset generated: {dest}")
    print(f"    Total  : {len(rows)}")
    print(f"    Spam   : {spam_count}")
    print(f"    Ham    : {ham_count}")
    print(f"    Columns: text, label, sender, device\n")

if __name__ == '__main__':
    main()
