import re
import bz2

with open(r"d:\bot store\extracted_temp\database.c", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Find cstring definition
# example: const char* const cstring = "...";
match = re.search(r'const char\* const cstring = "(.*?)";', content, re.DOTALL)
if not match:
    print("Could not find cstring in database.c")
    sys.exit(1)

cstring_val = match.group(1)
# Clean up C-style string concat and escapes
# E.g. "abc""def" -> "abcdef"
cstring_val = re.sub(r'"\s*"', '', cstring_val)

# Now decode C escape sequences
# We can do this by converting the string to bytes using latin-1, then parsing C escapes
raw_bytes = cstring_val.encode('latin-1')

# Parse escape sequences:
# \ooo (octal)
# \xHH (hex)
# \a, \b, \f, \n, \r, \t, \v, \\, \?, \', \", \0
# We can write a custom decoder or use a regex to decode octal escapes since they are the main ones here.
# Let's do it byte by byte or using a regex replacement on a bytearray.
res = bytearray()
i = 0
n = len(raw_bytes)
while i < n:
    if raw_bytes[i] == ord('\\'):
        if i + 1 < n:
            next_char = raw_bytes[i+1]
            if ord('0') <= next_char <= ord('7'):
                # Octal escape: up to 3 octal digits
                octal_str = ""
                for j in range(3):
                    if i + 1 + j < n and ord('0') <= raw_bytes[i+1+j] <= ord('7'):
                        octal_str += chr(raw_bytes[i+1+j])
                    else:
                        break
                res.append(int(octal_str, 8))
                i += 1 + len(octal_str)
                continue
            elif next_char == ord('x'):
                # Hex escape: up to 2 hex digits
                hex_str = ""
                for j in range(2):
                    if i + 2 + j < n and chr(raw_bytes[i+2+j]).lower() in '0123456789abcdef':
                        hex_str += chr(raw_bytes[i+2+j])
                    else:
                        break
                res.append(int(hex_str, 16))
                i += 2 + len(hex_str)
                continue
            else:
                simple_escapes = {
                    ord('a'): 7, ord('b'): 8, ord('f'): 12, ord('n'): 10,
                    ord('r'): 13, ord('t'): 9, ord('v'): 11, ord('\\'): ord('\\'),
                    ord('?'): ord('?'), ord("'"): ord("'"), ord('"'): ord('"'), ord('0'): 0
                }
                if next_char in simple_escapes:
                    res.append(simple_escapes[next_char])
                else:
                    res.append(raw_bytes[i])
                    res.append(next_char)
                i += 2
                continue
        else:
            res.append(raw_bytes[i])
            i += 1
    else:
        res.append(raw_bytes[i])
        i += 1

print(f"Decoded bytes length: {len(res)}")

# Now decompress using bz2
decompressed = bz2.decompress(bytes(res))
print(f"Decompressed length: {len(decompressed)}")

# Find index array
# const struct { const unsigned int length: 10; } index[] = ...
# Let's extract the index numbers:
index_match = re.search(r'index\[\] = \{(.*?)\};', content, re.DOTALL)
if not index_match:
    print("Could not find index array in database.c")
    sys.exit(1)

index_content = index_match.group(1)
lengths = [int(x) for x in re.findall(r'(\d+)', index_content)]

# Reconstruct strings
strings = []
offset = 0
for idx, length in enumerate(lengths):
    val = decompressed[offset:offset+length]
    strings.append(val)
    offset += length

print(f"Total strings extracted: {len(strings)}")
print(f"String at index 194: {strings[194]}")
