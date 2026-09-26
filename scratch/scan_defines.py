import re

with open(r"d:\bot store\extracted_temp\cryptobot_client.c", "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if line.startswith("#define __pyx_"):
            if 'config' in line.lower() and 'bot_config' not in line.lower() and 'cryptobot' not in line.lower():
                print(line.strip())
