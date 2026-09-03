"""Generate an exhaustive, program-file-by-program-file verification checklist."""

import ast
import os
from pathlib import Path


def parse_file(p: Path):
    """parse_file."""
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content)
        doc = ast.get_docstring(tree) or ""
        first_doc = doc.strip().split("\n")[0] if doc else "Utility/helper module."
        classes = []
        for n in tree.body:
            if isinstance(n, ast.ClassDef):
                methods = [
                    m.name
                    for m in n.body
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not m.name.startswith("__")
                ]
                classes.append((n.name, methods))
        top_funcs = [
            n.name
            for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not n.name.startswith("_")
        ]
        line_count = len(content.splitlines())
        return {
            "doc": first_doc,
            "classes": classes,
            "funcs": top_funcs,
            "lines": line_count,
        }
    except Exception as exc:
        return {"doc": f"Parse error: {exc}", "classes": [], "funcs": [], "lines": 0}


sections = [
    ("System Maintenance & Optimization Tools", ["src/cortex_unified/system_tools"]),
    ("File & Deduplication Analyzers", ["src/cortex_unified/analyzers"]),
    ("Nexus Native Explorer Engine", ["src/NexusExplorer/native"]),
    ("Core Framework & Safety PathGuards", ["src/cortex_unified/core"]),
    ("Processing & Algorithmic Engines", ["src/cortex_unified/engine"]),
    ("Unified Explorer & File Systems", ["src/cortex_unified/explorer"]),
    ("Performance & Hardware Acceleration", ["src/cortex_unified/performance"]),
    (
        "Licensing, Reports, Scheduler & i18n",
        [
            "src/cortex_unified/licensing",
            "src/cortex_unified/reports",
            "src/cortex_unified/scheduler",
            "src/cortex_unified/i18n",
        ],
    ),
    (
        "Accessibility, Visualization & UI Safety",
        [
            "src/cortex_unified/accessibility",
            "src/cortex_unified/visualization",
            "src/cortex_unified/ui/safety",
            "src/cortex_unified/ui/navigation",
            "src/cortex_unified/cli",
            "src/cortex_unified/debug",
        ],
    ),
    ("Premium UI Navigation Shell & Pages", ["src/cortex_unified/ui/premium"]),
    ("Classic UI Tabs & Panels", ["src/cortex_unified/ui/tabs"]),
    ("Diagnostics & Automation Scripts", ["scripts"]),
    ("Root Launchers & Application Entrypoints", ["."]),
]

md_lines = [
    "# Complete Program-File-Wise Inventory & Checklist",
    "",
    "This document provides an exhaustive, **program-file-by-program-file verification checklist** covering every single source file in the repository.",
    "Each entry details the file path, total lines of code, core architectural purpose, defined classes, and key exported methods.",
    "",
]

item_num = 1
total_loc = 0

for sec_title, sec_dirs in sections:
    md_lines.append(f"## {sec_title}")
    md_lines.append("")

    files = []
    for d in sec_dirs:
        p_dir = Path(d)
        if d == ".":
            for f in sorted(p_dir.glob("*.py")):
                files.append(f)
        else:
            for p in sorted(p_dir.rglob("*.py")):
                if "__pycache__" not in str(p) and "tests" not in str(p):
                    files.append(p)

    for f in files:
        rel = f.as_posix()
        info = parse_file(f)
        total_loc += info["lines"]
        abs_path = f.resolve().as_posix()
        md_lines.append(f"- [ ] **{item_num:03d}. [`{rel}`](file:///{abs_path})** ({info['lines']} LOC)")
        md_lines.append(f"  - **Purpose**: {info['doc']}")
        if info["classes"]:
            cls_items = []
            for c_name, m_list in info["classes"][:5]:
                m_str = f" ({len(m_list)} methods: `{'`, `'.join(m_list[:4])}`)" if m_list else ""
                cls_items.append(f"`{c_name}`{m_str}")
            md_lines.append(f"  - **Classes ({len(info['classes'])})**: {', '.join(cls_items)}")
        if info["funcs"]:
            fns_str = ", ".join(f"`{fn}`" for fn in info["funcs"][:8])
            md_lines.append(f"  - **Exported Functions ({len(info['funcs'])})**: {fns_str}")
        md_lines.append("")
        item_num += 1

md_lines.insert(3, f"> **Total Program Files Audited**: {item_num - 1} files | **Total Analyzed Lines of Code**: {total_loc:,} LOC")
md_lines.insert(4, "")

out_path = Path("PROGRAM_FILES_CHECKLIST.md")
out_path.write_text("\n".join(md_lines), encoding="utf-8")
print(f"Generated {item_num - 1} program file items ({total_loc:,} LOC) in PROGRAM_FILES_CHECKLIST.md")
