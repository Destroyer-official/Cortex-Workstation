"""Nexus Explorer — Binary & Hex File Differ Engine.

Performs byte-by-byte comparison between two binary or data files:
1. Calculates match percentage and byte discrepancies.
2. Locates first difference offset.
3. Generates side-by-side hex diff dumps with offset markers and ASCII representations.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class HexDiffChunk:
    """Hexdiffchunk.

    Manages HexDiffChunk operations and coordinates related state changes for the component.
    """
    offset: int
    left_bytes: bytes
    right_bytes: bytes
    left_hex: str
    right_hex: str
    left_ascii: str
    right_ascii: str
    is_match: bool


@dataclass
class BinaryDiffReport:
    """Binarydiffreport.

    Manages BinaryDiffReport operations and coordinates related state changes for the component.
    """
    file_a: str
    file_b: str
    size_a: int
    size_b: int
    is_identical: bool
    matching_percentage: float
    total_differences_bytes: int
    first_difference_offset: Optional[int]
    diff_chunks: List[HexDiffChunk]
    error: Optional[str] = None


class BinaryDiffer:
    """Binarydiffer.

    Manages BinaryDiffer operations and coordinates related state changes for the component.
    """

    CHUNK_SIZE = 16  # Standard 16-byte hex viewer row

    @staticmethod
    def _to_ascii(b_data: bytes) -> str:
        """Convert bytes to printable ASCII with dots for non-printables.

        Manages to ascii operations and coordinates related state changes for the component.

        Args:
            b_data (bytes): The b data parameter.

        Returns:
            str: Formatted string or path.
        """
        return "".join(chr(b) if 32 <= b <= 126 else "." for b in b_data)

    @classmethod
    def compare_binary_files(
        cls,
        file_a_path: str | Path,
        file_b_path: str | Path,
        max_diff_chunks: int = 200,
    ) -> BinaryDiffReport:
        """Perform byte-by-byte comparison and generate hex diff report.

        Manages compare binary files operations and coordinates related state changes for the component.

        Args:
            file_a_path (str | Path): Filesystem path to the target file or directory.
            file_b_path (str | Path): Filesystem path to the target file or directory.
            max_diff_chunks (int): The max diff chunks parameter.

        Returns:
            BinaryDiffReport: Result of the operation.
        """
        pa = Path(file_a_path).resolve()
        pb = Path(file_b_path).resolve()

        if not pa.is_file() or not pb.is_file():
            return BinaryDiffReport(
                file_a=str(pa),
                file_b=str(pb),
                size_a=pa.stat().st_size if pa.is_file() else 0,
                size_b=pb.stat().st_size if pb.is_file() else 0,
                is_identical=False,
                matching_percentage=0.0,
                total_differences_bytes=0,
                first_difference_offset=None,
                diff_chunks=[],
                error="One or both files do not exist",
            )

        size_a = pa.stat().st_size
        size_b = pb.stat().st_size
        max_size = max(size_a, size_b)

        if max_size == 0:
            return BinaryDiffReport(str(pa), str(pb), 0, 0, True, 100.0, 0, None, [])

        offset = 0
        matching_bytes = 0
        diff_bytes = 0
        first_diff: Optional[int] = None
        chunks: List[HexDiffChunk] = []

        try:
            with open(pa, "rb") as fa, open(pb, "rb") as fb:
                while offset < max_size:
                    chunk_a = fa.read(cls.CHUNK_SIZE)
                    chunk_b = fb.read(cls.CHUNK_SIZE)

                    is_match = chunk_a == chunk_b
                    min_len = min(len(chunk_a), len(chunk_b))

                    for i in range(min_len):
                        if chunk_a[i] == chunk_b[i]:
                            matching_bytes += 1
                        else:
                            diff_bytes += 1
                            if first_diff is None:
                                first_diff = offset + i

                    # Account for size differences
                    size_discrepancy = abs(len(chunk_a) - len(chunk_b))
                    if size_discrepancy > 0:
                        diff_bytes += size_discrepancy
                        if first_diff is None:
                            first_diff = offset + min_len

                    # Record chunk if different or if within sample limit
                    if not is_match and len(chunks) < max_diff_chunks:
                        chunks.append(HexDiffChunk(
                            offset=offset,
                            left_bytes=chunk_a,
                            right_bytes=chunk_b,
                            left_hex=chunk_a.hex(" ").upper(),
                            right_hex=chunk_b.hex(" ").upper(),
                            left_ascii=cls._to_ascii(chunk_a),
                            right_ascii=cls._to_ascii(chunk_b),
                            is_match=is_match,
                        ))

                    offset += cls.CHUNK_SIZE

            pct = (matching_bytes / max_size) * 100.0 if max_size > 0 else 100.0
            is_ident = size_a == size_b and diff_bytes == 0

            return BinaryDiffReport(
                file_a=str(pa),
                file_b=str(pb),
                size_a=size_a,
                size_b=size_b,
                is_identical=is_ident,
                matching_percentage=round(pct, 2),
                total_differences_bytes=diff_bytes,
                first_difference_offset=first_diff,
                diff_chunks=chunks,
            )
        except Exception as exc:
            return BinaryDiffReport(
                file_a=str(pa),
                file_b=str(pb),
                size_a=size_a,
                size_b=size_b,
                is_identical=False,
                matching_percentage=0.0,
                total_differences_bytes=0,
                first_difference_offset=None,
                diff_chunks=[],
                error=str(exc),
            )
