import os
import re

dist = r"d:\bot store\dist"

for root, dirs, files in os.walk(dist):
    for f in files:
        if f.endswith(".so"):
            path = os.path.join(root, f)
            with open(path, "rb") as fp:
                data = fp.read()
                # find standalone 'config' byte sequences
                matches = re.findall(rb'(?<![a-zA-Z0-9_])config(?![a-zA-Z0-9_])', data)
                if matches:
                    print(f"Standalone 'config' match ({len(matches)}) in: {os.path.relpath(path, dist)}")
