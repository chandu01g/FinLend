import math
import random
import re
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List

import mysql.connector
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config["SECRET_KEY"]

OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 30


def get_db_connection():
    """Create a MySQL connection using settings from config.py."""
    return mysql.connector.connect(
        host=app.config["MYSQL_HOST"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        database=app.config["MYSQL_DB"],
        port=app.config["MYSQL_PORT"],
    )


def run_select(query: str, params: tuple = (), one: bool = False):
    """Run a SELECT query safely with placeholders."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchone() if one else cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def run_modify(query: str, params: tuple = ()):
    """Run INSERT/UPDATE/DELETE safely with placeholders."""
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, params)
        connection.commit()
        return cursor.lastrowid, cursor.rowcount
    finally:
        cursor.close()
        connection.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access required.", "danger")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped_view


def normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def valid_email(email: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email))


def valid_phone(phone: str) -> bool:
    digits = normalize_phone(phone)
    return 10 <= len(digits) <= 15


def check_eligibility(income: float, loan_amount: float) -> bool:
    """
    Simple eligibility rule:
    - Minimum monthly income: 15,000
    - Maximum loan: 20x monthly income
    """
    return income >= 15000 and loan_amount <= (income * 20)


def calculate_loan_breakdown(principal: float, annual_rate: float, months: int) -> Dict[str, float]:
    """Return EMI, total interest, and total payable values."""
    monthly_rate = annual_rate / 1200

    if monthly_rate == 0:
        emi = principal / months
    else:
        factor = math.pow(1 + monthly_rate, months)
        emi = (principal * monthly_rate * factor) / (factor - 1)

    total_payable = emi * months
    total_interest = total_payable - principal

    return {
        "emi_amount": round(emi, 2),
        "total_interest": round(total_interest, 2),
        "total_payable": round(total_payable, 2),
    }


def get_request_payload() -> Dict[str, Any]:
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def seed_default_admin():
    """
    Create a default admin if the admin table is empty.
    Username: admin
    Password: admin123
    """
    try:
        admin_count = run_select("SELECT COUNT(*) AS count FROM admin", one=True)
        if admin_count and admin_count["count"] == 0:
            password_hash = generate_password_hash("admin123")
            run_modify(
                "INSERT INTO admin (username, password_hash) VALUES (%s, %s)",
                ("admin", password_hash),
            )
            print("Default admin created (username: admin, password: admin123)")
    except mysql.connector.Error as exc:
        print(f"Admin seed skipped: {exc}")


def serialize_loan(loan: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MySQL row values to JSON-friendly types."""
    item = dict(loan)

    numeric_fields = [
        "income",
        "loan_amount",
        "annual_interest_rate",
        "emi_amount",
        "total_interest",
        "total_payable",
    ]
    for field in numeric_fields:
        if field in item and item[field] is not None:
            item[field] = float(item[field])

    if "tenure_months" in item and item["tenure_months"] is not None:
        item["tenure_months"] = int(item["tenure_months"])

    item["created_at"] = item["created_at"].isoformat() if item.get("created_at") else None
    item["updated_at"] = item["updated_at"].isoformat() if item.get("updated_at") else None
    return item


@app.route("/")
def home():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/api/auth/send-otp", methods=["POST"])
def send_otp():
    payload = get_request_payload()
    phone = normalize_phone(payload.get("phone", ""))
    purpose = (payload.get("purpose", "register") or "register").strip().lower()

    if purpose not in {"register"}:
        return jsonify({"success": False, "message": "Invalid OTP purpose."}), 400
    if not valid_phone(phone):
        return jsonify({"success": False, "message": "Please enter a valid phone number."}), 400

    try:
        latest = run_select(
            """
            SELECT id, created_at
            FROM phone_otps
            WHERE phone = %s AND purpose = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (phone, purpose),
            one=True,
        )

        if latest and latest.get("created_at"):
            elapsed = (datetime.utcnow() - latest["created_at"]).total_seconds()
            if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
                wait_seconds = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Please wait {wait_seconds}s before requesting another OTP.",
                        }
                    ),
                    429,
                )

        code = f"{random.randint(100000, 999999)}"
        code_hash = generate_password_hash(code)
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)

        run_modify("DELETE FROM phone_otps WHERE phone = %s AND purpose = %s", (phone, purpose))
        run_modify(
            """
            INSERT INTO phone_otps (phone, purpose, otp_hash, expires_at, attempts, is_verified)
            VALUES (%s, %s, %s, %s, 0, 0)
            """,
            (phone, purpose, code_hash, expires_at),
        )

        response = {
            "success": True,
            "message": "OTP generated successfully. Check your SMS inbox.",
            "expires_in_seconds": OTP_EXPIRY_MINUTES * 60,
        }

        # Development convenience: show OTP in UI when debug is enabled.
        if app.config.get("OTP_DEBUG_MODE", False):
            response["demo_otp"] = code
            response["demo_sms_format"] = (
                f"<#> FinLend OTP is {code}. Do not share this code.\n"
                f"@{app.config['OTP_AUTOFILL_ORIGIN']} #{code}"
            )

        return jsonify(response)
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():
    payload = get_request_payload()
    phone = normalize_phone(payload.get("phone", ""))
    otp = str(payload.get("otp", "")).strip()
    purpose = (payload.get("purpose", "register") or "register").strip().lower()

    if purpose not in {"register"}:
        return jsonify({"success": False, "message": "Invalid OTP purpose."}), 400
    if not valid_phone(phone):
        return jsonify({"success": False, "message": "Please enter a valid phone number."}), 400
    if not re.fullmatch(r"\d{6}", otp):
        return jsonify({"success": False, "message": "OTP must be a 6-digit number."}), 400

    try:
        otp_row = run_select(
            """
            SELECT id, otp_hash, expires_at, attempts, is_verified
            FROM phone_otps
            WHERE phone = %s AND purpose = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (phone, purpose),
            one=True,
        )

        if not otp_row:
            return jsonify({"success": False, "message": "No OTP request found. Please send OTP first."}), 404

        if otp_row["is_verified"]:
            session[f"{purpose}_verified_phone"] = phone
            return jsonify({"success": True, "message": "Phone already verified."})

        if datetime.utcnow() > otp_row["expires_at"]:
            return jsonify({"success": False, "message": "OTP expired. Please request a new OTP."}), 400

        if otp_row["attempts"] >= OTP_MAX_ATTEMPTS:
            return jsonify({"success": False, "message": "Maximum OTP attempts reached. Please request a new OTP."}), 429

        if not check_password_hash(otp_row["otp_hash"], otp):
            run_modify("UPDATE phone_otps SET attempts = attempts + 1 WHERE id = %s", (otp_row["id"],))
            return jsonify({"success": False, "message": "Invalid OTP."}), 400

        run_modify(
            "UPDATE phone_otps SET is_verified = 1, verified_at = UTC_TIMESTAMP() WHERE id = %s",
            (otp_row["id"],),
        )
        session[f"{purpose}_verified_phone"] = phone
        return jsonify({"success": True, "message": "Phone number verified successfully."})
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone_raw = request.form.get("phone", "").strip()
        phone = normalize_phone(phone_raw)
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([full_name, email, phone, address, password, confirm_password]):
            flash("All fields are required.", "danger")
            return render_template("register.html")
        if not valid_email(email):
            flash("Please enter a valid email address.", "danger")
            return render_template("register.html")
        if not valid_phone(phone):
            flash("Please enter a valid phone number.", "danger")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register.html")
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        verified_phone = session.get("register_verified_phone")
        if verified_phone != phone:
            flash("Please verify your phone number using OTP before registering.", "warning")
            return render_template("register.html")

        try:
            existing = run_select("SELECT id FROM users WHERE email = %s", (email,), one=True)
            if existing:
                flash("Email already registered. Please login.", "warning")
                return redirect(url_for("login"))

            password_hash = generate_password_hash(password)
            run_modify(
                """
                INSERT INTO users (full_name, email, phone, address, password_hash)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (full_name, email, phone, address, password_hash),
            )
            session.pop("register_verified_phone", None)
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))
        except mysql.connector.Error as exc:
            flash(f"Database error: {exc}", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html")

        try:
            user = run_select("SELECT * FROM users WHERE email = %s", (email,), one=True)
            if not user or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "danger")
                return render_template("login.html")

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["is_admin"] = False
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))
        except mysql.connector.Error as exc:
            flash(f"Database error: {exc}", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    try:
        loans: List[Dict[str, Any]] = run_select(
            """
            SELECT id, income, employment_type, loan_amount, loan_purpose, status,
                   annual_interest_rate, tenure_months, emi_amount, total_interest, total_payable,
                   created_at, updated_at
            FROM loan_applications
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (session["user_id"],),
        )

        stats = {
            "total": len(loans),
            "pending": sum(1 for loan in loans if loan["status"] == "Pending"),
            "approved": sum(1 for loan in loans if loan["status"] == "Approved"),
            "rejected": sum(1 for loan in loans if loan["status"] == "Rejected"),
        }
        return render_template("dashboard.html", loans=loans, stats=stats)
    except mysql.connector.Error as exc:
        flash(f"Database error: {exc}", "danger")
        return render_template(
            "dashboard.html",
            loans=[],
            stats={"total": 0, "pending": 0, "approved": 0, "rejected": 0},
        )


@app.route("/apply-loan", methods=["GET", "POST"])
@login_required
def apply_loan():
    try:
        user = run_select(
            "SELECT full_name, email, phone, address FROM users WHERE id = %s",
            (session["user_id"],),
            one=True,
        )
    except mysql.connector.Error as exc:
        flash(f"Database error: {exc}", "danger")
        user = None

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone_raw = request.form.get("phone", "").strip()
        phone = normalize_phone(phone_raw)
        address = request.form.get("address", "").strip()
        income_raw = request.form.get("income", "").strip()
        employment_type = request.form.get("employment_type", "").strip()
        loan_amount_raw = request.form.get("loan_amount", "").strip()
        annual_interest_rate_raw = request.form.get("annual_interest_rate", "").strip()
        tenure_months_raw = request.form.get("tenure_months", "").strip()
        loan_purpose = request.form.get("loan_purpose", "").strip()

        if not all(
            [
                full_name,
                email,
                phone,
                address,
                income_raw,
                employment_type,
                loan_amount_raw,
                annual_interest_rate_raw,
                tenure_months_raw,
                loan_purpose,
            ]
        ):
            flash("All fields are required.", "danger")
            return render_template("apply_loan.html", user=user)
        if not valid_email(email):
            flash("Please enter a valid email address.", "danger")
            return render_template("apply_loan.html", user=user)
        if not valid_phone(phone):
            flash("Please enter a valid phone number.", "danger")
            return render_template("apply_loan.html", user=user)
        if employment_type not in ["Salaried", "Self-Employed", "Business", "Student", "Other"]:
            flash("Invalid employment type selected.", "danger")
            return render_template("apply_loan.html", user=user)

        try:
            income = float(income_raw)
            loan_amount = float(loan_amount_raw)
            annual_interest_rate = float(annual_interest_rate_raw)
            tenure_months = int(tenure_months_raw)
        except ValueError:
            flash("Income, amount, interest rate, and installments must be valid numbers.", "danger")
            return render_template("apply_loan.html", user=user)

        if income <= 0 or loan_amount <= 0:
            flash("Income and loan amount must be greater than 0.", "danger")
            return render_template("apply_loan.html", user=user)
        if annual_interest_rate < 0 or annual_interest_rate > 60:
            flash("Interest rate must be between 0 and 60.", "danger")
            return render_template("apply_loan.html", user=user)
        if tenure_months < 1 or tenure_months > 480:
            flash("Installments must be between 1 and 480 months.", "danger")
            return render_template("apply_loan.html", user=user)
        if len(loan_purpose) < 5:
            flash("Loan purpose must be at least 5 characters.", "danger")
            return render_template("apply_loan.html", user=user)
        if not check_eligibility(income, loan_amount):
            flash("You are currently not eligible for this loan amount.", "warning")
            return render_template("apply_loan.html", user=user)

        breakdown = calculate_loan_breakdown(loan_amount, annual_interest_rate, tenure_months)

        try:
            # Keep user profile details synced with latest form submission.
            run_modify(
                """
                UPDATE users
                SET full_name = %s, email = %s, phone = %s, address = %s
                WHERE id = %s
                """,
                (full_name, email, phone, address, session["user_id"]),
            )
            run_modify(
                """
                INSERT INTO loan_applications
                (
                    user_id, full_name, email, phone, address,
                    income, employment_type, loan_amount, annual_interest_rate,
                    tenure_months, emi_amount, total_interest, total_payable,
                    loan_purpose, status
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, 'Pending'
                )
                """,
                (
                    session["user_id"],
                    full_name,
                    email,
                    phone,
                    address,
                    income,
                    employment_type,
                    loan_amount,
                    annual_interest_rate,
                    tenure_months,
                    breakdown["emi_amount"],
                    breakdown["total_interest"],
                    breakdown["total_payable"],
                    loan_purpose,
                ),
            )
            flash(
                (
                    "Loan application submitted. "
                    f"EMI: Rs {breakdown['emi_amount']:.2f} per month, "
                    f"Installments: {tenure_months}, "
                    f"Total interest: Rs {breakdown['total_interest']:.2f}."
                ),
                "success",
            )
            return redirect(url_for("dashboard"))
        except mysql.connector.Error as exc:
            flash(f"Database error: {exc}", "danger")

    return render_template("apply_loan.html", user=user)


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("admin.html")

        try:
            admin = run_select("SELECT * FROM admin WHERE username = %s", (username,), one=True)
            if not admin or not check_password_hash(admin["password_hash"], password):
                flash("Invalid admin credentials.", "danger")
                return render_template("admin.html")

            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            session["is_admin"] = True
            flash("Admin login successful.", "success")
            return redirect(url_for("admin_dashboard"))
        except mysql.connector.Error as exc:
            flash(f"Database error: {exc}", "danger")

    return render_template("admin.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    try:
        users = run_select(
            "SELECT id, full_name, email, phone, created_at FROM users ORDER BY created_at DESC"
        )
        loans = run_select(
            """
            SELECT la.id, la.user_id, la.full_name, la.email, la.phone, la.income,
                   la.employment_type, la.loan_amount, la.annual_interest_rate,
                   la.tenure_months, la.emi_amount, la.total_interest, la.total_payable,
                   la.loan_purpose, la.status, la.created_at
            FROM loan_applications la
            ORDER BY la.created_at DESC
            """
        )
        stats = run_select(
            """
            SELECT
                (SELECT COUNT(*) FROM users) AS total_users,
                (SELECT COUNT(*) FROM loan_applications) AS total_loans,
                (SELECT COUNT(*) FROM loan_applications WHERE status = 'Pending') AS pending_loans,
                (SELECT COUNT(*) FROM loan_applications WHERE status = 'Approved') AS approved_loans,
                (SELECT COUNT(*) FROM loan_applications WHERE status = 'Rejected') AS rejected_loans,
                (SELECT COALESCE(SUM(loan_amount), 0) FROM loan_applications WHERE status = 'Approved') AS approved_amount
            """,
            one=True,
        )
        return render_template("admin_dashboard.html", users=users, loans=loans, stats=stats)
    except mysql.connector.Error as exc:
        flash(f"Database error: {exc}", "danger")
        return render_template("admin_dashboard.html", users=[], loans=[], stats={})


@app.route("/admin/loan/<int:loan_id>/status", methods=["POST"])
@admin_required
def update_loan_status(loan_id: int):
    action = request.form.get("action", "").lower()
    status_map = {"approve": "Approved", "reject": "Rejected"}

    if action not in status_map:
        flash("Invalid action.", "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        _, count = run_modify(
            "UPDATE loan_applications SET status = %s WHERE id = %s",
            (status_map[action], loan_id),
        )
        if count == 0:
            flash("Loan application not found.", "warning")
        else:
            flash(f"Loan status updated to {status_map[action]}.", "success")
    except mysql.connector.Error as exc:
        flash(f"Database error: {exc}", "danger")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/loan/<int:loan_id>/delete", methods=["POST"])
@admin_required
def delete_loan(loan_id: int):
    try:
        _, count = run_modify("DELETE FROM loan_applications WHERE id = %s", (loan_id,))
        if count == 0:
            flash("Loan application not found.", "warning")
        else:
            flash("Loan application deleted.", "info")
    except mysql.connector.Error as exc:
        flash(f"Database error: {exc}", "danger")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Admin logged out.", "info")
    return redirect(url_for("admin_login"))


@app.route("/api/loans", methods=["GET"])
@login_required
def api_user_loans():
    try:
        loans = run_select(
            "SELECT * FROM loan_applications WHERE user_id = %s ORDER BY created_at DESC",
            (session["user_id"],),
        )
        return jsonify({"success": True, "data": [serialize_loan(loan) for loan in loans]})
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def api_admin_stats():
    try:
        stats = run_select(
            """
            SELECT
                (SELECT COUNT(*) FROM users) AS total_users,
                (SELECT COUNT(*) FROM loan_applications) AS total_loans,
                (SELECT COUNT(*) FROM loan_applications WHERE status = 'Pending') AS pending_loans,
                (SELECT COUNT(*) FROM loan_applications WHERE status = 'Approved') AS approved_loans,
                (SELECT COUNT(*) FROM loan_applications WHERE status = 'Rejected') AS rejected_loans
            """,
            one=True,
        )
        return jsonify({"success": True, "data": stats})
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.errorhandler(404)
def page_not_found(_):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_):
    return render_template("500.html"), 500


if __name__ == "__main__":
    seed_default_admin()
    app.run(debug=True)
