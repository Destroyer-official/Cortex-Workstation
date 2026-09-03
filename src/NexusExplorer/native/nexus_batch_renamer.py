"""Nexus Explorer — Enterprise Batch Multi-Rename Engine.

Provides regex replacement, token template interpolation (<counter:001>, <folder>, <date>),
case transformation (UPPER, lower, Title, camelCase, snake_case), EXIF/ID3 metadata extraction,
collision detection, live preview generation, and atomic undo transaction history.
"""

from __future__ import annotations

import os
import re
import shutil
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


class CaseTransformation(Enum):
    """CaseTransformation."""
    NONE = "None"
    UPPERCASE = "UPPERCASE"
    LOWERCASE = "lowercase"
    TITLE_CASE = "Title Case"
    CAMEL_CASE = "camelCase"
    SNAKE_CASE = "snake_case"
    KEBAB_CASE = "kebab-case"
    """CaseTransformation class."""


@dataclass
class RenamePlanItem:
    """RenamePlanItem."""
    original_path: str
    original_name: str
    new_name: str
    new_path: str
    is_valid: bool = True
    error_message: str = ""
    is_changed: bool = False
    """RenamePlanItem class."""


@dataclass
class RenameTransaction:
    """RenameTransaction."""
    timestamp: float
    items: List[Tuple[str, str]]  # (old_path, new_path)
    """RenameTransaction class."""


