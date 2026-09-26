import re

with open(r"d:\bot store\extracted_temp\crypto_verifier.c", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

match = re.search(r'const char\* const bytes = "(.*?)";', content, re.DOTALL)
if match:
    raw = match.group(1)
    # let's decode C string escapes
    clean_bytes = raw.encode('ascii').decode('unicode_escape').encode('latin1')
    strings = clean_bytes.split(b'\x00')
    print(f"Total strings: {len(strings)}")
    if len(strings) > 155:
        print(f"String 155: {strings[155]!r}")
    for idx, s in enumerate(strings):
        if b'config' in s.lower():
            print(f"Index {idx}: {s!r}")
