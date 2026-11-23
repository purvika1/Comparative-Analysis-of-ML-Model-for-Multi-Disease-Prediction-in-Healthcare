# System Summary

## 🎨 Frontend (Streamlit - `app.py`)

**Technology:** Streamlit web application

**Features:**
- Modern medical-themed UI with green gradient design
- User authentication (Login/Register with OTP verification)
- Login supports both email and username
- Forgot password functionality with OTP reset
- 5 main tabs:
  - Single Disease Prediction
  - Batch CSV Analysis
  - Symptom-based Prediction
  - Diabetes Risk Assessment
  - Medical Report Upload (PDF/Image OCR)
- Patient history viewing
- PDF report generation
- Real-time predictions with visualizations

**Key Components:**
- Custom CSS styling for modern look
- API integration with backend
- Session state management
- JWT token handling

---

## ⚙️ Backend (Flask - `backend.py`)

**Technology:** Flask REST API

**Endpoints:**
- `POST /api/register` - User registration (requires OTP)
- `POST /api/login` - Login with username/email
- `POST /api/logout` - User logout
- `POST /api/verify` - Token verification
- `POST /api/send-otp` - Send OTP for registration
- `POST /api/verify-otp` - Verify OTP code
- `POST /api/forgot-password` - Request password reset
- `POST /api/reset-password` - Reset password with OTP
- `GET /api/patient-records` - Get patient records
- `POST /api/patient-records` - Create patient record
- `DELETE /api/patient-records/<id>` - Delete record
- `GET /api/health` - Health check

**Security:**
- JWT token-based authentication
- Password hashing (SHA256)
- OTP verification for registration and password reset
- Session management

**Email Service:**
- SMTP email support (Gmail/Outlook/Yahoo)
- OTP codes sent via email
- Falls back to console output if email not configured

---

## 💾 Database (SQLite - `users.db`)

**Technology:** SQLite database

**Tables:**

1. **users**
   - `id` (Primary Key)
   - `username` (Unique)
   - `email` (Unique)
   - `password_hash`
   - `created_at`

2. **sessions**
   - `id` (Primary Key)
   - `user_id` (Foreign Key)
   - `token` (JWT token)
   - `created_at`
   - `expires_at`

3. **patient_records**
   - `id` (Primary Key)
   - `user_id` (Foreign Key)
   - `patient_name`
   - `age`, `gender`
   - `medical_history`
   - `symptoms`
   - `predicted_disease`
   - `probability`
   - `created_at`

4. **otp_verification**
   - `id` (Primary Key)
   - `email`
   - `otp_code`
   - `created_at`
   - `expires_at` (10 minutes)
   - `verified` (0 or 1)

**Features:**
- Auto-created on first backend run
- Default admin user: `admin` / `admin123`
- Data persists between sessions
- Foreign key relationships

---

## 🔄 System Flow

1. **User Registration:**
   - Enter email → Receive OTP → Verify OTP → Create account

2. **User Login:**
   - Enter email/username + password → Get JWT token → Access app

3. **Password Reset:**
   - Click "Forgot Password" → Enter email → Receive OTP → Enter OTP + new password → Reset complete

4. **Disease Prediction:**
   - Enter patient details + symptoms → ML model predicts → Results saved to database → Generate PDF report

---

## 🚀 Tech Stack

- **Frontend:** Streamlit, Plotly, Pandas
- **Backend:** Flask, Flask-CORS, PyJWT
- **Database:** SQLite
- **ML Models:** scikit-learn (joblib)
- **Email:** SMTP (smtplib)
- **OCR:** Tesseract, pdfplumber
- **Reports:** ReportLab

---

## 📊 Data Flow

```
User Input → Frontend (Streamlit)
    ↓
API Request → Backend (Flask)
    ↓
Database Query → SQLite
    ↓
ML Model Prediction → Results
    ↓
Save to Database → Return to Frontend
    ↓
Display Results + Generate PDF
```

---

## 🔐 Security Features

- JWT token authentication
- Password hashing
- OTP verification (expires in 10 minutes)
- Session management
- Email verification for registration
- Secure password reset flow

---

## 📝 Default Credentials

- **Username:** `admin`
- **Email:** `admin@example.com`
- **Password:** `admin123`

---

## 🎯 Main Features

✅ User authentication with OTP
✅ Login with email or username
✅ Forgot password with OTP reset
✅ Disease prediction using ML models
✅ Batch CSV processing
✅ Medical report OCR analysis
✅ Patient record management
✅ PDF report generation
✅ Modern, responsive UI