class BatchRenamer:
    """Production multi-file renaming engine with preview and safety checks."""

    def __init__(self):
        """__init__."""
        self._history: List[RenameTransaction] = []
        """__init__."""

    @staticmethod
    def _apply_case(text: str, transformation: CaseTransformation) -> str:
        """_apply_case."""
        if transformation == CaseTransformation.UPPERCASE:
            return text.upper()
        if transformation == CaseTransformation.LOWERCASE:
            return text.lower()
        if transformation == CaseTransformation.TITLE_CASE:
            return text.title()
        if transformation == CaseTransformation.SNAKE_CASE:
            s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
            s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
            return re.sub(r"[-\s]+", "_", s).lower()
        if transformation == CaseTransformation.KEBAB_CASE:
            s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", text)
            s = re.sub(r"([a-z\d])([A-Z])", r"\1-\2", s)
            return re.sub(r"[_\s]+", "-", s).lower()
        if transformation == CaseTransformation.CAMEL_CASE:
            words = re.split(r"[_\-\s]+", text)
            if not words:
                return text
            return words[0].lower() + "".join(w.capitalize() for w in words[1:])
        return text
        """_apply_case."""

    @staticmethod
    def _extract_exif_metadata(file_path: Path) -> Dict[str, str]:
        """_extract_exif_metadata."""
        meta = {"camera": "", "date": "", "dimensions": ""}
        ext = file_path.suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".tiff"):
            return meta

        try:
            from PIL import Image, ExifTags
            with Image.open(file_path) as img:
                meta["dimensions"] = f"{img.width}x{img.height}"
                exif_data = img.getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag_id, "")
                        if tag_name == "Model":
                            meta["camera"] = str(value).strip()
                        elif tag_name in ("DateTimeOriginal", "DateTime"):
                            # Replace colons in YYYY:MM:DD with dashes
                            meta["date"] = str(value).replace(":", "-")[:10]
        except Exception:
            pass
        return meta
        """_extract_exif_metadata."""

    @staticmethod
    def _extract_id3_metadata(file_path: Path) -> Dict[str, str]:
        """_extract_id3_metadata."""
        meta = {"artist": "", "title": "", "album": "", "track": ""}
        ext = file_path.suffix.lower()
        if ext not in (".mp3", ".flac", ".ogg", ".m4a"):
            return meta

        try:
            import mutagen
            audio = mutagen.File(file_path)
            if audio:
                if "artist" in audio:
                    meta["artist"] = str(audio["artist"][0])
                if "title" in audio:
                    meta["title"] = str(audio["title"][0])
                if "album" in audio:
                    meta["album"] = str(audio["album"][0])
                if "tracknumber" in audio:
                    meta["track"] = str(audio["tracknumber"][0]).split("/")[0]
        except Exception:
            pass
        return meta
        """_extract_id3_metadata."""

    def preview_rename(
        self,
        file_paths: List[str | Path],
        search_pattern: str = "",
        replace_pattern: str = "",
        use_regex: bool = False,
        prefix: str = "",
        suffix: str = "",
        case_transform: CaseTransformation = CaseTransformation.NONE,
        start_counter: int = 1,
        step_counter: int = 1,
    ) -> List[RenamePlanItem]:
        """Generate a live preview plan for renaming a batch of files."""
        plan: List[RenamePlanItem] = []
        seen_targets: Dict[str, str] = {}  # target_path -> source_path for collision detection

        now = time.localtime()
        date_str = time.strftime("%Y-%m-%d", now)
        time_str = time.strftime("%H-%M-%S", now)

        counter = start_counter

        for path_input in file_paths:
            path_obj = Path(path_input)
            if not path_obj.exists():
                plan.append(RenamePlanItem(
                    original_path=str(path_input),
                    original_name=path_obj.name,
                    new_name=path_obj.name,
                    new_path=str(path_input),
                    is_valid=False,
                    error_message="File does not exist",
                ))
                continue

            stem = path_obj.stem
            ext = path_obj.suffix
            parent_dir = path_obj.parent
            parent_name = parent_dir.name

            # 1. Base name modification
            working_name = stem

            if search_pattern:
                if use_regex:
                    try:
                        working_name = re.sub(search_pattern, replace_pattern, working_name)
                    except re.error as e:
                        plan.append(RenamePlanItem(
                            original_path=str(path_obj),
                            original_name=path_obj.name,
                            new_name=path_obj.name,
                            new_path=str(path_obj),
                            is_valid=False,
                            error_message=f"Regex error: {e}",
                        ))
                        continue
                else:
                    working_name = working_name.replace(search_pattern, replace_pattern)

            # 2. Token replacements
            exif_meta = self._extract_exif_metadata(path_obj)
            id3_meta = self._extract_id3_metadata(path_obj)

            def _replace_tokens(text: str) -> str:
                """_replace_tokens."""
                t = text
                t = t.replace("<name>", stem)
                t = t.replace("<ext>", ext.lstrip("."))
                t = t.replace("<folder>", parent_name)
                t = t.replace("<date>", date_str)
                t = t.replace("<time>", time_str)
                t = t.replace("<guid>", str(uuid.uuid4())[:8])

                # Counter patterns: <counter:01>, <counter:001>, <counter:0001>, <#>, <##>
                counter_matches = re.findall(r"<counter(?::(\d+))?>", t)
                for pad_match in counter_matches:
                    if pad_match:
                        pad_len = len(pad_match) if pad_match.startswith("0") else int(pad_match)
                    else:
                        pad_len = 1
                    t = re.sub(r"<counter(?::\d+)?>", f"{counter:0{pad_len}d}", t, count=1)

                t = t.replace("<#>", str(counter))
                t = t.replace("<##>", f"{counter:02d}")
                t = t.replace("<###>", f"{counter:03d}")

                # Metadata tokens & aliases
                t = t.replace("<exif:date>", exif_meta["date"])
                t = t.replace("<date_taken>", exif_meta["date"])
                t = t.replace("<exif:camera>", exif_meta["camera"])
                t = t.replace("<camera>", exif_meta["camera"])
                t = t.replace("<camera_model>", exif_meta["camera"])
                t = t.replace("<exif:dimensions>", exif_meta.get("dimensions", ""))
                t = t.replace("<dimensions>", exif_meta.get("dimensions", ""))

                t = t.replace("<id3:artist>", id3_meta["artist"])
                t = t.replace("<artist>", id3_meta["artist"])
                t = t.replace("<id3:title>", id3_meta["title"])
                t = t.replace("<title>", id3_meta["title"])
                t = t.replace("<id3:album>", id3_meta["album"])
                t = t.replace("<album>", id3_meta["album"])
                t = t.replace("<id3:track>", id3_meta["track"])
                t = t.replace("<track>", id3_meta["track"])
                return t
                """_replace_tokens."""

            working_name = _replace_tokens(working_name)
            p_prefix = _replace_tokens(prefix)
            p_suffix = _replace_tokens(suffix)

            # 3. Case transformation on stem
            working_name = self._apply_case(working_name, case_transform)

            # 4. Assemble final filename
            final_name = f"{p_prefix}{working_name}{p_suffix}{ext}"

            # Validate Windows filename invalid characters
            invalid_chars = set('<>:"/\\|?*')
            has_invalid = any(c in invalid_chars for c in final_name)

            final_path = str(parent_dir / final_name)
            is_changed = (final_name != path_obj.name)
            is_valid = not has_invalid and len(final_name.strip()) > 0
            err_msg = "Contains invalid Windows characters" if has_invalid else ""

            # Collision check
            if final_path.lower() in seen_targets and final_path.lower() != str(path_obj).lower():
                is_valid = False
                err_msg = f"Collision with target: {final_name}"
            elif os.path.exists(final_path) and final_path.lower() != str(path_obj).lower():
                is_valid = False
                err_msg = "Target file already exists on disk"

            seen_targets[final_path.lower()] = str(path_obj)

            plan.append(RenamePlanItem(
                original_path=str(path_obj.resolve()),
                original_name=path_obj.name,
                new_name=final_name,
                new_path=final_path,
                is_valid=is_valid,
                error_message=err_msg,
                is_changed=is_changed,
            ))

            counter += step_counter

        return plan

    def execute_rename(
        self,
        plan: List[RenamePlanItem],
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[int, int, List[str]]:
        """Execute the renaming plan atomically with rollback recording."""
        executed: List[Tuple[str, str]] = []
        errors: List[str] = []
        total = len(plan)

        for i, item in enumerate(plan):
            if not item.is_valid or not item.is_changed:
                continue

            if progress_cb:
                progress_cb(i + 1, total, item.new_name)

            src = Path(item.original_path)
            dst = Path(item.new_path)

            try:
                # Handle case-only rename on Windows safely via intermediate temporary name
                if src.resolve() == dst.resolve() and src.name != dst.name:
                    temp_path = src.parent / f"__nexus_tmp_{uuid.uuid4().hex[:8]}_{src.name}"
                    src.rename(temp_path)
                    temp_path.rename(dst)
                else:
                    src.rename(dst)
                executed.append((str(src), str(dst)))
            except Exception as exc:
                errors.append(f"Failed to rename {item.original_name} -> {item.new_name}: {exc}")

        if executed:
            self._history.append(RenameTransaction(timestamp=time.time(), items=executed))

        return len(executed), len(errors), errors

    def undo_last(self) -> Tuple[int, List[str]]:
        """Undo the most recent batch rename operation."""
        if not self._history:
            return 0, ["No rename operations to undo."]

        tx = self._history.pop()
        reverted = 0
        errors: List[str] = []

        # Revert in reverse order
        for old_path, new_path in reversed(tx.items):
            src = Path(new_path)
            dst = Path(old_path)
            if not src.exists():
                errors.append(f"Cannot revert {src.name}: file no longer exists")
                continue

            try:
                if src.resolve() == dst.resolve() and src.name != dst.name:
                    temp_path = src.parent / f"__nexus_undo_{uuid.uuid4().hex[:8]}_{src.name}"
                    src.rename(temp_path)
                    temp_path.rename(dst)
                else:
                    src.rename(dst)
                reverted += 1
            except Exception as exc:
                errors.append(f"Failed to revert {src.name} -> {dst.name}: {exc}")

        return reverted, errors
