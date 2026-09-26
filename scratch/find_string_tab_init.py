import re

with open(r"d:\bot store\extracted_temp\crypto_verifier.c", "r", encoding="utf-8", errors="ignore") as f:
    for idx, line in enumerate(f, 1):
        if '__pyx_string_tab' in line:
            if len(line.strip()) < 150:
                print(f"Line {idx}: {line.strip()}")
