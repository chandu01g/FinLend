# FinLend - Loan Management Platform

FinLend is a Flask + MySQL full-stack web application where users can register, apply for loans, and track status. Admin can review, approve, reject, and delete applications.

## Tech Stack
- Backend: Flask (Python)
- Frontend: HTML, CSS, JavaScript, Bootstrap
- Database: MySQL (XAMPP phpMyAdmin)

## Default Admin
- Username: `admin`
- Password: `admin123`

The default admin is auto-created on first app run when the `admin` table is empty.

## Quick Start
1. Start Apache and MySQL from XAMPP Control Panel.
2. Import `database/schema.sql` into phpMyAdmin.
3. Create and activate a virtual environment.
4. Install dependencies:
   `pip install -r requirements.txt`
5. Run app:
   `python app.py`
6. Open: `http://127.0.0.1:5000`

## MySQL Connection (XAMPP)
Edit `config.py` if needed. Default values are:
- host: `localhost`
- user: `root`
- password: `` (empty)
- database: `finlend_db`
- port: `3306`
