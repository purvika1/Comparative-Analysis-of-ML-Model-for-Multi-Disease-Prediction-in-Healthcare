# Quick Start Guide

## Step-by-Step Instructions to Run the Application

### Prerequisites
- Python 3.7 or higher installed
- All dependencies installed (see Step 1)

---

## Step 1: Install Dependencies

Open a terminal/command prompt in the project directory and run:

```bash
pip install -r requirements.txt
```

This will install all required packages including Flask, Streamlit, and other dependencies.

---

## Step 2: Start the Backend Server

**Option A: Using Command Line**
```bash
python backend.py
```

**Option B: Using the Batch File (Windows)**
Double-click `start_backend.bat`

You should see:
```
Database initialized. Default admin user created (username: admin, password: admin123)
Starting Flask backend server on http://localhost:5000
 * Running on http://0.0.0.0:5000
```

✅ **Keep this terminal window open!** The backend must be running for the frontend to work.

---

## Step 3: Start the Frontend (Streamlit App)

Open a **NEW terminal/command prompt** window (keep the backend running in the first one).

**Option A: Using Command Line**
```bash
streamlit run app.py
```

**Option B: Using the Batch File (Windows)**
Double-click `start_frontend.bat`

You should see:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

The browser should automatically open. If not, navigate to `http://localhost:8501`

---

## Step 4: Login

1. You'll see a login page
2. Use the default credentials:
   - **Username:** `admin`
   - **Password:** `admin123`
3. Click "Login"
4. You'll be redirected to the main application

---

## Step 5: Use the Application

Once logged in, you can:
- Make disease predictions
- Upload medical reports
- View patient history
- Generate PDF reports
- Logout using the sidebar button

### Validate Medical Report Extraction

To verify the upgraded report parser, use the bundled sample report:
1. From the "Medical Report Analyzer" tab, upload `sample_reports.pdf` (located in the project root).
2. Confirm that the extracted text lists Beta-hCG laboratory notes.
3. You should see context-based insights such as germ cell tumor references and new symptoms (for example `fatigue`, `nausea`).
4. Suggested diseases from the context (for example `Germ Cell Tumor`, `Gestational Trophoblastic Disease`) appear in a highlighted box.
5. The prediction table should populate using the detected symptoms. If no symptoms appear, add them manually and report the behavior.

---

## Troubleshooting

### ❌ "Connection error" when trying to login
- **Solution:** Make sure the backend is running (Step 2). Check that you see "Running on http://0.0.0.0:5000" in the backend terminal.

### ❌ "Port 5000 already in use"
- **Solution:** Another application is using port 5000. Either:
  - Close the other application
  - Change the port in `backend.py` (line with `app.run(port=5000)`) to a different port like 5001

### ❌ "Module not found" errors
- **Solution:** Run `pip install -r requirements.txt` again to ensure all packages are installed.

### ❌ Backend starts but frontend can't connect
- **Solution:** 
  1. Check that backend is running on `http://localhost:5000`
  2. Verify firewall isn't blocking the connection
  3. Check the `API_BASE_URL` in `app.py` matches your backend URL

---

## Stopping the Application

1. **To stop the frontend:** Press `Ctrl+C` in the Streamlit terminal
2. **To stop the backend:** Press `Ctrl+C` in the backend terminal

---

## Creating a New User

1. On the login page, click the "Register" tab
2. Fill in:
   - Username
   - Email
   - Password (minimum 6 characters)
   - Confirm Password
3. Click "Register"
4. You'll be automatically logged in

---

## Notes

- The backend creates a SQLite database file (`users.db`) automatically on first run
- Patient records are saved to both the backend database and local CSV file
- The default admin user is created automatically - change the password in production!

