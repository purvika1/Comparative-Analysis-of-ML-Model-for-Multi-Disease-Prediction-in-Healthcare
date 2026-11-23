from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
import pandas as pd
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for Streamlit frontend

# Secret key for JWT tokens (in production, use environment variable)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Database file
DB_FILE = 'users.db'

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Sessions table for tracking active sessions
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  token TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  expires_at TIMESTAMP NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Patient records table
    c.execute('''CREATE TABLE IF NOT EXISTS patient_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  patient_name TEXT NOT NULL,
                  age INTEGER,
                  gender TEXT,
                  medical_history TEXT,
                  symptoms TEXT,
                  predicted_disease TEXT,
                  probability REAL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # OTP table for email verification
    c.execute('''CREATE TABLE IF NOT EXISTS otp_verification
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT NOT NULL,
                  otp_code TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  expires_at TIMESTAMP NOT NULL,
                  verified INTEGER DEFAULT 0)''')
    
    conn.commit()
    conn.close()
    
    # Create default admin user if not exists
    create_default_user()

def create_default_user():
    """Create a default admin user for testing"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if admin user exists
    c.execute("SELECT * FROM users WHERE username = ?", ('admin',))
    if not c.fetchone():
        password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                  ('admin', 'admin@example.com', password_hash))
        conn.commit()
    
    conn.close()

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash

# =============================
# OTP Functions
# =============================

# Email configuration (can be set via environment variables)
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')

def generate_otp(length=6):
    """Generate a random OTP code"""
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(email, otp_code):
    """Send OTP code to user's email"""
    try:
        # If SMTP credentials are not configured, print OTP to console (for development)
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            print(f"\n{'='*50}")
            print(f"OTP for {email}: {otp_code}")
            print(f"{'='*50}\n")
            return True
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = email
        msg['Subject'] = "Your Registration OTP Code"
        
        body = f"""
        <html>
          <body>
            <h2>Healthcare Disease Prediction System - OTP Verification</h2>
            <p>Your OTP code for registration is:</p>
            <h1 style="color: #4B8BBE; font-size: 32px; letter-spacing: 5px;">{otp_code}</h1>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this code, please ignore this email.</p>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        # For development, still print OTP to console
        print(f"\n{'='*50}")
        print(f"OTP for {email}: {otp_code}")
        print(f"{'='*50}\n")
        return False

def store_otp(email, otp_code):
    """Store OTP in database with expiration"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Delete old OTPs for this email
    c.execute("DELETE FROM otp_verification WHERE email = ?", (email,))
    
    # Insert new OTP (expires in 10 minutes)
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    c.execute("INSERT INTO otp_verification (email, otp_code, expires_at) VALUES (?, ?, ?)",
              (email, otp_code, expires_at))
    
    conn.commit()
    conn.close()

def verify_otp(email, otp_code):
    """Verify OTP code for email"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get the most recent OTP for this email
    c.execute("""SELECT otp_code, expires_at, verified 
                 FROM otp_verification 
                 WHERE email = ? 
                 ORDER BY created_at DESC LIMIT 1""", (email,))
    
    result = c.fetchone()
    conn.close()
    
    if not result:
        return False, "No OTP found for this email. Please request a new one."
    
    stored_otp, expires_at_str, verified = result
    
    # Check if already verified
    if verified:
        return False, "This OTP has already been used."
    
    # Check if expired
    expires_at = datetime.fromisoformat(expires_at_str)
    if datetime.utcnow() > expires_at:
        return False, "OTP has expired. Please request a new one."
    
    # Check if OTP matches
    if stored_otp != otp_code:
        return False, "Invalid OTP code. Please try again."
    
    # Mark OTP as verified
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE otp_verification SET verified = 1 WHERE email = ? AND otp_code = ?",
              (email, otp_code))
    conn.commit()
    conn.close()
    
    return True, "OTP verified successfully."

def generate_token(user_id, username):
    """Generate JWT token"""
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(days=1)  # Token expires in 1 day
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    """Decorator to protect routes that require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = verify_token(token)
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            request.user_id = payload['user_id']
            request.username = payload['username']
        except Exception as e:
            return jsonify({'error': 'Token verification failed'}), 401
        
        return f(*args, **kwargs)
    return decorated

# =============================
# Authentication Endpoints
# =============================

@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    """Send OTP to email for registration"""
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    # Check if email already exists
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = ?", (email,))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'Email already exists. Please use a different email address.'}), 400
    conn.close()
    
    # Generate and send OTP
    otp_code = generate_otp()
    if send_otp_email(email, otp_code):
        store_otp(email, otp_code)
        return jsonify({'message': 'OTP sent successfully to your email'}), 200
    else:
        return jsonify({'error': 'Failed to send OTP. Please try again.'}), 500

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp_endpoint():
    """Verify OTP code (without marking as used)"""
    data = request.json
    email = data.get('email')
    otp_code = data.get('otp')
    
    if not email or not otp_code:
        return jsonify({'error': 'Email and OTP code are required'}), 400
    
    # Check OTP validity without marking as verified
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get the most recent OTP for this email
    c.execute("""SELECT otp_code, expires_at, verified 
                 FROM otp_verification 
                 WHERE email = ? 
                 ORDER BY created_at DESC LIMIT 1""", (email,))
    
    result = c.fetchone()
    conn.close()
    
    if not result:
        return jsonify({'error': 'No OTP found for this email. Please request a new one.', 'verified': False}), 400
    
    stored_otp, expires_at_str, verified = result
    
    # Check if expired
    expires_at = datetime.fromisoformat(expires_at_str)
    if datetime.utcnow() > expires_at:
        return jsonify({'error': 'OTP has expired. Please request a new one.', 'verified': False}), 400
    
    # Check if OTP matches
    if stored_otp != otp_code:
        return jsonify({'error': 'Invalid OTP code. Please try again.', 'verified': False}), 400
    
    # Just validate, don't mark as verified yet (will be marked when actually used)
    return jsonify({'message': 'OTP verified successfully', 'verified': True}), 200

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user (requires OTP verification)"""
    data = request.json
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    otp_code = data.get('otp')
    
    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    
    if not otp_code:
        return jsonify({'error': 'OTP code is required. Please verify your email first.'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    # Verify OTP first
    is_valid, message = verify_otp(email, otp_code)
    if not is_valid:
        return jsonify({'error': message}), 400
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        # Check if username already exists
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return jsonify({'error': 'Username already exists. Please choose a different username.'}), 400
        
        # Check if email already exists (double check)
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        if c.fetchone():
            conn.close()
            return jsonify({'error': 'Email already exists. Please use a different email address.'}), 400
        
        # If both are available, proceed with registration
        password_hash = hash_password(password)
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                  (username, email, password_hash))
        user_id = c.lastrowid
        conn.commit()
        
        token = generate_token(user_id, username)
        
        # Store session
        expires_at = datetime.utcnow() + timedelta(days=1)
        c.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
                  (user_id, token, expires_at))
        conn.commit()
        
        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user_id': user_id,
            'username': username
        }), 201
    
    except sqlite3.IntegrityError as e:
        # Fallback error handling (shouldn't reach here with our checks above)
        conn.close()
        return jsonify({'error': 'Registration failed. Username or email may already exist.'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    """Login user with username or email"""
    data = request.json
    
    username_or_email = data.get('username') or data.get('email')  # Accept both
    password = data.get('password')
    
    if not username_or_email or not password:
        return jsonify({'error': 'Username/Email and password required'}), 400
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Try to find user by username or email
    c.execute("SELECT id, username, email, password_hash FROM users WHERE username = ? OR email = ?", 
              (username_or_email, username_or_email))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401
    
    user_id, db_username, email, password_hash = user
    
    if not verify_password(password, password_hash):
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Generate token
    token = generate_token(user_id, db_username)
    
    # Store session
    expires_at = datetime.utcnow() + timedelta(days=1)
    c.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
              (user_id, token, expires_at))
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user_id': user_id,
        'username': db_username,
        'email': email
    }), 200

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """Send password reset OTP to email"""
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if email exists
    c.execute("SELECT id, username FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        # Don't reveal if email exists for security
        return jsonify({'message': 'If the email exists, a password reset code has been sent.'}), 200
    
    user_id, username = user
    conn.close()
    
    # Generate and send OTP
    otp_code = generate_otp()
    if send_otp_email(email, otp_code):
        # Store OTP with a flag indicating it's for password reset
        store_otp(email, otp_code)
        return jsonify({'message': 'Password reset code sent to your email'}), 200
    else:
        return jsonify({'error': 'Failed to send reset code. Please try again.'}), 500

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    """Reset password using OTP"""
    data = request.json
    email = data.get('email')
    otp_code = data.get('otp')
    new_password = data.get('new_password')
    
    if not email or not otp_code or not new_password:
        return jsonify({'error': 'Email, OTP code, and new password are required'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    # Verify OTP
    is_valid, message = verify_otp(email, otp_code)
    if not is_valid:
        return jsonify({'error': message}), 400
    
    # Update password
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT id FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    # Hash new password
    password_hash = hash_password(new_password)
    c.execute("UPDATE users SET password_hash = ? WHERE email = ?", (password_hash, email))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Password reset successfully. You can now login with your new password.'}), 200

@app.route('/api/logout', methods=['POST'])
@token_required
def logout():
    """Logout user (invalidate token)"""
    token = request.headers.get('Authorization')
    if token.startswith('Bearer '):
        token = token[7:]
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/api/verify', methods=['POST'])
def verify():
    """Verify token validity"""
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({'valid': False}), 401
    
    if token.startswith('Bearer '):
        token = token[7:]
    
    payload = verify_token(token)
    if not payload:
        return jsonify({'valid': False}), 401
    
    return jsonify({
        'valid': True,
        'user_id': payload['user_id'],
        'username': payload['username']
    }), 200

# =============================
# Patient Records Endpoints
# =============================

@app.route('/api/patient-records', methods=['GET'])
@token_required
def get_patient_records():
    """Get all patient records for the logged-in user"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("""SELECT id, patient_name, age, gender, medical_history, 
                 symptoms, predicted_disease, probability, created_at
                 FROM patient_records WHERE user_id = ? ORDER BY created_at DESC""",
              (request.user_id,))
    
    records = c.fetchall()
    conn.close()
    
    result = []
    for record in records:
        result.append({
            'id': record[0],
            'patient_name': record[1],
            'age': record[2],
            'gender': record[3],
            'medical_history': record[4],
            'symptoms': record[5],
            'predicted_disease': record[6],
            'probability': record[7],
            'created_at': record[8]
        })
    
    return jsonify({'records': result}), 200

@app.route('/api/patient-records', methods=['POST'])
@token_required
def create_patient_record():
    """Create a new patient record"""
    data = request.json
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("""INSERT INTO patient_records 
                 (user_id, patient_name, age, gender, medical_history, 
                  symptoms, predicted_disease, probability)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (request.user_id,
               data.get('patient_name'),
               data.get('age'),
               data.get('gender'),
               data.get('medical_history'),
               data.get('symptoms'),
               data.get('predicted_disease'),
               data.get('probability')))
    
    record_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Record created successfully', 'id': record_id}), 201

@app.route('/api/patient-records/<int:record_id>', methods=['DELETE'])
@token_required
def delete_patient_record(record_id):
    """Delete a patient record"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Verify record belongs to user
    c.execute("SELECT user_id FROM patient_records WHERE id = ?", (record_id,))
    record = c.fetchone()
    
    if not record:
        conn.close()
        return jsonify({'error': 'Record not found'}), 404
    
    if record[0] != request.user_id:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403
    
    c.execute("DELETE FROM patient_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Record deleted successfully'}), 200

# =============================
# Health Check
# =============================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Healthcare Prediction API'}), 200

if __name__ == '__main__':
    init_db()
    print("Database initialized. Default admin user created (username: admin, password: admin123)")
    print("Starting Flask backend server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

