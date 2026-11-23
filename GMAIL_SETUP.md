# Gmail OTP Setup Guide

This guide will help you configure Gmail to send OTP (One-Time Password) codes via email.

## Why Gmail App Password?

Gmail requires an **App Password** (not your regular password) to send emails via SMTP. This is a security feature that allows third-party applications to access your Gmail account securely.

## Step-by-Step Instructions

### Step 1: Enable 2-Step Verification

1. Go to your Google Account: https://myaccount.google.com/
2. Click on **Security** in the left sidebar
3. Under "Signing in to Google", find **2-Step Verification**
4. If it's not enabled, click on it and follow the prompts to enable it
   - You'll need to verify your phone number
   - Google will send you a verification code

### Step 2: Generate App Password

1. After enabling 2-Step Verification, go back to **Security** settings
2. Under "Signing in to Google", you should now see **App passwords**
3. Click on **App passwords**
   - You may need to sign in again
4. Select **Mail** as the app
5. Select **Other (Custom name)** as the device
6. Enter a name like "Healthcare App OTP" or "Disease Prediction System"
7. Click **Generate**
8. **Copy the 16-character password** that appears (it will look like: `abcd efgh ijkl mnop`)
   - ⚠️ **Important**: You can only see this password once! Copy it immediately.

### Step 3: Configure Your Application

1. Create a `.env` file in your project root directory (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

2. Open the `.env` file and fill in your details:
   ```env
   SMTP_EMAIL=your-email@gmail.com
   SMTP_PASSWORD=abcd efgh ijkl mnop
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   ```

   **Important Notes:**
   - Use your **full Gmail address** for `SMTP_EMAIL`
   - Use the **16-character App Password** (you can include or remove spaces, both work)
   - Do NOT use your regular Gmail password

3. Save the `.env` file

### Step 4: Install Dependencies

Make sure you have the required package:
```bash
pip install python-dotenv
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### Step 5: Test the Setup

1. Start your backend server:
   ```bash
   python backend.py
   ```

2. The backend will automatically load the `.env` file

3. Try registering a new user or requesting a password reset - the OTP should be sent to the email address via Gmail!

## Troubleshooting

### "Invalid credentials" or "Authentication failed"

- Make sure you're using an **App Password**, not your regular Gmail password
- Verify that 2-Step Verification is enabled on your Google account
- Check that the App Password was copied correctly (no extra spaces)

### "Connection refused" or "Could not connect to SMTP server"

- Check your internet connection
- Verify firewall settings aren't blocking port 587
- Try using port 465 with SSL instead (requires code modification)

### OTP not received in email

- Check your spam/junk folder
- Verify the email address is correct
- Check the backend console for error messages
- Make sure the `.env` file is in the same directory as `backend.py`

### Still seeing OTP in console instead of email

- Verify that `SMTP_EMAIL` and `SMTP_PASSWORD` are set in your `.env` file
- Make sure the `.env` file is in the project root directory
- Restart the backend server after creating/modifying the `.env` file

## Security Best Practices

1. **Never commit `.env` to version control** - it's already in `.gitignore`
2. **Use a dedicated Gmail account** for production applications (not your personal email)
3. **Rotate App Passwords** periodically for security
4. **Keep your App Passwords secure** - treat them like regular passwords

## Alternative: Using Other Email Providers

If you prefer not to use Gmail, you can use other SMTP providers:

### Outlook/Hotmail
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_EMAIL=your-email@outlook.com
SMTP_PASSWORD=your-password
```

### Yahoo Mail
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_EMAIL=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

### Custom SMTP Server
```env
SMTP_SERVER=your-smtp-server.com
SMTP_PORT=587
SMTP_EMAIL=your-email@domain.com
SMTP_PASSWORD=your-password
```

## Need Help?

If you're still having issues:
1. Check the backend console for detailed error messages
2. Verify all environment variables are set correctly
3. Test your SMTP credentials using a simple Python script
4. Check Google Account security settings

