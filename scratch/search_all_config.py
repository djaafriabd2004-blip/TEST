import re

with open(r"d:\bot store\extracted_temp\database.c", "r", encoding="utf-8", errors="ignore") as f:
    for idx, line in enumerate(f, 1):
        # Find all occurrences of 'config' (case-insensitive)
        matches = re.finditer(r'config', line, re.IGNORECASE)
        for match in matches:
            start = max(0, match.start() - 15)
            end = min(len(line), match.end() + 15)
            snippet = line[start:end].strip()
            # If the match is NOT part of 'bot_config', print it!
            if 'bot_config' not in snippet.lower():
                print(f"Line {idx}: match='{match.group(0)}' context='{snippet}'")
