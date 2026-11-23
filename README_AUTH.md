# Authentication & Backend Setup Guide

This guide explains how to set up and use the authentication system and backend API for the Healthcare Disease Prediction System.

## Features Added

1. **User Authentication**
   - Login page with username/password
   - User registration
   - JWT token-based authentication
   - Session management

2. **Backend API (Flask)**
   - RESTful API endpoints for authentication
   - Patient records management
   - SQLite database for data persistence
   - JWT token generation and verification

3. **Logout Functionality**
   - Secure logout that invalidates tokens
   - Session cleanup

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Backend Server

Open a terminal and run:

```bash
python backend.py
```

The backend will start on `http://localhost:5000` and automatically:
- Create the SQLite database (`users.db`)
- Create default admin user (username: `admin`, password: `admin123`)

### 3. Start the Streamlit Frontend

Open another terminal and run:

```bash
streamlit run app.py
```

The frontend will be available at `http://localhost:8501`

## Default Credentials

- **Username:** `admin`
- **Password:** `admin123`

⚠️ **Important:** Change the default admin password in production!

## API Endpoints

### Authentication Endpoints

- `POST /api/register` - Register a new user
  ```json
  {
    "username": "user123",
    "email": "user@example.com",
    "password": "password123"
  }
  ```

- `POST /api/login` - Login user
  ```json
  {
    "username": "admin",
    "password": "admin123"
  }
  ```

- `POST /api/logout` - Logout user (requires Bearer token)
  Headers: `Authorization: Bearer <token>`

- `POST /api/verify` - Verify token validity
  Headers: `Authorization: Bearer <token>`

### Patient Records Endpoints

- `GET /api/patient-records` - Get all patient records for logged-in user
  Headers: `Authorization: Bearer <token>`

- `POST /api/patient-records` - Create a new patient record
  Headers: `Authorization: Bearer <token>`
  ```json
  {
    "patient_name": "John Doe",
    "age": 35,
    "gender": "Male",
    "medical_history": "Hypertension",
    "symptoms": "fever, cough",
    "predicted_disease": "Common Cold",
    "probability": 0.85
  }
  ```

- `DELETE /api/patient-records/<id>` - Delete a patient record
  Headers: `Authorization: Bearer <token>`

## Database Schema

The backend uses SQLite with three main tables:

1. **users** - User accounts
   - id, username, email, password_hash, created_at

2. **sessions** - Active user sessions
   - id, user_id, token, created_at, expires_at

3. **patient_records** - Patient prediction records
   - id, user_id, patient_name, age, gender, medical_history, symptoms, predicted_disease, probability, created_at

## Security Notes

1. **JWT Tokens**: Tokens expire after 1 day
2. **Password Hashing**: Passwords are hashed using SHA256 (consider bcrypt for production)
3. **CORS**: Enabled for Streamlit frontend
4. **Secret Key**: Change `SECRET_KEY` in `backend.py` for production

## Environment Variables

You can set the following environment variables:

- `API_BASE_URL` - Backend API URL (default: `http://localhost:5000`)
- `SECRET_KEY` - JWT secret key (default: hardcoded - change in production!)

## Troubleshooting

### Backend won't start
- Check if port 5000 is already in use
- Ensure all dependencies are installed
- Check Python version (3.7+ required)

### Can't login
- Ensure backend is running
- Check if username/password are correct
- Verify database was created (`users.db` file exists)

### Frontend can't connect to backend
- Verify backend is running on `http://localhost:5000`
- Check `API_BASE_URL` environment variable
- Check firewall settings

## Production Deployment

For production deployment:

1. Change `SECRET_KEY` in `backend.py` to a secure random string
2. Use a production database (PostgreSQL, MySQL) instead of SQLite
3. Use environment variables for sensitive configuration
4. Enable HTTPS
5. Use a production WSGI server (Gunicorn, uWSGI)
6. Implement proper password hashing (bcrypt)
7. Add rate limiting
8. Set up proper logging and monitoring

