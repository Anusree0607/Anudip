from flask import Flask, request, render_template, jsonify, redirect, url_for, session, flash
import pandas as pd
import pickle
import os
import sqlite3
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# === Load the best trained model pipeline ===
model_path = r'C:\Users\DELL\OneDrive\Desktop\block_code\Models\best_model.pkl'
with open(model_path, 'rb') as file:
    model = pickle.load(file)

# === User login DB function ===
def get_user(username):
    db_path = r'C:\Users\DELL\OneDrive\Desktop\block_code\users.db'
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
        X = preprocess_for_prediction(df)
        predictions = model.predict(X)
        fraud_count = (predictions == 1).sum()
        return jsonify({'fraud_count': int(fraud_count), 'total': len(predictions)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === Single Transaction Prediction ===
@app.route('/predict', methods=['POST'])
def predict_transaction():
    try:
        data = request.form.to_dict()

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
        
        # Debug: Print feature values and model steps
        print("Input Features:", features.to_dict(orient='records')[0])
        if hasattr(model, 'named_steps'):
            print("Pipeline Steps:", list(model.named_steps.keys()))
            if 'selectkbest' in model.named_steps:
                selector = model.named_steps['selectkbest']
                mask = selector.get_support()
                feature_names = ['amount', 'location', 'transaction_type', 'device_id', 'hour', 'day_of_week', 'is_weekend']
                selected_features = [name for name, selected in zip(feature_names, mask) if selected]
                print("Selected Features by SelectKBest:", selected_features)

        # Force raw prediction check
        threshold = 0.4
        try:
            prob = model.predict_proba(features)[0][1]  # Probability of fraud
            prediction = 1 if prob >= threshold else 0
            result = 'Fraud' if prediction == 1 else 'Legit'
        except ValueError as e:
            print(f"Prediction Error: {e}")
            # Fallback to raw predict if proba fails
            prediction = model.predict(features)[0]
            result = 'Fraud' if prediction == 1 else 'Legit'
            prob = None  # No probability if raw predict is used

        print(f"Prediction: {result}, Probability: {prob if prob else 'N/A'}, Threshold: {threshold}")
        
        return jsonify({'prediction': result, 'fraud_probability': prob if prob else 0.0})

    except Exception as e:
        return jsonify({'prediction': f'Error: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)
