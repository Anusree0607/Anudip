from flask import Flask, request, render_template, jsonify, redirect, url_for, session, flash
import pandas as pd
import pickle
import os
import sqlite3
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# === Load the best trained model pipeline ===
model_path = r'C:\Users\DELL\OneDrive\Desktop\SECURE_UPI\models\best_model.pkl'
with open(model_path, 'rb') as file:
    model = pickle.load(file)

# === User login DB function ===
def get_user(username):
    db_path = r'C:\Users\DELL\OneDrive\Desktop\SECURE_UPI\users.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user

# === Preprocessing for uploaded or form data ===
def preprocess_for_prediction(df):
    location_map = {'Delhi': 0, 'Mumbai': 1, 'Chennai': 2, 'Bangalore': 3, 'Kolkata': 4}
    type_map = {'payment': 0, 'withdrawal': 1, 'transfer': 2}

    df['location'] = df['location'].str.lower().str.capitalize().map(location_map).fillna(-1)
    df['transaction_type'] = df['transaction_type'].str.lower().map(type_map).fillna(-1)

    # Handle device_id (convert to numeric if necessary)
    df['device_id'] = pd.to_numeric(df['device_id'], errors='coerce').fillna(-1).astype(int)

    # Extract features from timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['hour'] = df['timestamp'].dt.hour.fillna(0).astype(int)
    df['day_of_week'] = df['timestamp'].dt.dayofweek.fillna(-1).astype(int)
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

    selected_features = ['amount', 'location', 'transaction_type', 'device_id', 'hour', 'day_of_week', 'is_weekend']
    return df[selected_features]

# === Login Route ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form.get('username')
        passwd = request.form.get('password')
        user = get_user(uname)
        if user and user[2] == passwd:
            session['username'] = uname
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('index.html')

# === Logout Route ===
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out!', 'info')
    return redirect(url_for('login'))

# === Home Page ===
@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html')
    return redirect(url_for('login'))

# === CSV Upload + Batch Prediction ===
@app.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    try:
        df = pd.read_csv(file)
        
        # Define alias map for flexible column detection
        
        column_aliases = {
    'transaction_id': ['txn_id', 'transaction_id', 'transaction_reference'],
    'amount': ['amount', 'txn_amount', 'transaction_amount', 'amt', 'txn_amt'],
    'location': ['location', 'place', 'city', 'geo_location', 'merchant_location'],
    'transaction_type': ['transaction_type', 'txn_type', 'payment_type', 'type'],
    'device_id': ['device_id', 'device', 'device_id', 'device_identifier'],
    'timestamp': ['timestamp', 'time', 'datetime', 'timestamp_of_transaction'],
    'user_id': ['user_id', 'user_identifier', 'uid', 'user'],
    'merchant_id': ['merchant_id', 'merchant', 'merchant_identifier', 'merchant_code'],
    'payment_method': ['payment_method', 'method', 'payment_mode', 'payment_type'],
    'status': ['status', 'txn_status', 'payment_status', 'transaction_status'],
    'bank_name': ['bank_name', 'bank', 'bank_code', 'payment_bank'],
    'mobile_number': ['mobile_number', 'mobile', 'phone', 'user_mobile'],
    'merchant_name': ['merchant_name', 'merchant_business_name', 'store_name'],
    'transaction_fee': ['txn_fee', 'transaction_fee', 'service_fee', 'charge']
}

        # Rename columns based on alias match
        col_renamed = {}
        for standard_col, aliases in column_aliases.items():
            for alias in aliases:
                if alias in df.columns:
                    col_renamed[alias] = standard_col
                    break

        df = df.rename(columns=col_renamed)

        # Fill any missing expected columns with safe defaults
        defaults = {
            'amount': 0,
            'location': 'Unknown',
            'transaction_type': 'unknown',
            'device_id': -1,
            'timestamp': pd.Timestamp.now()
        }

        for col, default_val in defaults.items():
            if col not in df.columns:
                df[col] = default_val

        # Preprocess and predict
        X = preprocess_for_prediction(df)
        predictions = model.predict(X)
        fraud_count = int((predictions == 1).sum())

        return jsonify({'fraud_count': fraud_count, 'total': len(predictions)})

    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500


# === Single Transaction Prediction ===
@app.route('/predict', methods=['POST'])
def predict_transaction():
    try:
        data = request.get_json()

        # Extract and convert inputs
        amount = float(data.get('amount', 0))
        hour = int(data.get('hour', 0))
        device_id = int(data.get('device_id', 0))

        # Mappings
        location_map = {'Delhi': 0, 'Mumbai': 1, 'Chennai': 2, 'Bangalore': 3, 'Kolkata': 4, 'Pune': 5}
        type_map = {'payment': 0, 'withdrawal': 1, 'transfer': 2}

        location = location_map.get(data.get('location', '').capitalize(), -1)
        transaction_type = type_map.get(data.get('transaction_type', '').lower(), -1)

        # Compute derived features
        from datetime import datetime
        now = datetime.now()
        day_of_week = now.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0

        # Set correct feature names in order
        features = pd.DataFrame([{
            'amount': amount,
            'location': location,
            'transaction_type': transaction_type,
            'device_id': device_id,
            'hour': hour,
            'day_of_week': day_of_week,
            'is_weekend': is_weekend
        }])

        prediction = model.predict(features)[0]
        result = 'Fraud' if prediction == 1 else 'Legit'
        return jsonify({'prediction': result})

    except Exception as e:
        return jsonify({'prediction': f'Error: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)
