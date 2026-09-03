"""Tests for NexusExplorer nested folder, nested file, batch scaffolding, and undo/redo."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure native directory is in sys.path
NATIVE_DIR = Path(__file__).resolve().parent.parent.parent / "native"
if str(NATIVE_DIR) not in sys.path:
    sys.path.insert(0, str(NATIVE_DIR))

from nexus_core import (
    create_nested_folder,
    create_nested_file,
    scaffold_hierarchy,
    FILE_TEMPLATES,
    PROJECT_SCAFFOLD_PRESETS,
)
from nexus_undo import UndoStack, CreateFileEntry, MkdirEntry, BatchCreateEntry


def test_create_nested_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        target, created = create_nested_folder(base, "components/ui/modals")
        
        assert target.is_dir()
        assert target == base / "components" / "ui" / "modals"
        assert len(created) == 3
        assert str(base / "components") in created
        assert str(base / "components" / "ui") in created
        assert str(base / "components" / "ui" / "modals") in created


def test_create_nested_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        content = "export const Button = () => null;"
        target, created = create_nested_file(base, "src/components/Button.tsx", content=content)
        
        assert target.is_file()
        assert target.read_text(encoding="utf-8") == content
        assert str(base / "src") in created
        assert str(base / "src" / "components") in created


def test_scaffold_hierarchy_indented():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        spec = """
app/
  api/
    v1/
      routes.py
  core/
    config.py
  main.py
README.md
"""
        result = scaffold_hierarchy(base, spec)
        assert len(result["errors"]) == 0
        assert (base / "app" / "api" / "v1" / "routes.py").is_file()
        assert (base / "app" / "core" / "config.py").is_file()
        assert (base / "app" / "main.py").is_file()
        assert (base / "README.md").is_file()
        # Verify template python content is applied
        py_content = (base / "app" / "main.py").read_text(encoding="utf-8")
        assert "def main():" in py_content or "Module Description" in py_content


def test_scaffold_hierarchy_path_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        spec = """
src/services/auth.ts
src/types/index.ts
package.json
"""
        result = scaffold_hierarchy(base, spec)
        assert len(result["errors"]) == 0
        assert (base / "src" / "services" / "auth.ts").is_file()
        assert (base / "src" / "types" / "index.ts").is_file()
        assert (base / "package.json").is_file()


def test_scaffold_presets():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        fastapi_preset = PROJECT_SCAFFOLD_PRESETS["FastAPI Microservice"]
        result = scaffold_hierarchy(base, fastapi_preset)
        assert len(result["errors"]) == 0
        assert (base / "app" / "main.py").is_file()
        assert (base / "requirements.txt").is_file()
        assert (base / "app" / "api" / "v1" / "endpoints" / "auth.py").is_file()


def test_undo_redo_create_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        target, created = create_nested_file(base, "deep/folder/structure/script.py", content="print('hello')")
        assert target.is_file()
        
        entry = CreateFileEntry(str(target), content="print('hello')", created_parents=created)
        
        # Undo: deletes file and cleans up empty parents
        entry.undo()
        assert not target.exists()
        assert not (base / "deep" / "folder" / "structure").exists()
        assert not (base / "deep").exists()
        
        # Redo: restores file and parent directories
        entry.redo()
        assert target.is_file()
        assert target.read_text(encoding="utf-8") == "print('hello')"


def test_undo_redo_batch_create():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        spec = "src/a.py\nsrc/b.py"
        res = scaffold_hierarchy(base, spec)
        
        entries = []
        for d in res["created_dirs"]:
            entries.append(MkdirEntry(d))
        for f, c in res["created_files"]:
            entries.append(CreateFileEntry(f, content=c))
            
        batch = BatchCreateEntry(entries, "Test scaffold")
        batch.undo()
        assert not (base / "src" / "a.py").exists()
        assert not (base / "src" / "b.py").exists()
        
        batch.redo()
        assert (base / "src" / "a.py").is_file()
        assert (base / "src" / "b.py").is_file()


@pytest.mark.skipif(os.environ.get("QT_QPA_PLATFORM") != "offscreen" and not sys.platform.startswith("win"), reason="Qt offscreen")
def test_dialogs_construction():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    
    from nexus_explorer import NestedFolderDialog, NestedFileDialog, BatchScaffoldDialog
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        
        dlg_folder = NestedFolderDialog(base)
        dlg_folder.input_path.setText("new/nested/folder")
        assert dlg_folder.get_target_path() == "new/nested/folder"
        
        dlg_file = NestedFileDialog(base)
        dlg_file.input_path.setText("src/utils/math.py")
        path_res, content_res = dlg_file.get_result()
        assert path_res == "src/utils/math.py"
        
        dlg_scaffold = BatchScaffoldDialog(base)
        dlg_scaffold.spec_edit.setPlainText("a/\n  b.txt")
        assert "b.txt" in dlg_scaffold.get_spec_text()
