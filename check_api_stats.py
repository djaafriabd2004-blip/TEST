import os
import sys
import sqlite3
from datetime import datetime

# Ensure utf-8 output in Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import bot_config as config
except ImportError:
    try:
        import config
    except ImportError:
        config = None

def get_db_path():
    if config and hasattr(config, "DB_NAME"):
        return config.DB_NAME
    volume_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    if volume_mount:
        return os.path.join(volume_mount, "store.db")
    return os.getenv("DB_NAME", "store.db")

def print_separator(char="=", length=65):
    print(char * length)

def main():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"❌ لم يتم العثور على قاعدة البيانات في المسار: {db_path}")
        print("تأكد من تشغيل البوت مرة واحدة على الأقل لإنشاء قاعدة البيانات.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print_separator("=")
    print("📊 تقرير إحصائيات طلبات الـ API للبوت (API Statistics Report)")
    print(f"🕒 تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 مسار قاعدة البيانات: {db_path}")
    print_separator("=")

    # 1. External Providers Summary
    cursor.execute("""
        SELECT 
            p.id as provider_id,
            p.base_url,
            p.store_name,
            COUNT(DISTINCT pr.id) as linked_products_count,
            COUNT(o.id) as total_orders,
            COALESCE(SUM(o.price_paid), 0.0) as total_spent
        FROM providers p
        LEFT JOIN products pr ON pr.provider_id = p.id
        LEFT JOIN orders o ON o.product_id = pr.id
        GROUP BY p.id
    """)
    providers = cursor.fetchall()

    print("\n🔌 [1] إحصائيات المزودين الخارجيين (External API Providers):")
    if not providers:
        print("  ⚠️ لا يوجد مزودين مضافين حالياً في قاعدة البيانات.")
    else:
        for p in providers:
            store_name = p['store_name'] or 'بدون اسم'
            print(f"  🔹 المزود #{p['provider_id']} | {p['base_url']}")
            print(f"     • الاسم المستعار: {store_name}")
            print(f"     • عدد المنتجات المربوطة: {p['linked_products_count']}")
            print(f"     • إجمالي الطلبات المنفذة: {p['total_orders']} طلب")
            print(f"     • إجمالي المبيعات/المصروفات: ${p['total_spent']:.2f} USD")
            print("     " + "-" * 50)

    # 2. Total Orders by External API vs Local Stock
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN pr.provider_id IS NOT NULL THEN 1 END) as provider_orders_count,
            COALESCE(SUM(CASE WHEN pr.provider_id IS NOT NULL THEN o.price_paid ELSE 0 END), 0.0) as provider_orders_amount,
            COUNT(CASE WHEN pr.provider_id IS NULL THEN 1 END) as local_orders_count,
            COALESCE(SUM(CASE WHEN pr.provider_id IS NULL THEN o.price_paid ELSE 0 END), 0.0) as local_orders_amount,
            COUNT(o.id) as total_orders_count,
            COALESCE(SUM(o.price_paid), 0.0) as total_orders_amount
        FROM orders o
        LEFT JOIN products pr ON o.product_id = pr.id
    """)
    orders_summary = cursor.fetchone()

    print("\n📦 [2] مقارنة مبيعات الـ API مقابل المخزون المحلي (Sales Breakdown):")
    if orders_summary:
        print(f"  🌐 طلبات المزودين (API Orders): {orders_summary['provider_orders_count']} طلب | ${orders_summary['provider_orders_amount']:.2f} USD")
        print(f"  💾 طلبات المخزون المحلي (Local): {orders_summary['local_orders_count']} طلب | ${orders_summary['local_orders_amount']:.2f} USD")
        print(f"  📈 الإجمالي الكلي: {orders_summary['total_orders_count']} طلب | ${orders_summary['total_orders_amount']:.2f} USD")

    # 3. Client Reseller API Orders (Incoming via our Bot API)
    cursor.execute("""
        SELECT 
            COUNT(*) as client_api_orders_count,
            COALESCE(SUM(price_paid), 0.0) as client_api_orders_amount
        FROM orders
        WHERE client_order_id IS NOT NULL AND client_order_id != ''
    """)
    client_api = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as count FROM api_keys")
    api_keys_count = cursor.fetchone()['count']

    print("\n🤖 [3] طلبات الـ API المستلمة من الموزعين (Incoming Reseller API):")
    print(f"  🔑 عدد مفاتيح الـ API المفعلة للعملاء: {api_keys_count}")
    if client_api:
        print(f"  📥 طلبات الشراء عبر API البوت: {client_api['client_api_orders_count']} طلب | ${client_api['client_api_orders_amount']:.2f} USD")

    # 4. Pre-Orders Status
    cursor.execute("""
        SELECT COUNT(*) as pre_orders_count, COALESCE(SUM(price_paid), 0.0) as pre_orders_amount
        FROM pre_orders
    """)
    pre_orders = cursor.fetchone()
    print("\n⏳ [4] الطلبات المسبقة والمعلقة (Pre-Orders Queue):")
    if pre_orders:
        print(f"  • الطلبات في قائمة الانتظار: {pre_orders['pre_orders_count']} طلب | ${pre_orders['pre_orders_amount']:.2f} USD")

    # 5. Recent 5 API Orders
    cursor.execute("""
        SELECT 
            o.id as order_id,
            o.user_id,
            o.purchased_at,
            o.price_paid,
            o.product_name_ar,
            o.client_order_id,
            p.base_url
        FROM orders o
        JOIN products pr ON o.product_id = pr.id
        LEFT JOIN providers p ON pr.provider_id = p.id
        WHERE pr.provider_id IS NOT NULL OR o.client_order_id IS NOT NULL
        ORDER BY o.id DESC
        LIMIT 5
    """)
    recent_api_orders = cursor.fetchall()

    print("\n🕒 [5] آخر 5 طلبات API منفذة (Latest API Orders):")
    if not recent_api_orders:
        print("  • لا توجد طلبات API سابقة حتى الآن.")
    else:
        for ro in recent_api_orders:
            prov_str = ro['base_url'] if ro['base_url'] else 'Local API Client'
            client_ref = f" | Ref: {ro['client_order_id']}" if ro['client_order_id'] else ""
            print(f"  • طلب #{ro['order_id']} | مستخدم: {ro['user_id']} | منتج: {ro['product_name_ar']}")
            print(f"    المزود: {prov_str}{client_ref} | المبلغ: ${ro['price_paid']:.2f} | الوقت: {ro['purchased_at']}")

    print_separator("=")
    conn.close()

if __name__ == "__main__":
    main()
