"""Nexus Explorer — High-Throughput Batch Image Optimizer & WebP Transcoder.

Compresses and transcodes image assets:
1. Supports PNG, JPEG, BMP, TIFF, WebP formats.
2. Re-encodes via QImage/QImageWriter; no explicit EXIF/GPS handling is performed.
3. Provides configurable quality presets (1-100) and WebP conversion.
4. Calculates real disk space savings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtGui import QImage, QImageReader, QImageWriter


@dataclass
class ImageOptimizeResult:
    """Imageoptimizeresult.

    Manages ImageOptimizeResult operations and coordinates related state changes for the component.
    """
    source_path: str
    output_path: str
    original_size_bytes: int
    compressed_size_bytes: int
    space_saved_bytes: int
    compression_ratio_pct: float
    success: bool
    error: Optional[str] = None


@dataclass
class BatchOptimizeSummary:
    """Batchoptimizesummary.

    Manages BatchOptimizeSummary operations and coordinates related state changes for the component.
    """
    total_images: int
    successful_count: int
    total_original_bytes: int
    total_compressed_bytes: int
    total_freed_bytes: int
    results: List[ImageOptimizeResult]


class ImageOptimizer:
    """Imageoptimizer.

    Manages ImageOptimizer operations and coordinates related state changes for the component.
    """

    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}

    @classmethod
    def optimize_image(
        cls,
        source_path: str | Path,
        output_path: Optional[str | Path] = None,
        target_format: str = "webp",  # "webp", "jpg", "png", "original"
        quality: int = 80,  # 1 - 100
        strip_metadata: bool = True,
    ) -> ImageOptimizeResult:
        """Compress a single image and save to output path.
        strip_metadata: currently unused (no explicit stripping implemented); QImage re-encode drops metadata."""
        src_p = Path(source_path).resolve()
        if not src_p.is_file():
            return ImageOptimizeResult(str(src_p), "", 0, 0, 0, 0.0, False, "Source image not found")

        orig_size = src_p.stat().st_size

        # Determine target format and output path
        fmt = target_format.lower().replace(".", "")
        if fmt == "original":
            fmt = src_p.suffix.lower().lstrip(".")
            if fmt == "jpeg":
                fmt = "jpg"

        if output_path is None:
            out_p = src_p.with_name(f"{src_p.stem}_opt.{fmt}")
        else:
            out_p = Path(output_path).resolve()

        out_p.parent.mkdir(parents=True, exist_ok=True)

        try:
            img = QImage(str(src_p))
            if img.isNull():
                return ImageOptimizeResult(str(src_p), str(out_p), orig_size, 0, 0, 0.0, False, "Failed to decode image data")

            writer = QImageWriter(str(out_p), fmt.encode("ascii"))
            writer.setQuality(quality)

            if fmt in ("jpg", "jpeg", "webp"):
                writer.setOptimizedWrite(True)

            ok = writer.write(img)
            if not ok:
                return ImageOptimizeResult(str(src_p), str(out_p), orig_size, 0, 0, 0.0, False, writer.errorString() or "Write failed")

            new_size = out_p.stat().st_size
            freed = max(0, orig_size - new_size)
            ratio = ((orig_size - new_size) / orig_size * 100.0) if orig_size > 0 else 0.0

            return ImageOptimizeResult(
                source_path=str(src_p),
                output_path=str(out_p),
                original_size_bytes=orig_size,
                compressed_size_bytes=new_size,
                space_saved_bytes=freed,
                compression_ratio_pct=round(ratio, 1),
                success=True,
            )
        except Exception as exc:
            return ImageOptimizeResult(str(src_p), str(out_p), orig_size, 0, 0, 0.0, False, str(exc))

    @classmethod
    def optimize_batch(
        cls,
        image_paths: List[str | Path],
        output_directory: Optional[str | Path] = None,
        target_format: str = "webp",
        quality: int = 80,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> BatchOptimizeSummary:
        """Batch optimize multiple images.

        Manages optimize batch operations and coordinates related state changes for the component.

        Args:
            image_paths (List[str | Path]): Filesystem path to the target file or directory.
            output_directory (Optional[str | Path]): The output directory parameter.
            target_format (str): The target format parameter.
            quality (int): The quality parameter.
            progress_cb (Optional[Callable[[int, int, str], None]]): Callback invoked with progress updates.
            cancel_check (Optional[Callable[[], bool]]): Threading event or callable to check for cancellation.

        Returns:
            BatchOptimizeSummary: Result of the operation.
        """
        results: List[ImageOptimizeResult] = []
        total_orig = 0
        total_comp = 0
        success_cnt = 0
        total_imgs = len(image_paths)

        out_dir = Path(output_directory).resolve() if output_directory else None
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)

        for idx, imp in enumerate(image_paths):
            if cancel_check and cancel_check():
                break

            p = Path(imp).resolve()
            if not p.is_file():
                continue

            dest_path = None
            if out_dir:
                ext = target_format.lower().lstrip(".")
                if ext == "original":
                    ext = p.suffix.lower().lstrip(".")
                dest_path = out_dir / f"{p.stem}.{ext}"

            res = cls.optimize_image(
                source_path=p,
                output_path=dest_path,
                target_format=target_format,
                quality=quality,
            )

            results.append(res)
            if res.success:
                success_cnt += 1
                total_orig += res.original_size_bytes
                total_comp += res.compressed_size_bytes

            if progress_cb:
                progress_cb(idx + 1, total_imgs, p.name)

        return BatchOptimizeSummary(
            total_images=total_imgs,
            successful_count=success_cnt,
            total_original_bytes=total_orig,
            total_compressed_bytes=total_comp,
            total_freed_bytes=max(0, total_orig - total_comp),
            results=results,
        )
