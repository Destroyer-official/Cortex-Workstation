"""Scanner script to detect placeholders, TODOs, and mock patterns."""

import os
import re
import sys

patterns = {
    'mock_fake_dummy': re.compile(r'\b(mock|dummy|fake|sample_data|placeholder|simulated)\b', re.I),
    'TODO_FIXME': re.compile(r'\b(TODO|FIXME|XXX|HACK)\b'),
    'hardcoded_user_path': re.compile(r'C:\\Users\\', re.I),
    'hardcoded_c_drive': re.compile(r'[\'"]C:[\\/]', re.I),
    'stub_or_notimplemented': re.compile(r'raise NotImplementedError|pass  # stub', re.I),
}

results = {k: [] for k in patterns}
all_py_files = []

for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            all_py_files.append(p)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as file:
                    for line_no, line in enumerate(file, 1):
                        for k, pat in patterns.items():
                            if pat.search(line):
                                results[k].append((p, line_no, line.strip()))
            except Exception as e:
                print(f"Error reading {p}: {e}")

print(f"Total Python files scanned: {len(all_py_files)}")
for k, matches in results.items():
    print(f"\n==========================================")
    print(f"=== Pattern: {k} ({len(matches)} matches) ===")
    print(f"==========================================")
    for p, lno, l in matches[:30]:
        print(f"{p}:{lno} -> {l[:120]}")
    if len(matches) > 30:
        print(f"  ... and {len(matches)-30} more")
