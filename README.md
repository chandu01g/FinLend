# FinLend - Loan Management Platform

![Flask](https://img.shields.io/badge/Backend-Flask-000000?logo=flask)
![MySQL](https://img.shields.io/badge/Database-MySQL-00758F?logo=mysql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/UI-Bootstrap-7952B3?logo=bootstrap&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)

FinLend is a Flask + MySQL full-stack web application where users can register, verify phone with OTP, apply for loans, and track status. Admin can review, approve, reject, and delete applications.

## Features
- User registration/login with hashed passwords.
- Phone number verification via OTP before account creation.
- Manual OTP verification input on register page.
- Loan application with:
  - interest rate
  - installments (tenure)
  - EMI
  - total interest
  - total payable amount
- User dashboard with loan history and repayment details.
- Admin dashboard for user and loan management.
- REST endpoints for user loans and admin stats.

## Screenshots
Add your project screenshots in `docs/screenshots/` and update links below.

- Login page: `docs/screenshots/login.png`
- Register + OTP page: `docs/screenshots/register-otp.png`
- User dashboard: `docs/screenshots/dashboard.png`
- Admin dashboard: `docs/screenshots/admin-dashboard.png`

## Tech Stack
- Backend: Flask (Python)
- Frontend: HTML, CSS, JavaScript, Bootstrap
- Database: MySQL (XAMPP phpMyAdmin)

## Default Admin
- Username: `admin`
- Password: `admin123`

The default admin is auto-created on first app run when the `admin` table is empty.

## Project Setup
1. Start Apache and MySQL from XAMPP Control Panel.
2. Import `database/schema.sql` into phpMyAdmin.
3. Create and activate virtual environment.
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Create `.env` from sample:
   ```bash
   copy .env.example .env
   ```
6. Run app:
   ```bash
   python app.py
   ```
7. Open: `http://127.0.0.1:5000`

## Environment Variables (`.env`)
```env
SECRET_KEY=replace-with-a-strong-secret-key
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=finlend_db
MYSQL_PORT=3306
OTP_PROVIDER=twilio
OTP_DEBUG_MODE=false
OTP_AUTOFILL_ORIGIN=localhost
OTP_SMS_TEMPLATE=Your FinLend OTP is {otp}. Valid for {expiry_minutes} minutes. Do not share this code.
TEXTLOCAL_API_URL=https://api.txtlocal.in/send/
TEXTLOCAL_API_KEY=your_textlocal_api_key
TEXTLOCAL_SENDER=
TEXTLOCAL_DLT_TE_ID=
TEXTLOCAL_COUNTRY_CODE=91
TEXTLOCAL_TEST_MODE=false
FAST2SMS_API_URL=https://www.fast2sms.com/dev/bulkV2
FAST2SMS_API_KEY=your_fast2sms_api_key
FAST2SMS_ROUTE=q
FAST2SMS_LANGUAGE=english
FAST2SMS_FLASH=0
FAST2SMS_SENDER_ID=
TWILIO_VERIFY_API_URL=https://verify.twilio.com/v2
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_VERIFY_SERVICE_SID=your_twilio_verify_service_sid
TWILIO_COUNTRY_CODE=91
```

## MySQL Connection (XAMPP)
Connection is configured in `config.py`:
- host: `localhost`
- user: `root`
- password: empty by default
- database: `finlend_db`
- port: `3306`

## OTP Note
- Real SMS sending supports Textlocal (`OTP_PROVIDER=textlocal`), Fast2SMS (`OTP_PROVIDER=fast2sms`), and Twilio Verify (`OTP_PROVIDER=twilio`).
- Set provider-specific API keys in `.env` and restart Flask.
- In development (`OTP_DEBUG_MODE=true`), OTP is also shown in UI for testing fallback.

## API Endpoints
- `POST /api/auth/send-otp`
- `POST /api/auth/verify-otp`
- `GET /api/loans`
- `GET /api/admin/stats`
