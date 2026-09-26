import re

with open(r"d:\bot store\extracted_temp\cryptobot_client.c", "r", encoding="utf-8", errors="ignore") as f:
    for idx, line in enumerate(f, 1):
        if 'config' in line:
            if 'bot_config' not in line and 'cryptobot' not in line and 'Config' not in line and 'configure' not in line:
                print(f"Line {idx}: {line.strip()}")
