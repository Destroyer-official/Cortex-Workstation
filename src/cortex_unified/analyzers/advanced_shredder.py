"""Advanced multi-pattern overwrite disk sanitization (DoD 5220.22-M style pass sequence).

Passes: zeros, ones, then random cryptographic data -- a robust implementation of the
classic DoD 5220.22-M disk sanitization standard. As with any overwrite scheme this is only
physically meaningful on rotational media; on SSD/NVMe wear-leveling can leave original
blocks recoverable (see ``engine.secure_delete`` for the storage-aware path).

SAFETY: Callers MUST vet every path through
:func:`~cortex_unified.core.security.check_deletion_safety` (or PathGuard)
before invoking it.
"""

import enum
import logging
import os
import random
import stat
from typing import Sequence, Union

from cortex_unified.core.security import check_deletion_safety


class ShredMethod(str, enum.Enum):
    """Sanitization standards for secure data erasure."""

    ZERO = "Zero Fill (1 pass)"
    RANDOM = "Random (1 pass)"
    DOD_5220_22_M = "DoD 5220.22-M (3 passes)"
    DOD_5220_22_M_ECE = "DoD 5220.22-M ECE (7 passes)"
    NIST_800_88 = "NIST SP 800-88 (1 pass)"
    GUTMANN = "Gutmann Algorithm (35 passes)"
    VSITR = "German VSITR (7 passes)"
    SCHNEIER = "Bruce Schneier (7 passes)"


class AdvancedShredder:
    """Overwrites files with certified pass patterns before deletion."""

    # Gutmann 35-pass magnetic transition patterns
    _GUTMANN_PATTERNS = [
        None, None, None, None,  # 1-4: Random
        b"\x55", b"\xAA", b"\x92\x49\x24", b"\x49\x24\x92", b"\x24\x92\x49",  # 5-9
        b"\x00", b"\x11", b"\x22", b"\x33", b"\x44", b"\x55", b"\x66", b"\x77",  # 10-17
        b"\x88", b"\x99", b"\xAA", b"\xBB", b"\xCC", b"\xDD", b"\xEE", b"\xFF",  # 18-25
        b"\x92\x49\x24", b"\x49\x24\x92", b"\x24\x92\x49",  # 26-28
        b"\x6D\xB6\xDB", b"\xB6\xDB\x6D", b"\xDB\x6D\xB6",  # 29-31
        None, None, None, None,  # 32-35: Random
    ]

    _VSITR_PATTERNS = [
        b"\x00", b"\xFF", b"\x00", b"\xFF", b"\x00", b"\xFF", b"\xAA"
    ]

    def __init__(self):
        self.logger = logging.getLogger("advanced_shredder")
        """__init__."""
        """__init__."""

    def _generate_pass_data(self, pattern: bytes | None, size: int) -> bytes:
        """Generate byte pattern for a single chunk."""
        if pattern is None:
            return os.urandom(size)
        repeat_count = (size // len(pattern)) + 1
        return (pattern * repeat_count)[:size]

    def shred_file(
        self,
        file_path: str,
        passes: int | None = None,
        method: Union[ShredMethod, str] = ShredMethod.DOD_5220_22_M,
    ) -> bool:
        """Overwrite *file_path* with the chosen sanitization pattern, then remove it.

        The file is renamed to a random name just before unlinking: on NTFS
        the MFT entry outlives deletion, and a scrambled name prevents
        trivial filename-based recovery tools from re-linking the data.
        """
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return False

        safe, reason = check_deletion_safety(file_path)
        if not safe:
            self.logger.warning("Shred blocked by safety guard: %s (%s)", file_path, reason)
            return False

        # Resolve standard patterns
        patterns: list[bytes | None] = []
        if isinstance(method, str):
            try:
                method = ShredMethod(method)
            except ValueError:
                method = ShredMethod.DOD_5220_22_M

        if method == ShredMethod.ZERO:
            patterns = [b"\x00"]
        elif method == ShredMethod.RANDOM or method == ShredMethod.NIST_800_88:
            patterns = [None]
        elif method == ShredMethod.DOD_5220_22_M:
            patterns = [b"\x00", b"\xFF", None]
        elif method == ShredMethod.DOD_5220_22_M_ECE:
            patterns = [b"\x00", b"\xFF", None, b"\x96", b"\x00", b"\xFF", None]
        elif method == ShredMethod.GUTMANN:
            patterns = list(self._GUTMANN_PATTERNS)
        elif method == ShredMethod.VSITR:
            patterns = list(self._VSITR_PATTERNS)
        elif method == ShredMethod.SCHNEIER:
            patterns = [b"\xFF", b"\x00", None, None, None, None, None]
        else:
            patterns = [b"\x00", b"\xFF", None]

        if passes is not None and passes > 0:
            if len(patterns) < passes:
                patterns = patterns + [None] * (passes - len(patterns))
            else:
                patterns = patterns[:passes]

        try:
            os.chmod(file_path, stat.S_IWRITE)
            file_size = os.path.getsize(file_path)

            with open(file_path, "r+b") as f:
                chunk_size = 1024 * 1024  # 1 MiB stream
                for pattern in patterns:
                    f.seek(0)
                    bytes_written = 0
                    while bytes_written < file_size:
                        write_size = min(chunk_size, file_size - bytes_written)
                        chunk = self._generate_pass_data(pattern, write_size)
                        f.write(chunk)
                        bytes_written += write_size

                    f.flush()
                    os.fsync(f.fileno())

            dir_name = os.path.dirname(file_path)
            base_ext = os.path.splitext(file_path)[1]
            rand_name = os.path.join(dir_name, str(random.randint(100000, 999999)) + base_ext)
            os.rename(file_path, rand_name)
            os.remove(rand_name)
            return True

        except Exception as e:
            self.logger.error(f"Failed to shred file {file_path}: {e}")
            return False

    def shred_directory(
        self,
        dir_path: str,
        passes: int | None = None,
        method: Union[ShredMethod, str] = ShredMethod.DOD_5220_22_M,
    ) -> bool:
        """Recursively shreds a directory and its contents."""
        success = True
        for root, dirs, files in os.walk(dir_path, topdown=False):
            for file in files:
                filepath = os.path.join(root, file)
                if not self.shred_file(filepath, passes=passes, method=method):
                    success = False

            for d in dirs:
                dirpath = os.path.join(root, d)
                try:
                    os.rmdir(dirpath)
                except OSError:
                    success = False

        try:
            os.rmdir(dir_path)
        except OSError:
            success = False

        return success


# Backward-compatible alias
WeaponizedShredder = AdvancedShredder
