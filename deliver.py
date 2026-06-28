import os
import json
import sqlite3
import urllib.request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN environment variable not found.")
        return

    possible_dbs = ['/data/store.db', 'store.db']
    db_path = None
    for path in possible_dbs:
        if os.path.exists(path):
            db_path = path
            break
            
    if not db_path:
        import glob
        dbs = glob.glob('*.db') + glob.glob('/**/*.db', recursive=True)
        if dbs:
            db_path = dbs[0]

    if not db_path:
        logger.error("No database file found.")
        return

    logger.info(f"Using database: {db_path}")
    conn = sqlite3.connect(db_path)
    
    target_user_id = 8596636011
    rows = conn.execute(
        "SELECT stock_data FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 37",
        (target_user_id,)
    ).fetchall()
    
    if not rows:
        logger.error(f"No orders found for user {target_user_id}")
        return

    links = [r[0] for r in rows][::-1]
    logger.info(f"Retrieved {len(links)} links for user {target_user_id}")

    chunks = [links[i:i+15] for i in range(0, len(links), 15)]

    for idx, chunk in enumerate(chunks):
        if idx == 0:
            text = (
                "🎉 *Order Delivery & Apology (37 Items)*\n\n"
                "Dear valued customer, we sincerely apologize for the temporary technical glitch during automated delivery. Here are all 37 of your requested links:\n\n"
            )
        else:
            text = "📦 *Remaining Items (Continued):*\n\n"

        formatted_items = "\n\n".join([f"{idx*15 + i + 1}. {link}" for i, link in enumerate(chunk)])
        full_message = text + formatted_items

        payload = {
            "chat_id": target_user_id,
            "text": full_message,
            "parse_mode": "Markdown"
        }

        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )

        try:
            with urllib.request.urlopen(req) as resp:
                logger.info(f"Sent chunk {idx+1}/{len(chunks)} successfully.")
        except Exception as e:
            logger.error(f"Failed to send chunk {idx+1}: {e}")

    print("✅ Done sending 37 links with English apology!")

if __name__ == "__main__":
    main()
