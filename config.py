import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")

    # XAMPP MySQL defaults:
    # host: localhost, user: root, password: (empty), port: 3306
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "finlend_db")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))

    # OTP development flags
    OTP_DEBUG_MODE = os.getenv("OTP_DEBUG_MODE", "true").lower() == "true"
    OTP_AUTOFILL_ORIGIN = os.getenv("OTP_AUTOFILL_ORIGIN", "localhost")
