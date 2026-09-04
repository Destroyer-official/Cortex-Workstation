"""Diagnostic script to check for hardcoded Windows paths."""

import os
import re
from pathlib import Path

def analyze_paths():
    """analyze_paths.

    Manages analyze paths operations and coordinates related state changes for the component.
    """
    print("=== Analyzing Hardcoded Paths across src/ ===")
    hardcoded_re = re.compile(r'["\'](C:[/\\][^"\']*)["\']', re.I)
    
    findings = []
    for root, dirs, files in os.walk('src'):
        for f in files:
            if f.endswith('.py'):
                p = os.path.join(root, f)
                with open(p, 'r', encoding='utf-8', errors='ignore') as file:
                    for lno, line in enumerate(file, 1):
                        matches = hardcoded_re.findall(line)
                        if matches:
                            # Filter out harmless comments/docs if needed, or inspect all
                            findings.append((p, lno, matches, line.strip()))
                            
    print(f"Total lines with hardcoded C: paths: {len(findings)}")
    for p, lno, matches, line in findings:
        print(f"{p}:{lno} [{', '.join(matches)}] -> {line[:100]}")

if __name__ == '__main__':
    analyze_paths()
