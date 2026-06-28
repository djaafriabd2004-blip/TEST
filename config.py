import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    try:
        ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    except ValueError:
        print("Warning: ADMIN_IDS contains invalid integers in .env")

def _default_db_path() -> str:
    # Railway: persist SQLite on the attached volume (app dir is often read-only)
    volume_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    if volume_mount:
        return os.path.join(volume_mount, "store.db")
    return "store.db"


DB_NAME = os.path.abspath(os.getenv("DB_NAME", _default_db_path()))
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
