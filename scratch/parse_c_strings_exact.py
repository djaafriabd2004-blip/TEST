import re

with open(r"d:\bot store\extracted_temp\crypto_verifier.c", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# find __pyx_string_tab definitions or initialization
matches = re.findall(r'#define __pyx_\w+\s+__pyx_string_tab\[(\d+)\]', content)
print(f"Total string tab defines found: {len(matches)}")

# Let's search for __pyx_string_tab array initialization in C
tab_match = re.search(r'static const char\* const __pyx_string_tab\[\] = \{(.*?)\};', content, re.DOTALL)
if tab_match:
    tab_content = tab_match.group(1)
    items = re.findall(r'"(.*?)"', tab_content)
    print(f"String tab entries count: {len(items)}")
    if len(items) > 155:
        print(f"Entry 155: {items[155]!r}")
    for idx, item in enumerate(items):
        if 'config' in item.lower():
            print(f"Index {idx}: {item!r}")
else:
    print("Could not find __pyx_string_tab array in C source.")
