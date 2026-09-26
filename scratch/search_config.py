import re

with open(r"d:\bot store\extracted_temp\database.c", "r", encoding="utf-8", errors="ignore") as f:
    for idx, line in enumerate(f, 1):
        if re.search(r'\bconfig\b', line, re.IGNORECASE):
            # Print matching lines, but exclude comment blocks if they are too long
            if len(line.strip()) < 200:
                print(f"Line {idx}: {line.strip()}")
            else:
                print(f"Line {idx}: (long line) {line.strip()[:200]}...")
