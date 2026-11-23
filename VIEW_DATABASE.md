# How to View the Database

## Database File Location

The database file `users.db` is located in the same directory as `backend.py`:
```
puri02/
  ├── backend.py
  ├── app.py
  ├── users.db  ← Your database file is here
  └── ...
```

## Method 1: Using the Python Script (Easiest)

I've created a simple script to view the database:

1. **Install tabulate** (if not already installed):
   ```bash
   pip install tabulate
   ```

2. **Run the viewer script**:
   ```bash
   python view_database.py
   ```

This will display all tables and their contents in a nice formatted table.

## Method 2: Using DB Browser for SQLite (Recommended GUI)

1. **Download DB Browser for SQLite**:
   - Windows: https://sqlitebrowser.org/dl/
   - Mac: `brew install --cask db-browser-for-sqlite`
   - Linux: Available in most package managers

2. **Open the database**:
   - Launch DB Browser
   - Click "Open Database"
   - Navigate to your project folder
   - Select `users.db`
   - Browse tables, view data, run queries

## Method 3: Using VS Code Extension

1. **Install SQLite extension** in VS Code:
   - Search for "SQLite" in Extensions
   - Install "SQLite Viewer" or "SQLite" extension

2. **Open the database**:
   - Right-click `users.db` in VS Code
   - Select "Open Database" or "Open with SQLite Viewer"
   - Browse tables in the sidebar

## Method 4: Using Command Line (SQLite3)

1. **Open terminal** in your project directory

2. **Run SQLite**:
   ```bash
   sqlite3 users.db
   ```

3. **View tables**:
   ```sql
   .tables                    -- List all tables
   SELECT * FROM users;       -- View users table
   SELECT * FROM sessions;    -- View sessions table
   SELECT * FROM patient_records;  -- View patient records
   SELECT * FROM otp_verification;  -- View OTP codes
   .schema                    -- View table schemas
   .quit                      -- Exit
   ```

## Method 5: Quick Python Command

Run this in Python or a Jupyter notebook:

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('users.db')

# View users table
users_df = pd.read_sql_query("SELECT * FROM users", conn)
print("USERS:")
print(users_df)

# View patient records
records_df = pd.read_sql_query("SELECT * FROM patient_records", conn)
print("\nPATIENT RECORDS:")
print(records_df)

conn.close()
```

## What You'll See

### users Table
- All registered user accounts
- Usernames, emails, password hashes
- Account creation dates

### sessions Table
- Active user login sessions
- JWT tokens
- Session expiration times

### patient_records Table
- All disease prediction records
- Patient information
- Symptoms and predicted diseases
- Prediction probabilities

### otp_verification Table
- OTP codes sent for registration
- Email addresses
- Expiration times
- Verification status

## Tips

- **Database is created automatically** when you first run `backend.py`
- **Data persists** between backend restarts
- **To reset database**: Delete `users.db` and restart backend (creates fresh database)
- **Backup database**: Simply copy `users.db` file

## Troubleshooting

**"Database file not found"**
- Make sure you've run `backend.py` at least once
- Check you're in the correct directory
- Look for `users.db` in the project root

**"Permission denied"**
- Make sure the database file isn't locked by another process
- Close DB Browser or other tools accessing the database
- Restart the backend if needed

