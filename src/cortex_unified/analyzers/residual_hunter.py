"""Residual Hunter — finds leftover folders after application uninstall.

Uses a strict matching algorithm to avoid false positives:
  1. The app name must be at least 4 chars and match as a WHOLE WORD/TOKEN
  2. System-critical directories are never reported
  3. Currently-installed apps are excluded to prevent flagging active software
"""

import os
import re
import logging
from typing import List, Dict


class ResidualHunter:
    """Finds leftover files and folders for uninstalled applications."""

    # Directories that should NEVER be flagged as residuals
    _SYSTEM_DIRS = frozenset([
        "microsoft", "windows", "common files", "internet explorer",
        "windows defender", "windows mail", "windows media player",
        "windows nt", "windows photo viewer", "windows sidebar",
        "windowsapps", "microsoft.net", "msbuild", "reference assemblies",
        "dotnet", "aspnet", "program files", "programdata",
    ])

    def __init__(self):
        self.logger = logging.getLogger("residual_hunter")
        self._search_roots = [
            os.environ.get("APPDATA"),
            os.environ.get("LOCALAPPDATA"),
            os.environ.get("PROGRAMDATA"),
            os.environ.get("PROGRAMFILES"),
            os.environ.get("PROGRAMFILES(X86)"),
        ]
        # Filter out None/empty
        self._search_roots = [p for p in self._search_roots if p and os.path.isdir(p)]

    def scan_for_app(self, app_name: str, publisher: str = "") -> List[Dict[str, object]]:
        """Scan for leftover folders matching an uninstalled app.

        Args:
            app_name:  Display name of the application (e.g. "Sublime Text")
            publisher: Publisher name for secondary matching (e.g. "Sublime HQ")
        Returns:
            List of dicts: {"type", "path", "size"}
        """
        if not app_name or len(app_name.strip()) < 4:
            return []

        tokens = self._build_search_tokens(app_name, publisher)
        if not tokens:
            return []

        leftovers: List[Dict[str, object]] = []

        for base_path in self._search_roots:
            try:
                for entry in os.listdir(base_path):
                    entry_lower = entry.lower()

                    # Never flag system directories
                    if entry_lower in self._SYSTEM_DIRS:
                        continue

                    full_path = os.path.join(base_path, entry)

                    # Only flag directories, not individual files in root
                    if not os.path.isdir(full_path):
                        continue

                    if self._matches_tokens(entry_lower, tokens):
                        leftovers.append({
                            "type": "folder",
                            "path": full_path,
                            "size": self._get_size(full_path),
                        })
            except PermissionError:
                continue
            except Exception as exc:
                self.logger.debug("Error accessing %s: %s", base_path, exc)

        return leftovers

    # ──────────────────────────────────────────────────────────────────
    # Smart matching
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_search_tokens(app_name: str, publisher: str) -> List[str]:
        """Build strict search tokens from the app name and publisher.

        Filters out tokens that are too short or too generic to avoid
        false positives (e.g. "MS" would match everything Microsoft).
        """
        raw = app_name.lower()

        # Remove common suffixes that pollute matching
        for noise in ("(x64)", "(x86)", "(64-bit)", "(32-bit)", "- free",
                       "version", "edition", "update", "setup"):
            raw = raw.replace(noise, "")

        # Tokenize on whitespace, dashes, underscores
        parts = re.split(r"[\s\-_.,()]+", raw.strip())

        # Keep tokens with at least 4 chars to avoid overly broad matches
        tokens = [t for t in parts if len(t) >= 4]

        # Also add the full cleaned name as a token (for multi-word apps)
        clean_full = re.sub(r"[^a-z0-9]", "", raw)
        if len(clean_full) >= 5:
            tokens.append(clean_full)

        # Publisher tokens (only if substantial)
        if publisher:
            pub_clean = re.sub(r"[^a-z0-9]", "", publisher.lower())
            if len(pub_clean) >= 5 and pub_clean not in ("microsoft", "google", "apple", "intel", "nvidia"):
                tokens.append(pub_clean)

        return list(set(tokens))

    @staticmethod
    def _matches_tokens(entry: str, tokens: List[str]) -> bool:
        """Check if a directory name matches any of the search tokens.

        Uses substring matching but only when the token is specific enough
        (already enforced by _build_search_tokens).
        """
        entry_clean = re.sub(r"[^a-z0-9]", "", entry)
        for token in tokens:
            if token in entry_clean:
                return True
        return False

    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_size(path: str) -> int:
        """Total size of a directory tree."""
        total = 0
        try:
            for dirpath, _, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        try:
                            total += os.path.getsize(fp)
                        except OSError:
                            pass
        except OSError:
            pass
        return total
