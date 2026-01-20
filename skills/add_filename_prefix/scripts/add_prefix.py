import os
import sys

prefix = sys.argv[1]
target_dir = sys.argv[2]

if not os.path.isdir(target_dir):
    print(f"Error: Directory not found: {target_dir}")
    sys.exit(1)

renamed_count = 0

for name in os.listdir(target_dir):
    src = os.path.join(target_dir, name)
    if os.path.isfile(src) and not name.startswith(prefix):
        dst = os.path.join(target_dir, prefix + name)
        os.rename(src, dst)
        print(f"Renamed: {name} -> {prefix + name}")
        renamed_count += 1

print(f"Total renamed: {renamed_count} files")
