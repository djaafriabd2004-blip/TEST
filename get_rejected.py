import sqlite3
import os

db = '/data/store.db' if os.path.exists('/data/store.db') else 'store.db'
if not os.path.exists(db):
    print("Database file not found!")
    exit(0)

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
    SELECT p.id, p.user_id, p.amount, p.payment_method, p.status, p.created_at, u.first_name, u.username 
    FROM payments p 
    LEFT JOIN users u ON p.user_id = u.user_id 
    WHERE p.status = 'rejected' 
    ORDER BY p.id DESC;
""")
rows = c.fetchall()

print(f"\n--- Total Rejected Payments: {len(rows)} ---\n" + "="*50)
if not rows:
    print("No rejected payments found in database.")
else:
    for r in rows:
        fn = r['first_name'] or 'N/A'
        un = f"@{r['username']}" if r['username'] else 'No Username'
        amt = r['amount'] if r['amount'] is not None else 0.0
        print(f"Payment ID: {r['id']} | User: {fn} ({un}) [{r['user_id']}]")
        print(f"Amount: ${amt:.2f} USD | Method/TxID: {r['payment_method']}")
        print(f"Date: {r['created_at']}\n" + "-"*50)

conn.close()
