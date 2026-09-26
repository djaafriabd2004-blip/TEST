import re

with open(r"d:\bot store\extracted_temp\cryptobot_client.c", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

match = re.search(r'const char\* const bytes = "(.*?)";', content, re.DOTALL)
if match:
    raw = match.group(1)
    clean_bytes = raw.encode('ascii').decode('unicode_escape').encode('latin1')
    strings = clean_bytes.split(b'\x00')
    print(f"Total strings in cryptobot_client.c: {len(strings)}")
    for idx, s in enumerate(strings):
        if s == b'config':
            print(f"EXACT MATCH Index {idx}: {s!r}")
