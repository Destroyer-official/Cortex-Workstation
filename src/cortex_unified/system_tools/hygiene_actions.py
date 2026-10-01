"""Cortex Cleaner — instant hygiene actions (DNS cache flush, clipboard clear).

One-shot OS hygiene operations with no scan phase: they finish in under a
second, need no folder picker, and report an honest success/failure result.
Used by the Cleanup Hub's quick-actions row so classic "System" checkboxes
(DNS cache, clipboard) also live in one place.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass

logger = logging.getLogger("cortex.system_tools.hygiene_actions")


@dataclass
class HygieneResult:
    """Outcome of one hygiene action."""

    action: str
    success: bool
    message: str


def flush_dns() -> HygieneResult:
    """Flush the OS DNS resolver cache.

    Windows runs ``ipconfig /flushdns`` (works unelevated); POSIX tries
    ``resolvectl``/``systemd-resolve`` when present and reports honestly when
    no known flush mechanism exists.
    """
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            ok = proc.returncode == 0
            detail = (proc.stdout or proc.stderr or "").strip().splitlines()
            detail = detail[0] if detail else ""
            return HygieneResult(
                action="flush_dns",
                success=ok,
                message=(
                    f"DNS resolver cache flushed. {detail}".strip()
                    if ok
                    else f"DNS flush failed (exit {proc.returncode}). {detail}".strip()
                ),
            )
        except Exception as exc:  # noqa: BLE001 - report, don't crash the batch
            logger.error("DNS flush failed: %s", exc)
            return HygieneResult(action="flush_dns", success=False, message=f"DNS flush failed: {exc}")
    for cmd in (["resolvectl", "flush-caches"], ["systemd-resolve", "--flush-caches"]):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0:
            return HygieneResult(action="flush_dns", success=True, message="DNS resolver cache flushed.")
    return HygieneResult(
        action="flush_dns",
        success=False,
        message="No supported DNS flush mechanism found on this host.",
    )


def clear_clipboard() -> HygieneResult:
    """Empty the OS clipboard (text payload).

    Windows uses ``OpenClipboard``/``EmptyClipboard`` via ctypes; other
    platforms report honestly instead of pretending. Only supported on
    Windows in this build.
    """
    if os.name != "nt":
        return HygieneResult(
            action="clear_clipboard",
            success=False,
            message="Clipboard clearing is only supported on Windows in this build.",
        )
    try:
        import ctypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        if not user32.OpenClipboard(None):
            return HygieneResult(
                action="clear_clipboard",
                success=False,
                message="Clipboard is in use by another app — try again in a moment.",
            )
        try:
            ok = bool(user32.EmptyClipboard())
        finally:
            user32.CloseClipboard()
        if ok:
            return HygieneResult(action="clear_clipboard", success=True, message="Clipboard cleared.")
        return HygieneResult(action="clear_clipboard", success=False, message="Clipboard clear was refused by Windows.")
    except Exception as exc:  # noqa: BLE001 - report, don't crash the batch
        logger.error("clipboard clear failed: %s", exc)
        return HygieneResult(action="clear_clipboard", success=False, message=f"Clipboard clear failed: {exc}")
