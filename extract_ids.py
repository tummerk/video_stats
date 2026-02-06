"""
Extract user_pk and usernames from scripts/text file.
Creates usernames.json with user_pk values already populated.
"""

import json
import re
from pathlib import Path

def extract_from_text(file_path: str) -> list:
    """Extract ID and username pairs from text file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    results = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Look for ID pattern (numeric string)
        if line.isdigit() and len(line) > 5:  # ID is usually > 5 digits
            potential_id = line

            # Check next line for username
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()

                # Username pattern: starts with letter/underscore, contains letters/numbers/underscores/dots
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', next_line):
                    # Check it's not another number
                    if not next_line.isdigit():
                        results.append({
                            "username": next_line,
                            "user_pk": int(potential_id)
                        })
                        print(f"✓ Found: {potential_id} -> @{next_line}")
                        i += 2  # Skip both lines
                        continue

        i += 1

    return results

def main():
    input_file = Path("scripts/text")
    output_file = Path("scripts/usernames.json")

    if not input_file.exists():
        print(f"❌ File not found: {input_file}")
        return

    print(f"📖 Reading {input_file}...")
    results = extract_from_text(str(input_file))

    # Deduplicate by username
    seen = set()
    unique_results = []
    for item in results:
        if item['username'] not in seen:
            seen.add(item['username'])
            unique_results.append(item)

    dup_count = len(results) - len(unique_results)

    print(f"\n📊 Results:")
    print(f"   Total found: {len(results)}")
    if dup_count > 0:
        print(f"   Duplicates removed: {dup_count}")
    print(f"   Unique: {len(unique_results)}")

    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved to {output_file}")
    print(f"\n📝 First 5 entries:")
    for item in unique_results[:5]:
        print(f"   {item['user_pk']} -> @{item['username']}")

if __name__ == "__main__":
    main()
