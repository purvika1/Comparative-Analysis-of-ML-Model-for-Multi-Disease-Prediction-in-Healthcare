# OTP Email Configuration Guide

## Overview

The registration system now requires OTP (One-Time Password) verification via email. This guide explains how to configure email sending.

## Development Mode (Default)

**By default, the system runs in development mode** where OTP codes are printed to the backend console instead of being sent via email. This is perfect for testing.

When you click "Send OTP" during registration:
- The OTP will appear in the backend terminal/console
- Look for output like:
  ```
  ==================================================
  OTP for user@example.com: 123456
  ==================================================
  ```

## Production Mode (Email Configuration)

To enable actual email sending, set the following environment variables:

### For Gmail:

1. **Enable "Less secure app access"** or use **App Password**:
   - Go to your Google Account settings
   - Enable 2-Step Verification
   - Generate an App Password for "Mail"

2. **Set environment variables:**
   ```bash
   # Windows (PowerShell)
   $env:SMTP_EMAIL="your-email@gmail.com"
   $env:SMTP_PASSWORD="your-app-password"
   $env:SMTP_SERVER="smtp.gmail.com"
   $env:SMTP_PORT="587"

   # Windows (CMD)
   set SMTP_EMAIL=your-email@gmail.com
   set SMTP_PASSWORD=your-app-password
   set SMTP_SERVER=smtp.gmail.com
   set SMTP_PORT=587

   # Linux/Mac
   export SMTP_EMAIL="your-email@gmail.com"
   export SMTP_PASSWORD="your-app-password"
   export SMTP_SERVER="smtp.gmail.com"
   export SMTP_PORT="587"
   ```

3. **Or modify `backend.py` directly** (not recommended for production):
   ```python
   SMTP_EMAIL = 'your-email@gmail.com'
   SMTP_PASSWORD = 'your-app-password'
   ```

### For Other Email Providers:

**Outlook/Hotmail:**
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

**Yahoo:**
```bash
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
```

**Custom SMTP:**
```bash
SMTP_SERVER=your-smtp-server.com
SMTP_PORT=587  # or 465 for SSL
```

## How OTP Works

1. **User enters email** in registration form
2. **Clicks "Send OTP"** button
3. **System generates 6-digit OTP** and stores it in database
4. **OTP is sent to email** (or printed to console in dev mode)
5. **User enters OTP** in the registration form
6. **System verifies OTP** before completing registration
7. **OTP expires after 10 minutes**
8. **OTP can only be used once**

## Testing Without Email

For development and testing:
- **No configuration needed** - OTPs will appear in backend console
- Just check the terminal where `backend.py` is running
- Copy the OTP code and paste it in the registration form

## Troubleshooting

### OTP not appearing in console
- Make sure backend is running
- Check backend terminal for any errors
- Try clicking "Send OTP" again

### Email not sending (production)
- Verify SMTP credentials are correct
- Check firewall settings
- For Gmail, ensure App Password is used (not regular password)
- Check spam folder if email seems to be sent

### OTP expired
- OTPs expire after 10 minutes
- Click "Send OTP" again to get a new code

### "OTP already used" error
- Each OTP can only be used once
- Request a new OTP if you need to try again

## Security Notes

- OTPs expire after 10 minutes
- Each OTP can only be verified once
- Old OTPs are automatically deleted when new ones are sent
- Never share OTP codes with others
- In production, use secure email credentials (environment variables)

