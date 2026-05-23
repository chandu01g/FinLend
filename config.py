import os

from dotenv import load_dotenv

# Ensure .env values override empty/old process environment variables.
load_dotenv(override=True)


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
    OTP_PROVIDER = os.getenv("OTP_PROVIDER", "textlocal").lower()
    OTP_DEBUG_MODE = os.getenv("OTP_DEBUG_MODE", "true").lower() == "true"
    OTP_AUTOFILL_ORIGIN = os.getenv("OTP_AUTOFILL_ORIGIN", "localhost")
    OTP_SMS_TEMPLATE = os.getenv(
        "OTP_SMS_TEMPLATE",
        "Your FinLend OTP is {otp}. Valid for {expiry_minutes} minutes. Do not share this code.",
    )

    # Textlocal SMS provider settings
    TEXTLOCAL_API_URL = os.getenv("TEXTLOCAL_API_URL", "https://api.txtlocal.in/send/")
    TEXTLOCAL_API_KEY = os.getenv("TEXTLOCAL_API_KEY", "")
    TEXTLOCAL_SENDER = os.getenv("TEXTLOCAL_SENDER", "")
    TEXTLOCAL_DLT_TE_ID = os.getenv("TEXTLOCAL_DLT_TE_ID", "")
    TEXTLOCAL_COUNTRY_CODE = os.getenv("TEXTLOCAL_COUNTRY_CODE", "91")
    TEXTLOCAL_TEST_MODE = os.getenv("TEXTLOCAL_TEST_MODE", "false").lower() == "true"

    # Fast2SMS provider settings
    FAST2SMS_API_URL = os.getenv("FAST2SMS_API_URL", "https://www.fast2sms.com/dev/bulkV2")
    FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY", "")
    FAST2SMS_ROUTE = os.getenv("FAST2SMS_ROUTE", "q")
    FAST2SMS_LANGUAGE = os.getenv("FAST2SMS_LANGUAGE", "english")
    FAST2SMS_FLASH = os.getenv("FAST2SMS_FLASH", "0")
    FAST2SMS_SENDER_ID = os.getenv("FAST2SMS_SENDER_ID", "")

    # Twilio Verify settings
    TWILIO_VERIFY_API_URL = os.getenv("TWILIO_VERIFY_API_URL", "https://verify.twilio.com/v2")
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID", "")
    TWILIO_COUNTRY_CODE = os.getenv("TWILIO_COUNTRY_CODE", "91")
