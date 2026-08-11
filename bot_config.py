import os
import sys
import hashlib
import datetime
from dotenv import load_dotenv

load_dotenv()

# Master Cryptographic Secret Key
_LICENSE_SECRET = "8f4c2e6b7d1a5c9f0b3e6d8a2c7f4b5d6e9f1a2b3c4d5e6f7a8b9c0d1e2f3a4b"

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().replace('"', '').replace("'", "")
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "").strip().replace('"', '').replace("'", "")
if admin_ids_str:
    try:
        ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    except ValueError:
        print("Warning: ADMIN_IDS contains invalid integers in .env")

def _default_db_path():
    volume_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    if volume_mount:
        return os.path.join(volume_mount, "store.db")
    return "store.db"

DB_NAME = os.path.abspath(os.getenv("DB_NAME", _default_db_path()))
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")

# License validation parameters from .env / hosting variables
LICENSE_KEY = os.getenv("LICENSE_KEY", "").strip()
LICENSE_EXPIRY = os.getenv("LICENSE_EXPIRY", "never").strip()

def verify_license():
    """Call this function before starting the bot to validate the license."""
    if not BOT_TOKEN:
        print("CRITICAL: BOT_TOKEN is empty! Please check your configuration.")
        return False
        
    if not LICENSE_KEY:
        print("CRITICAL: LICENSE_KEY is missing! Please contact the developer @abdlwahid4.")
        return False
        
    # Generate expected signature using SHA-256 with secret prefix
    raw_str = _LICENSE_SECRET + ":" + BOT_TOKEN + ":" + LICENSE_EXPIRY
    expected = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
    
    if LICENSE_KEY != expected:
        print("CRITICAL: License verification failed! Unauthorized BOT_TOKEN or invalid LICENSE_KEY.")
        return False
        
    # Check if license has expired
    if LICENSE_EXPIRY != "never":
        try:
            expiry_dt = datetime.datetime.strptime(LICENSE_EXPIRY, "%Y-%m-%d")
            if datetime.datetime.now() > expiry_dt:
                print("CRITICAL: License expired on " + LICENSE_EXPIRY + "! Please contact the developer @abdlwahid4.")
                return False
        except Exception:
            print("CRITICAL: Invalid LICENSE_EXPIRY format! Must be YYYY-MM-DD or never.")
            return False
    return True
