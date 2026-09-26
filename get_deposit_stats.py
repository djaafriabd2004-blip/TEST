import sqlite3
import os

db = '/data/store.db' if os.path.exists('/data/store.db') else 'store.db'
if not os.path.exists(db):
    print("Database file not found!")
    exit(0)

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 1. Total Completed Deposits
c.execute("SELECT COUNT(*), SUM(amount) FROM payments WHERE status = 'completed';")
row_total = c.fetchone()
total_count = row_total[0] if row_total and row_total[0] else 0
total_amount = row_total[1] if row_total and row_total[1] else 0.0

print("\n" + "="*55)
print("          BOT TOTAL DEPOSIT STATISTICS          ")
print("="*55)
print(f"Total Successful Deposits: {total_count}")
print(f"Total Amount Deposited:   ${total_amount:.2f} USD")
print("="*55)
print("BREAKDOWN BY PAYMENT METHOD:")
print("-" * 55)

# 2. Get breakdown
c.execute("""
    SELECT 
        CASE 
            WHEN payment_method = 'stars' THEN 'Telegram Stars (XTR)'
            WHEN payment_method LIKE 'cryptobot%' THEN 'CryptoBot (@CryptoBot)'
            WHEN payment_method LIKE 'blockchain_USDT%' THEN 'USDT (BEP-20)'
            WHEN payment_method LIKE 'blockchain_LTC%' THEN 'Litecoin (LTC)'
            WHEN payment_method LIKE 'blockchain_TON%' THEN 'TON'
            WHEN payment_method LIKE 'blockchain_BINANCE%' THEN 'Binance Pay / ID'
            ELSE payment_method
        END as method_group,
        COUNT(*) as count,
        SUM(amount) as total_sum
    FROM payments 
    WHERE status = 'completed'
    GROUP BY method_group
    ORDER BY total_sum DESC;
""")

breakdown_rows = c.fetchall()

if not breakdown_rows:
    print("No completed deposits recorded yet.")
else:
    for b in breakdown_rows:
        m_name = b['method_group']
        m_count = b['count']
        m_sum = b['total_sum'] or 0.0
        pct = (m_sum / total_amount * 100) if total_amount > 0 else 0.0
        print(f"* {m_name:<25} | Count: {m_count:<4} | Total: ${m_sum:>8.2f} USD ({pct:.1f}%)")

print("="*55 + "\n")
conn.close()
