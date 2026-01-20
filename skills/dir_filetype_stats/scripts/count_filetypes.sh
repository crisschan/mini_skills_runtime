#!/usr/bin/env sh
set -e

dir="$1"

if [ -z "$dir" ]; then
    echo "Usage: count_filetypes.sh <directory>"
    exit 1
fi

if [ ! -d "$dir" ]; then
    echo "Error: Directory not found: $dir"
    exit 1
fi

echo "File type statistics for: $dir"
echo "--------------------------------"
find "$dir" -maxdepth 1 -type f | sed 's/.*\.//' | sort | uniq -c | sort -nr
