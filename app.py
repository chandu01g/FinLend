import re
from functools import wraps
from typing import Any, Dict, List

import mysql.connector
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config["SECRET_KEY"]


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


def valid_email(email: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email))


def valid_phone(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    return 10 <= len(digits) <= 15


def check_eligibility(income: float, loan_amount: float) -> bool:
    """
    Simple eligibility rule:
    - Minimum monthly income: 15,000
    - Maximum loan: 20x monthly income
    """
    return income >= 15000 and loan_amount <= (income * 20)


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
    item["income"] = float(item["income"])
    item["loan_amount"] = float(item["loan_amount"])
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


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
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
            SELECT id, income, employment_type, loan_amount, loan_purpose, status, created_at, updated_at
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
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        income_raw = request.form.get("income", "").strip()
        employment_type = request.form.get("employment_type", "").strip()
        loan_amount_raw = request.form.get("loan_amount", "").strip()
        loan_purpose = request.form.get("loan_purpose", "").strip()

        if not all(
            [full_name, email, phone, address, income_raw, employment_type, loan_amount_raw, loan_purpose]
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
        except ValueError:
            flash("Income and loan amount must be numbers.", "danger")
            return render_template("apply_loan.html", user=user)

        if income <= 0 or loan_amount <= 0:
            flash("Income and loan amount must be greater than 0.", "danger")
            return render_template("apply_loan.html", user=user)
        if len(loan_purpose) < 5:
            flash("Loan purpose must be at least 5 characters.", "danger")
            return render_template("apply_loan.html", user=user)
        if not check_eligibility(income, loan_amount):
            flash("You are currently not eligible for this loan amount.", "warning")
            return render_template("apply_loan.html", user=user)

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
                (user_id, full_name, email, phone, address, income, employment_type, loan_amount, loan_purpose, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
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
                    loan_purpose,
                ),
            )
            flash("Loan application submitted successfully. Status: Pending", "success")
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
                   la.employment_type, la.loan_amount, la.loan_purpose, la.status, la.created_at
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
