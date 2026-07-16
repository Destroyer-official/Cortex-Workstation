"""Human-friendly process identity: what a running program actually is.

Task managers show cryptic names like ``svchost.exe`` or ``fontdrvhost.exe``.
This module turns those into plain-language descriptions so users understand
what's running. It combines two honest sources:

1. A curated table of well-known Windows / common-app processes (instant, no
   disk access), so users get a trustworthy explanation for the usual suspects.
2. The program's own embedded ``FileDescription`` from its PE version resource
   (via pywin32), read once per path and cached. This is the same text Windows
   shows, straight from the vendor - never guessed.

If neither yields anything, we return an empty string rather than inventing a
description. All results are cached, so it stays lightweight on live refreshes.
"""

from __future__ import annotations

import logging
import platform

_LOG = logging.getLogger("cortex.system_tools.process_meta")
_IS_WINDOWS = platform.system() == "Windows"

# Curated, trustworthy explanations for common Windows + app processes.
# Keys are lower-case executable names.
_KNOWN: dict[str, str] = {
    "system": "Windows kernel and system threads",
    "system idle process": "Idle time (unused CPU) - not a real program",
    "registry": "Windows registry subsystem process",
    "smss.exe": "Session Manager - starts Windows sessions",
    "csrss.exe": "Client/Server Runtime - core Windows subsystem",
    "wininit.exe": "Windows startup / initialization process",
    "winlogon.exe": "Windows logon and secure desktop",
    "services.exe": "Service Control Manager - runs Windows services",
    "lsass.exe": "Local Security Authority - handles logins & passwords",
    "svchost.exe": "Service Host - runs one or more Windows services",
    "fontdrvhost.exe": "Font driver host - renders fonts",
    "dwm.exe": "Desktop Window Manager - draws the Windows desktop",
    "explorer.exe": "Windows File Explorer, taskbar and desktop",
    "taskhostw.exe": "Host for Windows background tasks",
    "runtimebroker.exe": "Manages app permissions for Store apps",
    "sihost.exe": "Shell Infrastructure Host - Start menu / shell UI",
    "ctfmon.exe": "Text input, handwriting and language bar",
    "conhost.exe": "Console window host for command-line programs",
    "dllhost.exe": "COM Surrogate - hosts COM/shell components",
    "searchindexer.exe": "Windows Search indexing service",
    "searchhost.exe": "Windows Search / Start menu search UI",
    "startmenuexperiencehost.exe": "Start menu UI host",
    "textinputhost.exe": "Touch keyboard and text input UI",
    "audiodg.exe": "Windows audio device processing",
    "spoolsv.exe": "Print Spooler - manages printing",
    "wmiprvse.exe": "WMI provider - system management queries",
    "wudfhost.exe": "User-mode driver framework host",
    "memcompression": "Compressed memory store (saves RAM)",
    "msmpeng.exe": "Microsoft Defender Antivirus engine",
    "securityhealthservice.exe": "Windows Security health service",
    "nissrv.exe": "Microsoft Defender network inspection",
    "powershell.exe": "Windows PowerShell command shell",
    "pwsh.exe": "PowerShell (cross-platform) command shell",
    "cmd.exe": "Windows Command Prompt",
    "python.exe": "Python interpreter",
    "pythonw.exe": "Python interpreter (windowless)",
    "chrome.exe": "Google Chrome web browser",
    "msedge.exe": "Microsoft Edge web browser",
    "firefox.exe": "Mozilla Firefox web browser",
    "brave.exe": "Brave web browser",
    "opera.exe": "Opera web browser",
    "code.exe": "Visual Studio Code editor",
    "kiro.exe": "Kiro AI development environment",
    "explorer.exe ": "Windows File Explorer",
    "taskmgr.exe": "Windows Task Manager",
    "onedrive.exe": "Microsoft OneDrive cloud sync",
    "steam.exe": "Steam gaming platform",
    "discord.exe": "Discord chat / voice",
    "spotify.exe": "Spotify music player",
    "teams.exe": "Microsoft Teams",
    "ms-teams.exe": "Microsoft Teams",
    "outlook.exe": "Microsoft Outlook email",
    "winword.exe": "Microsoft Word",
    "excel.exe": "Microsoft Excel",
    "notepad.exe": "Notepad text editor",
    "wsl.exe": "Windows Subsystem for Linux",
    "docker.exe": "Docker container platform",
}

# Cache of exe-path -> FileDescription (read once per path).
_desc_cache: dict[str, str] = {}


def known_description(name: str) -> str:
    """Return the curated description for a process *name*, or ''."""
    return _KNOWN.get((name or "").lower().strip(), "")


def file_description(exe_path: str) -> str:
    """Read the vendor's embedded FileDescription for *exe_path* (cached)."""
    if not exe_path:
        return ""
    if exe_path in _desc_cache:
        return _desc_cache[exe_path]
    desc = ""
    if _IS_WINDOWS:
        try:
            import win32api
            info_path = "\\StringFileInfo\\%04X%04X\\FileDescription"
            langs = win32api.GetFileVersionInfo(exe_path, "\\VarFileInfo\\Translation")
            if langs:
                lang, codepage = langs[0]
                desc = win32api.GetFileVersionInfo(
                    exe_path, info_path % (lang, codepage)) or ""
        except Exception as exc:  # noqa: BLE001 - many system exes have no/blocked info
            _LOG.debug("no version info for %s: %s", exe_path, exc)
    _desc_cache[exe_path] = desc.strip()
    return _desc_cache[exe_path]


def describe(name: str, exe_path: str = "") -> str:
    """Best available human description for a process.

    Curated table first (fast, trustworthy for system processes), then the
    program's own FileDescription, else empty (never fabricated).
    """
    known = known_description(name)
    if known:
        return known
    return file_description(exe_path)
