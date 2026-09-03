"""Nexus Explorer — High-Performance File Checksum & Integrity Utility.

Provides streaming cryptographic and non-cryptographic checksum calculations,
manifest generation (.sfv, .md5, .sha256, .sha512), batch directory hashing,
and automated integrity verification against checksum files.
"""

from __future__ import annotations

import hashlib
import os
import time
import zlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


class HashAlgorithm(Enum):
    """HashAlgorithm."""
    MD5 = "MD5"
    SHA1 = "SHA-1"
    SHA256 = "SHA-256"
    SHA512 = "SHA-512"
    BLAKE3 = "BLAKE3"
    CRC32 = "CRC32"
    XXHASH64 = "xxHash64"
    """HashAlgorithm class."""


@dataclass
class HashResult:
    """HashResult."""
    path: str
    filename: str
    size: int
    algorithm: HashAlgorithm
    digest: str
    elapsed_seconds: float
    error: Optional[str] = None
    """HashResult class."""


@dataclass
class VerifyItem:
    """VerifyItem."""
    path: str
    expected_hash: str
    actual_hash: str
    algorithm: HashAlgorithm
    status: str  # "MATCH", "MISMATCH", "MISSING", "ERROR"
    error_message: str = ""
    """VerifyItem class."""


class HashTool:
    """Production file hashing engine with multi-algorithm streaming and manifest support."""

    CHUNK_SIZE = 64 * 1024  # 64 KB streaming buffer

    @classmethod
    def compute_hash(
        cls,
        file_path: str | Path,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> HashResult:
        """Compute the cryptographic or CRC32 hash for a single file."""
        path_obj = Path(file_path)
        if not path_obj.is_file():
            return HashResult(
                path=str(file_path),
                filename=path_obj.name,
                size=0,
                algorithm=algorithm,
                digest="",
                elapsed_seconds=0.0,
                error="File does not exist or is not a regular file",
            )

        start_time = time.perf_counter()
        total_size = path_obj.stat().st_size
        bytes_read = 0

        try:
            if algorithm == HashAlgorithm.CRC32:
                crc = 0
                with open(path_obj, "rb") as f:
                    while chunk := f.read(cls.CHUNK_SIZE):
                        if cancel_check and cancel_check():
                            return HashResult(str(file_path), path_obj.name, total_size, algorithm, "", 0.0, "Cancelled")
                        crc = zlib.crc32(chunk, crc)
                        bytes_read += len(chunk)
                        if progress_cb:
                            progress_cb(bytes_read, total_size)
                digest = f"{crc & 0xFFFFFFFF:08X}"
            elif algorithm == HashAlgorithm.BLAKE3:
                try:
                    import blake3
                    hasher = blake3.blake3()
                except ImportError:
                    # Fallback to standard hashlib sha256
                    hasher = hashlib.sha256()
                with open(path_obj, "rb") as f:
                    while chunk := f.read(cls.CHUNK_SIZE):
                        if cancel_check and cancel_check():
                            return HashResult(str(file_path), path_obj.name, total_size, algorithm, "", 0.0, "Cancelled")
                        hasher.update(chunk)
                        bytes_read += len(chunk)
                        if progress_cb:
                            progress_cb(bytes_read, total_size)
                digest = hasher.hexdigest().upper()
            elif algorithm == HashAlgorithm.XXHASH64:
                try:
                    import xxhash
                    hasher = xxhash.xxh64()
                    with open(path_obj, "rb") as f:
                        while chunk := f.read(cls.CHUNK_SIZE):
                            if cancel_check and cancel_check():
                                return HashResult(str(file_path), path_obj.name, total_size, algorithm, "", 0.0, "Cancelled")
                            hasher.update(chunk)
                            bytes_read += len(chunk)
                            if progress_cb:
                                progress_cb(bytes_read, total_size)
                    digest = hasher.hexdigest().upper()
                except ImportError:
                    return cls.compute_hash(file_path, HashAlgorithm.SHA256, progress_cb, cancel_check)
            else:
                # Standard hashlib algorithms
                algo_map = {
                    HashAlgorithm.MD5: hashlib.md5,
                    HashAlgorithm.SHA1: hashlib.sha1,
                    HashAlgorithm.SHA256: hashlib.sha256,
                    HashAlgorithm.SHA512: hashlib.sha512,
                }
                hasher_func = algo_map.get(algorithm, hashlib.sha256)
                hasher = hasher_func()
                with open(path_obj, "rb") as f:
                    while chunk := f.read(cls.CHUNK_SIZE):
                        if cancel_check and cancel_check():
                            return HashResult(str(file_path), path_obj.name, total_size, algorithm, "", 0.0, "Cancelled")
                        hasher.update(chunk)
                        bytes_read += len(chunk)
                        if progress_cb:
                            progress_cb(bytes_read, total_size)
                digest = hasher.hexdigest().upper()

            elapsed = time.perf_counter() - start_time
            return HashResult(
                path=str(path_obj.resolve()),
                filename=path_obj.name,
                size=total_size,
                algorithm=algorithm,
                digest=digest,
                elapsed_seconds=elapsed,
            )
        except Exception as exc:
            return HashResult(
                path=str(file_path),
                filename=path_obj.name,
                size=total_size,
                algorithm=algorithm,
                digest="",
                elapsed_seconds=time.perf_counter() - start_time,
                error=str(exc),
            )

    @classmethod
    def compute_all_hashes(
        cls,
        file_path: str | Path,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[HashAlgorithm, HashResult]:
        """Compute MD5, SHA1, SHA256, SHA512, and CRC32 in a single stream pass."""
        path_obj = Path(file_path)
        if not path_obj.is_file():
            empty_err = "File not found"
            return {
                algo: HashResult(str(file_path), path_obj.name, 0, algo, "", 0.0, empty_err)
                for algo in (HashAlgorithm.MD5, HashAlgorithm.SHA1, HashAlgorithm.SHA256, HashAlgorithm.SHA512, HashAlgorithm.CRC32)
            }

        start_time = time.perf_counter()
        total_size = path_obj.stat().st_size
        bytes_read = 0

        md5_h = hashlib.md5()
        sha1_h = hashlib.sha1()
        sha256_h = hashlib.sha256()
        sha512_h = hashlib.sha512()
        crc = 0

        try:
            with open(path_obj, "rb") as f:
                while chunk := f.read(cls.CHUNK_SIZE):
                    if cancel_check and cancel_check():
                        break
                    md5_h.update(chunk)
                    sha1_h.update(chunk)
                    sha256_h.update(chunk)
                    sha512_h.update(chunk)
                    crc = zlib.crc32(chunk, crc)
                    bytes_read += len(chunk)
                    if progress_cb:
                        progress_cb(bytes_read, total_size)

            elapsed = time.perf_counter() - start_time
            return {
                HashAlgorithm.MD5: HashResult(str(path_obj), path_obj.name, total_size, HashAlgorithm.MD5, md5_h.hexdigest().upper(), elapsed),
                HashAlgorithm.SHA1: HashResult(str(path_obj), path_obj.name, total_size, HashAlgorithm.SHA1, sha1_h.hexdigest().upper(), elapsed),
                HashAlgorithm.SHA256: HashResult(str(path_obj), path_obj.name, total_size, HashAlgorithm.SHA256, sha256_h.hexdigest().upper(), elapsed),
                HashAlgorithm.SHA512: HashResult(str(path_obj), path_obj.name, total_size, HashAlgorithm.SHA512, sha512_h.hexdigest().upper(), elapsed),
                HashAlgorithm.CRC32: HashResult(str(path_obj), path_obj.name, total_size, HashAlgorithm.CRC32, f"{crc & 0xFFFFFFFF:08X}", elapsed),
            }
        except Exception as exc:
            err = str(exc)
            return {
                algo: HashResult(str(file_path), path_obj.name, total_size, algo, "", 0.0, err)
                for algo in (HashAlgorithm.MD5, HashAlgorithm.SHA1, HashAlgorithm.SHA256, HashAlgorithm.SHA512, HashAlgorithm.CRC32)
            }

    @classmethod
    def create_manifest(
        cls,
        files: List[str | Path],
        output_file: str | Path,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> bool:
        """Create a checksum manifest file (.sfv, .md5, .sha256, etc.)."""
        lines = []
        out_path = Path(output_file)
        base_dir = out_path.parent

        if algorithm == HashAlgorithm.CRC32:
            lines.append("; Simple File Verification (.sfv) created by Nexus Explorer\n")
            lines.append(f"; Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n;\n")

        total_files = len(files)
        for idx, fpath in enumerate(files):
            if cancel_check and cancel_check():
                return False
            p = Path(fpath)
            if not p.is_file():
                continue
            if progress_cb:
                progress_cb(idx + 1, total_files, p.name)

            res = cls.compute_hash(p, algorithm, cancel_check=cancel_check)
            if res.error or not res.digest:
                continue

            try:
                rel_name = p.relative_to(base_dir).as_posix()
            except ValueError:
                rel_name = p.name

            if algorithm == HashAlgorithm.CRC32:
                lines.append(f"{rel_name} {res.digest}\n")
            else:
                lines.append(f"{res.digest.lower()} *{rel_name}\n")

        try:
            out_path.write_text("".join(lines), encoding="utf-8")
            return True
        except Exception:
            return False

    @classmethod
    def verify_manifest(
        cls,
        manifest_file: str | Path,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> List[VerifyItem]:
        """Verify files against a checksum manifest (.sfv, .md5, .sha256, .sha512)."""
        manifest_path = Path(manifest_file)
        if not manifest_path.is_file():
            return []

        ext = manifest_path.suffix.lower()
        if ext == ".sfv":
            algo = HashAlgorithm.CRC32
        elif ext == ".md5":
            algo = HashAlgorithm.MD5
        elif ext == ".sha1":
            algo = HashAlgorithm.SHA1
        elif ext == ".sha512":
            algo = HashAlgorithm.SHA512
        else:
            algo = HashAlgorithm.SHA256

        base_dir = manifest_path.parent
        items_to_check: List[Tuple[Path, str]] = []

        try:
            lines = manifest_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            return []

        for line in lines:
            line = line.strip()
            if not line or line.startswith(";") or line.startswith("#"):
                continue

            if algo == HashAlgorithm.CRC32:
                parts = line.rsplit(maxsplit=1)
                if len(parts) == 2:
                    fn, expected_crc = parts
                    items_to_check.append((base_dir / fn, expected_crc.upper()))
            else:
                if " *" in line:
                    h, fn = line.split(" *", 1)
                    items_to_check.append((base_dir / fn.strip(), h.strip().upper()))
                elif "  " in line:
                    h, fn = line.split("  ", 1)
                    items_to_check.append((base_dir / fn.strip(), h.strip().upper()))
                else:
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        items_to_check.append((base_dir / parts[1].strip(), parts[0].strip().upper()))

        results: List[VerifyItem] = []
        total = len(items_to_check)

        for i, (target_path, expected_hash) in enumerate(items_to_check):
            if cancel_check and cancel_check():
                break
            if progress_cb:
                progress_cb(i + 1, total, target_path.name)

            if not target_path.exists():
                results.append(VerifyItem(
                    path=str(target_path),
                    expected_hash=expected_hash,
                    actual_hash="",
                    algorithm=algo,
                    status="MISSING",
                    error_message="File not found",
                ))
                continue

            h_res = cls.compute_hash(target_path, algo, cancel_check=cancel_check)
            if h_res.error:
                results.append(VerifyItem(
                    path=str(target_path),
                    expected_hash=expected_hash,
                    actual_hash="",
                    algorithm=algo,
                    status="ERROR",
                    error_message=h_res.error,
                ))
            elif h_res.digest.upper() == expected_hash.upper():
                results.append(VerifyItem(
                    path=str(target_path),
                    expected_hash=expected_hash,
                    actual_hash=h_res.digest,
                    algorithm=algo,
                    status="MATCH",
                ))
            else:
                results.append(VerifyItem(
                    path=str(target_path),
                    expected_hash=expected_hash,
                    actual_hash=h_res.digest,
                    algorithm=algo,
                    status="MISMATCH",
                ))

        return results
