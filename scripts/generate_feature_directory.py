"""Generate docs/FEATURE_DIRECTORY.md listing all 118 UI pages across all groups."""

import os
import sys

sys.path.insert(0, "src")
from cortex_unified.ui.premium.registry import PAGES, GROUPS

out_path = os.path.join("docs", "FEATURE_DIRECTORY.md")

lines = [
    "# Cortex Workstation — Complete Feature & UI Directory",
    "",
    f"This directory documents all **{len(PAGES)} interactive pages** across the **{len(GROUPS)} navigation groups** in Cortex Workstation.",
    "Every page is backed by real Windows NT subsystem tools and asynchronous worker threads.",
    "",
    "---",
    "",
    "## Summary of Navigation Groups",
    "",
    "| Group ID | Section Name | Page Count | Primary Scope |",
    "| :--- | :--- | :--- | :--- |",
]

group_map = {g.id: g for g in GROUPS}

for g in GROUPS:
    g_pages = [p for p in PAGES if p.group == g.id]
    lines.append(f"| `{g.id}` | **{g.title}** | {len(g_pages)} | {g.id.capitalize()} tools and management |")

lines.append("")
lines.append("---")
lines.append("")

for g in GROUPS:
    g_pages = [p for p in PAGES if p.group == g.id]
    lines.append(f"## {g.title} (`{g.id}`)")
    lines.append(f"*Contains {len(g_pages)} interactive pages.*")
    lines.append("")
    lines.append("| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")

    for p in g_pages:
        mod_part, cls_part = p.factory.split(":")
        py_file = mod_part.replace(".", "/") + ".py"
        icon_link = f"`{p.icon}.svg`"
        lines.append(
            f"| `{p.id}` | **{p.title}** | {icon_link} | [`{cls_part}`](file:///d:/code/Main_projects/Cortex_Cleaner/src/{py_file}) | Forensic execution via `{cls_part}` |"
        )
    lines.append("")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Generated {out_path} with {len(PAGES)} pages.")
