# FinLend - Loan Management Platform

![Flask](https://img.shields.io/badge/Backend-Flask-000000?logo=flask)
![MySQL](https://img.shields.io/badge/Database-MySQL-00758F?logo=mysql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/UI-Bootstrap-7952B3?logo=bootstrap&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)

FinLend is a Flask + MySQL full-stack web application where users can register, verify phone with OTP, apply for loans, and track status. Admin can review, approve, reject, and delete applications.

## Features
- User registration/login with hashed passwords.
- Phone number verification via OTP before account creation.
- OTP auto-fill support for compatible browsers (WebOTP API).
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
OTP_DEBUG_MODE=true
OTP_AUTOFILL_ORIGIN=localhost
```

## MySQL Connection (XAMPP)
Connection is configured in `config.py`:
- host: `localhost`
- user: `root`
- password: empty by default
- database: `finlend_db`
- port: `3306`

## OTP Note
- In development (`OTP_DEBUG_MODE=true`), OTP is shown in UI for testing.
- In production, disable debug mode and integrate an SMS provider (Twilio/Fast2SMS/etc.) for real delivery.

## API Endpoints
- `POST /api/auth/send-otp`
- `POST /api/auth/verify-otp`
- `GET /api/loans`
- `GET /api/admin/stats`
