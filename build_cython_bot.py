import os
import sys
import shutil
import re
import subprocess

def main():
    print("====================================================")
    print("[CYTHON] Telegram Bot Binary Obfuscator & Builder")
    print("====================================================\n")
    
    # No token inputs needed at build time anymore - licensing is checked via signature key in .env at runtime.
    src_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(src_dir, "dist")
    build_temp_dir = os.path.join(src_dir, "build_temp")
    
    # Clean old directories
    if os.path.exists(build_temp_dir):
        shutil.rmtree(build_temp_dir)
    os.makedirs(build_temp_dir)
    
    # Clean dist but preserve .git directory for Railway deployment
    if os.path.exists(dist_dir):
        for item in os.listdir(dist_dir):
            if item == ".git":
                continue
            item_path = os.path.join(dist_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    else:
        os.makedirs(dist_dir)
    
    # Copy all files to build_temp for compilation to avoid modifying originals
    print("[PREPARE] Copying project files for compilation...")
    for f in os.listdir(src_dir):
        src_path = os.path.join(src_dir, f)
        temp_path = os.path.join(build_temp_dir, f)
        
        if f in [".git", "venv", "dist", "build_temp", "extracted_temp", "scratch", "brain", "__pycache__", "store.db", "generate_license.py"]:
            continue
            
        if os.path.isdir(src_path):
            shutil.copytree(src_path, temp_path)
        else:
            shutil.copy(src_path, temp_path)
            
    # Dynamic search for all .py files inside build_temp (including subdirectories)
    files_to_compile = []
    for root, dirs, files in os.walk(build_temp_dir):
        for file in files:
            # Exclude compiler scripts, build tools, and uncompiled configuration/database files from compilation
            if file.endswith(".py") and not file.startswith("build_") and not file.startswith("test_") and not file.startswith("debug_") and file not in ["compile_cython.py", "run.py", "database.py", "bot_config.py"]:
                rel_path = os.path.relpath(os.path.join(root, file), build_temp_dir)
                # Convert backslashes to forward slashes for Cython compatibility
                rel_path = rel_path.replace("\\", "/")
                files_to_compile.append(rel_path)
    print(f"[PREPARE] Found {len(files_to_compile)} Python files to compile.")
            
    # No config injection needed anymore, the core check is natively in root's config.py
        
    # Create the Cython compiler script inside build_temp
    compile_script_content = f"""
import os
import sys
import shutil
from setuptools import setup
from Cython.Build import cythonize

FILES_TO_COMPILE = {repr(files_to_compile)}

setup(
    ext_modules=cythonize(
        FILES_TO_COMPILE,
        compiler_directives={{'language_level': "3"}},
        force=True
    ),
    script_args=["build_ext", "--inplace"]
)
"""
    with open(os.path.join(build_temp_dir, "compile_cython.py"), "w", encoding="utf-8") as f:
        f.write(compile_script_content)
        
    # 3. Execute Docker compilation
    print("[DOCKER] Running compilation in Linux container...")
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{build_temp_dir}:/app_mount",
        "-w", "/app",
        "python:3.12",
        "sh", "-c", "mkdir -p /app && cp -Rp /app_mount/. /app/ && pip install cython setuptools && python compile_cython.py && python -c \"import os, shutil; os.remove('/app_mount/compiled_bot.zip') if os.path.exists('/app_mount/compiled_bot.zip') else None; shutil.make_archive('/app_mount/compiled_bot', 'zip', '/app')\""
    ]
    
    try:
        subprocess.run(docker_cmd, check=True)
        print("[SUCCESS] Cython compilation completed inside Docker.")
    except Exception as e:
        print(f"[ERROR] Docker compilation failed: {e}")
        print("[TIP] Ensure Docker Desktop is running and WSL is integrated.")
        # Cleanup
        shutil.rmtree(build_temp_dir)
        sys.exit(1)
        
    # 4. Extract archive and package files to dist
    print("[PACKAGE] Extracting compiled files archive...")
    extracted_dir = os.path.join(src_dir, "extracted_temp")
    if os.path.exists(extracted_dir):
        shutil.rmtree(extracted_dir)
    os.makedirs(extracted_dir)
    
    zip_path = os.path.join(build_temp_dir, "compiled_bot.zip")
    if not os.path.exists(zip_path):
        print("[ERROR] Compiled archive not found!")
        shutil.rmtree(build_temp_dir)
        shutil.rmtree(extracted_dir)
        sys.exit(1)
        
    shutil.unpack_archive(zip_path, extracted_dir, 'zip')
    
    print("[PACKAGE] Moving compiled files and documents to dist...")
    
    # We need a small launcher "run.py" to run the compiled bot.so
    launcher_content = """# Bot Launcher
import asyncio
import bot

if __name__ == "__main__":
    try:
        asyncio.run(bot.main())
    except (KeyboardInterrupt, SystemExit):
        pass
"""
    with open(os.path.join(dist_dir, "run.py"), "w", encoding="utf-8") as f:
        f.write(launcher_content)
        
    # Copy directories and compiled files to dist
    for f in os.listdir(extracted_dir):
        src_path = os.path.join(extracted_dir, f)
        dist_path = os.path.join(dist_dir, f)
        
        # Skip source files, compilation artifacts, and tools
        skip_files = [
            ".env", ".gitignore", "FEATURES.md", "compile_cython.py",
            "build_cython_bot.py", "build_encrypted_bot.py", "generate_license.py", "compiled_bot.zip", "build"
        ]
        if f in skip_files or f.endswith(".c") or f.endswith(".log") or f.endswith(".zip") or f.endswith(".db"):
            continue
        if f.endswith(".py") and f not in ["database.py", "bot_config.py"]:
            continue
            
        # Skip non-guide text files
        if f.endswith(".txt") and f not in ["requirements.txt", "DEPLOY_GUIDE.txt", "DEPLOY_GUIDE_EN.txt"]:
            continue
            
        if os.path.isdir(src_path):
            # Exclude source code files (.py, .c) when copying handlers/middlewares
            shutil.copytree(src_path, dist_path, ignore=shutil.ignore_patterns('*.py', '*.c'))
        else:
            shutil.copy(src_path, dist_path)
            
    # Generate clean .env template
    env_content = """# ============================
# Bot Configuration
# ============================
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_IDS=YOUR_TELEGRAM_ID_HERE
DB_NAME=store.db

# ============================
# License Security Keys
# ============================
LICENSE_KEY=YOUR_LICENSE_KEY_HERE
LICENSE_EXPIRY=never

# ============================
# Binance API Keys
# ============================
BINANCE_API_KEY=YOUR_BINANCE_API_KEY_HERE
BINANCE_SECRET_KEY=YOUR_BINANCE_SECRET_KEY_HERE
"""
    with open(os.path.join(dist_dir, ".env"), "w", encoding="utf-8") as f:
        f.write(env_content)
        
    # Update DEPLOY guides to specify running the launcher run.py
    for guide in ["DEPLOY_GUIDE.txt", "DEPLOY_GUIDE_EN.txt"]:
        guide_src = os.path.join(extracted_dir, guide)
        guide_dist = os.path.join(dist_dir, guide)
        if os.path.exists(guide_src):
            with open(guide_src, "r", encoding="utf-8") as f:
                content = f.read()
            # Replace python bot.py with python run.py
            content = content.replace("python bot.py", "python run.py")
            content = content.replace("python3 bot.py", "python3 run.py")
            with open(guide_dist, "w", encoding="utf-8") as f:
                f.write(content)
                
    def remove_readonly(func, path, exc_info):
        import stat
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    if os.path.exists(build_temp_dir):
        shutil.rmtree(build_temp_dir, onerror=remove_readonly)
    # if os.path.exists(extracted_dir):
    #     shutil.rmtree(extracted_dir)
    
    print("\n[SUCCESS] Binary Build completed successfully! The protected bot code is in the 'dist' folder.")
    print("[TIP] Instruct the buyer to run the bot using 'python run.py' instead of 'bot.py'.")
    print("[WARNING] The compiled bot will only run on Linux Python 3.12 environments with the licensed BOT_TOKEN.")

if __name__ == "__main__":
    main()
