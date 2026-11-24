#!/usr/bin/env python3
"""
clean_out_of_stock.py - Script to delete out-of-stock products (Local & Providers)

Usage:
  python clean_out_of_stock.py                 # Deletes all out-of-stock products (asks confirmation)
  python clean_out_of_stock.py --yes           # Deletes immediately without prompt (ideal for Railway console)
  python clean_out_of_stock.py --dry-run       # Preview what will be deleted without making any changes
  python clean_out_of_stock.py --local-only    # Only delete local out-of-stock products
  python clean_out_of_stock.py --providers-only# Only delete provider out-of-stock products
"""

import sys
import asyncio
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clean_oos")

async def main():
    parser = argparse.ArgumentParser(description="Delete out-of-stock products (Local & Providers)")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm deletion without prompting")
    parser.add_argument("--dry-run", action="store_true", help="Preview products that would be deleted without deleting")
    parser.add_argument("--local-only", action="store_true", help="Only delete local products with 0 stock")
    parser.add_argument("--providers-only", action="store_true", help="Only delete provider products with 0 stock")
    args = parser.parse_args()

    from database import (
        db_init,
        get_products,
        get_all_stock_counts,
        delete_product,
        DB_NAME
    )
    import aiosqlite

    await db_init()

    print(f"🔍 Scanning database: {DB_NAME}")
    products = await get_products()
    if not products:
        print("📭 No products found in the database.")
        return

    print(f"📦 Total products found: {len(products)}")

    # Check for active pre-orders to protect user funds
    active_preorder_pids = set()
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT DISTINCT product_id FROM pre_orders;") as cursor:
                rows = await cursor.fetchall()
                active_preorder_pids = {r['product_id'] for r in rows}
    except Exception as e:
        logger.warning(f"Could not check pre-orders: {e}")

    # Fetch live/cached stock counts
    print("⏳ Fetching stock counts (local and providers)...")
    stock_counts = await get_all_stock_counts(products, use_cache=False, force_refresh=True)

    to_delete = []
    skipped_preorders = []

    for p in products:
        p_dict = dict(p)
        pid = p_dict['id']
        name = p_dict.get('name_en') or p_dict.get('name_ar') or f"Product #{pid}"
        is_provider = p_dict.get('provider_id') is not None
        stock = stock_counts.get(pid, 0)

        # Filter by type if requested
        if args.local_only and is_provider:
            continue
        if args.providers_only and not is_provider:
            continue

        if stock <= 0:
            if pid in active_preorder_pids:
                skipped_preorders.append((pid, name, "Provider" if is_provider else "Local"))
                continue
            to_delete.append((pid, name, "Provider" if is_provider else "Local", stock))

    print("\n" + "=" * 60)
    print(f"📊 Scan Results:")
    print(f"  • Total Products Scanned: {len(products)}")
    print(f"  • Out of Stock (To Delete): {len(to_delete)}")
    if skipped_preorders:
        print(f"  • Skipped (Active Pre-orders with User Balance): {len(skipped_preorders)}")
    print("=" * 60)

    if skipped_preorders:
        print("\n⚠️ The following products are out of stock but were SKIPPED because users have active paid pre-orders:")
        for sp_id, sp_name, sp_type in skipped_preorders:
            print(f"   [SKIP] ID: {sp_id:4d} | Type: {sp_type:8s} | Name: {sp_name}")

    if not to_delete:
        print("\n✅ No out-of-stock products to delete!")
        return

    print("\n🗑️ Products marked for deletion (Stock = 0):")
    for pid, name, ptype, stk in to_delete:
        print(f"   [DEL] ID: {pid:4d} | Type: {ptype:8s} | Name: {name}")

    if args.dry_run:
        print("\nℹ️ [DRY RUN] No changes were made. Use without '--dry-run' to execute deletion.")
        return

    # Confirmation prompt if not auto-confirmed
    if not args.yes:
        try:
            confirm = input(f"\n⚠️ Are you sure you want to permanently delete these {len(to_delete)} products? [y/N]: ").strip().lower()
            if confirm not in ("y", "yes"):
                print("❌ Deletion cancelled.")
                return
        except EOFError:
            # Non-interactive environment, require --yes
            print("❌ Non-interactive console detected. Please rerun with '--yes' flag to confirm deletion.")
            return

    print(f"\n🚀 Deleting {len(to_delete)} out-of-stock products...")
    deleted_count = 0
    for pid, name, ptype, stk in to_delete:
        try:
            await delete_product(pid)
            deleted_count += 1
            print(f"  ✅ Deleted ID {pid}: {name}")
        except Exception as e:
            print(f"  ❌ Error deleting ID {pid} ({name}): {e}")

    print(f"\n🎉 Successfully deleted {deleted_count} out-of-stock product(s)!")

if __name__ == "__main__":
    asyncio.run(main())
