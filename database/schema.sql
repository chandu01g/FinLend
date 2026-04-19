CREATE DATABASE IF NOT EXISTS finlend_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE finlend_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    address VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS loan_applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address VARCHAR(255) NOT NULL,
    income DECIMAL(12, 2) NOT NULL,
    employment_type VARCHAR(50) NOT NULL,
    loan_amount DECIMAL(12, 2) NOT NULL,
    annual_interest_rate DECIMAL(5, 2) NOT NULL DEFAULT 10.00,
    tenure_months INT NOT NULL DEFAULT 12,
    emi_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    total_interest DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    total_payable DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    loan_purpose VARCHAR(255) NOT NULL,
    status ENUM('Pending', 'Approved', 'Rejected') NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_loan_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS phone_otps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phone VARCHAR(20) NOT NULL,
    purpose VARCHAR(30) NOT NULL,
    otp_hash VARCHAR(255) NOT NULL,
    attempts INT NOT NULL DEFAULT 0,
    is_verified TINYINT(1) NOT NULL DEFAULT 0,
    expires_at DATETIME NOT NULL,
    verified_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_loan_user_id ON loan_applications(user_id);
CREATE INDEX idx_loan_status ON loan_applications(status);
CREATE INDEX idx_loan_created_at ON loan_applications(created_at);
CREATE INDEX idx_phone_otps_phone_purpose ON phone_otps(phone, purpose);

-- Migration notes for existing installations (run once if you created an older schema):
-- ALTER TABLE loan_applications ADD COLUMN annual_interest_rate DECIMAL(5, 2) NOT NULL DEFAULT 10.00;
-- ALTER TABLE loan_applications ADD COLUMN tenure_months INT NOT NULL DEFAULT 12;
-- ALTER TABLE loan_applications ADD COLUMN emi_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00;
-- ALTER TABLE loan_applications ADD COLUMN total_interest DECIMAL(12, 2) NOT NULL DEFAULT 0.00;
-- ALTER TABLE loan_applications ADD COLUMN total_payable DECIMAL(12, 2) NOT NULL DEFAULT 0.00;
-- CREATE TABLE phone_otps (...same definition as above...);

-- Admin seed note:
-- app.py auto-creates this default admin when admin table is empty:
-- username: admin
-- password: admin123
