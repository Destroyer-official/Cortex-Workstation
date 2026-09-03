"""Deep inspector for placeholders, TODOs, stubs, and mocks across all src/ files."""

import os
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

PATTERNS = [
    r'\bTODO\b',
    r'\bFIXME\b',
    r'\bXXX\b',
    r'\bplaceholder\b',
    r'\bdummy\b',
    r'\bmock\b',
    r'\bstub\b',
    r'raise\s+NotImplementedError',
]

regexes = [re.compile(p, re.IGNORECASE) for p in PATTERNS]

results = []

for root, _, files in os.walk(SRC):
    for f in files:
        if not f.endswith((".py", ".rs", ".js", ".ts", ".html", ".css")):
            continue
        p = Path(root) / f
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            continue
        
        lines = content.splitlines()
        file_findings = []
        for i, line in enumerate(lines, 1):
            for reg in regexes:
                if reg.search(line):
                    file_findings.append({
                        "line_num": i,
                        "line": line.strip(),
                        "match": reg.pattern
                    })
        if file_findings:
            rel = str(p.relative_to(ROOT))
            results.append({
                "file": rel,
                "findings": file_findings
            })

print(f"Scanned src/ - Found {len(results)} files with potential placeholders/notes.")
out_path = ROOT / "scripts" / "placeholder_audit.json"
out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"Saved report to {out_path}")
