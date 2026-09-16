import os
import sys
import shutil
import hashlib
import re
import zipfile

# Secret key matching config.py exactly
_LICENSE_SECRET = "8f4c2e6b7d1a5c9f0b3e6d8a2c7f4b5d6e9f1a2b3c4d5e6f7a8b9c0d1e2f3a4b"

def generate_license_key(bot_token: str, expiry: str = "never") -> str:
    raw = _LICENSE_SECRET + ":" + bot_token.strip() + ":" + expiry.strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def create_customer_package(customer_name: str, bot_token: str, expiry: str = "never", admin_id: str = ""):
    src_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(src_dir, "dist")
    customers_dir = os.path.join(src_dir, "customers")
    
    if not os.path.exists(dist_dir):
        print("[ERROR] Muld 'dist' not found! Please run build_cython_bot.py first to compile binaries.")
        return False

    # Clean customer folder name (remove special characters)
    clean_name = re.sub(r'[^\w\-]', '_', customer_name.strip())
    if not clean_name:
        clean_name = "client"

    customer_folder = os.path.join(customers_dir, clean_name)
    os.makedirs(customers_dir, exist_ok=True)
    
    import stat
    def remove_readonly(func, path, exc_info):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    def ignore_files(d, files):
        to_ignore = []
        for f in ['.git', 'customers', 'customer_encryptor.cpython-312-x86_64-linux-gnu.so', 'customer_encryptor.py', 'compiled_bot.zip', 'customer_bot.zip']:
            if f in files:
                to_ignore.append(f)
        return to_ignore

    if os.path.exists(customer_folder):
        print(f"\n[1/4] Updating compiled binaries in existing folder (preserving .git) for: {clean_name}...")
        for item in os.listdir(customer_folder):
            if item == ".git":
                continue
            item_path = os.path.join(customer_folder, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, onerror=remove_readonly)
            else:
                try:
                    os.chmod(item_path, stat.S_IWRITE)
                except Exception:
                    pass
                os.remove(item_path)
        shutil.copytree(dist_dir, customer_folder, dirs_exist_ok=True, ignore=ignore_files)
    else:
        print(f"\n[1/4] Copying compiled binaries from 'dist' for customer: {clean_name}...")
        shutil.copytree(dist_dir, customer_folder, ignore=ignore_files)

    # 2. Generate license key
    license_key = generate_license_key(bot_token, expiry)

    # 3. Generate pre-configured .env
    env_content = f"""# ==========================================
# Pre-configured Environment for Customer: {clean_name}
# ==========================================
BOT_TOKEN={bot_token.strip()}
ADMIN_IDS={admin_id.strip()}
DB_NAME=store.db

# ==========================================
# License Security Keys
# ==========================================
LICENSE_KEY={license_key}
LICENSE_EXPIRY={expiry.strip()}

# ==========================================
# Binance API Keys (Optional)
# ==========================================
BINANCE_API_KEY=
BINANCE_SECRET_KEY=
"""
    env_path = os.path.join(customer_folder, ".env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    print(f"[2/4] Generated pre-configured .env for token {bot_token[:12]}...")

    # 4. Create ZIP archive
    zip_filename = f"customer_{clean_name}_bot"
    zip_output_path = os.path.join(customers_dir, zip_filename)
    shutil.make_archive(zip_output_path, 'zip', customer_folder)
    final_zip = zip_output_path + ".zip"
    
    # Also update root customer_bot.zip for convenient access
    root_zip = os.path.join(src_dir, "customer_bot.zip")
    shutil.copy2(final_zip, root_zip)
    print(f"[3/4] Package compressed to: {final_zip}")
    print(f"[4/4] Copied to root customer archive: {root_zip}")

    print("\n" + "=" * 60)
    print(f"  CUSTOMER ENCRYPTION PACKAGE READY: {clean_name}")
    print("=" * 60)
    print(f"Customer Name : {clean_name}")
    print(f"Bot Token     : {bot_token}")
    print(f"License Key   : {license_key}")
    print(f"Expiry Date   : {expiry}")
    print(f"Zip File Path : {final_zip}")
    print("=" * 60 + "\n")
    return True

def main():
    print("====================================================")
    print("      Customer Encrypted Bot Generator")
    print("====================================================\n")
    
    if len(sys.argv) >= 3:
        customer_name = sys.argv[1]
        bot_token = sys.argv[2]
        expiry = sys.argv[3] if len(sys.argv) > 3 else "never"
        admin_id = sys.argv[4] if len(sys.argv) > 4 else ""
    else:
        customer_name = input("[INPUT] Enter Customer Name (اسم الزبون): ").strip()
        if not customer_name:
            print("[ERROR] Customer name cannot be empty!")
            sys.exit(1)
            
        bot_token = input("[INPUT] Enter Buyer's Telegram BOT_TOKEN: ").strip()
        if not bot_token:
            print("[ERROR] Bot Token cannot be empty!")
            sys.exit(1)
            
        expiry = input("[INPUT] Expiry Date (YYYY-MM-DD, press Enter = never): ").strip()
        if not expiry:
            expiry = "never"
            
        admin_id = input("[INPUT] Admin Telegram ID (press Enter to skip): ").strip()

    create_customer_package(customer_name, bot_token, expiry, admin_id)

if __name__ == "__main__":
    main()
