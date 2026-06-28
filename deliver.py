import sqlite3
import os
import json
import urllib.request

token = os.getenv('BOT_TOKEN')
db = '/data/store.db' if os.path.exists('/data/store.db') else 'store.db'
if not os.path.exists(db):
    # Try finding any store.db
    import glob
    dbs = glob.glob('**/*.db', recursive=True)
    if dbs:
        db = dbs[0]

print(f"Connecting to database: {db}")
conn = sqlite3.connect(db)
rows = conn.execute('SELECT stock_data FROM orders WHERE user_id=8596636011 ORDER BY id DESC LIMIT 37').fetchall()
links = [r[0] for r in rows][::-1]

if not links:
    print("No items found for user 8596636011!")
else:
    print(f"Found {len(links)} items. Preparing delivery...")
    chunks = [links[i:i+15] for i in range(0, len(links), 15)]

    for idx, chunk in enumerate(chunks):
        header = "🎉 *Order Delivery & Apology (37 Items)*\n\nDear valued customer, we sincerely apologize for the temporary technical glitch during automated delivery. Here are all 37 of your requested links:\n\n" if idx == 0 else "📦 *Remaining Items (Continued):*\n\n"
        body = "\n\n".join([f"{idx*15 + i + 1}. {link}" for i, link in enumerate(chunk)])
        text = header + body
        
        payload = json.dumps({
            'chat_id': 8596636011,
            'text': text,
            'parse_mode': 'Markdown'
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={'Content-Type': 'application/json'}
        )
        try:
            urllib.request.urlopen(req)
            print(f"Sent chunk {idx+1}/{len(chunks)} successfully.")
        except Exception as e:
            print(f"Error sending chunk {idx+1}: {e}")

    print("Done sending 37 links with English apology.")
