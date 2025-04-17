import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Constants
NUM_ROWS = 10000
INDIAN_CITIES = ['Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur']
TRANSACTION_TYPES = ['send', 'receive', 'bill_payment', 'self_transfer', 'merchant_payment']

def generate_transaction_data(n=NUM_ROWS):
    data = []
    for i in range(n):
        transaction_id = f"TXN{100000+i}"
        user_id = f"USER{random.randint(1000, 9999)}"
        amount = round(random.uniform(10, 200000), 2)
        
        # Random timestamp in the last 90 days
        timestamp = datetime.now() - timedelta(days=random.randint(0, 90),
                                               hours=random.randint(0, 23),
                                               minutes=random.randint(0, 59))
        
        location = random.choice(INDIAN_CITIES)
        transaction_type = random.choice(TRANSACTION_TYPES)
        device_id = f"DEV{random.randint(100, 999)}"
        
        # Fraud heuristic
        hour = timestamp.hour
        is_fraud = 0
        if (amount > 100000 and hour in [1,2,3]) or (random.random() < 0.01):
            is_fraud = 1
        
        data.append([
            transaction_id, user_id, amount, timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            location, transaction_type, device_id, is_fraud
        ])
        
    df = pd.DataFrame(data, columns=[
        'transaction_id', 'user_id', 'amount', 'timestamp',
        'location', 'transaction_type', 'device_id', 'is_fraud'
    ])
    
    return df

# Generate and save
df = generate_transaction_data()
df.to_csv("synthetic_upi_transactions.csv", index=False)
print("Synthetic UPI dataset generated and saved.")
