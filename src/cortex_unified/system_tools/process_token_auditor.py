"""Cortex Cleaner — Process Security Token & Integrity Forensics.

Forensic inspector for Windows process security tokens:
- Inspects Token Integrity Levels (Untrusted, Low, Medium, High, System).
- Audits Token Elevation Types (Default, Full Elevated, Limited Standard).
- Identifies critical dangerous privileges (SeDebugPrivilege, SeImpersonatePrivilege, SeTakeOwnershipPrivilege).
- Detects unauthorized privilege escalation or unconstrained background processes.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import os
import psutil
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("cortex.system_tools.process_token_auditor")

# Win32 Process & Token Constants
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008

TokenIntegrityLevel = 25
TokenElevationType = 18
TokenPrivileges = 3

SECURITY_MANDATORY_UNTRUSTED_RID = 0x0000
SECURITY_MANDATORY_LOW_RID = 0x1000
SECURITY_MANDATORY_MEDIUM_RID = 0x2000
SECURITY_MANDATORY_HIGH_RID = 0x3000
SECURITY_MANDATORY_SYSTEM_RID = 0x4000


@dataclass
class ProcessTokenInfo:
    """Process Token Info data container."""
    pid: int
    name: str
    username: str
    integrity_level: str  # "Untrusted", "Low", "Medium", "High", "System", "Unknown"
    elevation_type: str  # "Full/Elevated", "Limited", "Default", "Unknown"
    is_elevated: bool
    privileges: list[str] = field(default_factory=list)
    risk_level: str = "Low"


@dataclass
class ProcessTokenAuditReport:
    """Process Token Audit Report data container."""
    processes: list[ProcessTokenInfo] = field(default_factory=list)
    system_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    elevated_count: int = 0
    dangerous_privilege_count: int = 0
    error: Optional[str] = None


class ProcessTokenAuditor:
    """Enterprise Process Security Token & Privilege Auditor."""

    def __init__(self):
        """Initialize Process Token Auditor."""
        self._is_windows = os.name == "nt"

    def audit(self, max_processes: int = 150) -> ProcessTokenAuditReport:
        """Audit active running processes and decode their security tokens."""
        if not self._is_windows:
            return ProcessTokenAuditReport(error="Process token auditing requires Windows NT.")

        results: list[ProcessTokenInfo] = []
        sys_cnt = high_cnt = med_cnt = low_cnt = elev_cnt = dang_cnt = 0

        for proc in psutil.process_iter(["pid", "name", "username"]):
            if len(results) >= max_processes:
                break
            try:
                pid = proc.info["pid"]
                name = proc.info["name"] or "Unknown"
                user = proc.info["username"] or "N/A"

                integ, elev, is_elev, privs = self._inspect_token(pid)

                if integ == "System":
                    sys_cnt += 1
                elif integ == "High":
                    high_cnt += 1
                elif integ == "Medium":
                    med_cnt += 1
                elif integ == "Low":
                    low_cnt += 1

                if is_elev:
                    elev_cnt += 1

                risk = "Low"
                if "SeDebugPrivilege" in privs or "SeImpersonatePrivilege" in privs:
                    dang_cnt += 1
                    risk = "High" if "user" in user.lower() else "Medium"
                elif integ == "High" and "system" not in user.lower():
                    risk = "Medium"

                results.append(
                    ProcessTokenInfo(
                        pid=pid,
                        name=name,
                        username=user,
                        integrity_level=integ,
                        elevation_type=elev,
                        is_elevated=is_elev,
                        privileges=privs,
                        risk_level=risk,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return ProcessTokenAuditReport(
            processes=results,
            system_count=sys_cnt,
            high_count=high_cnt,
            medium_count=med_cnt,
            low_count=low_cnt,
            elevated_count=elev_cnt,
            dangerous_privilege_count=dang_cnt,
        )

    def _inspect_token(self, pid: int) -> tuple[str, str, bool, list[str]]:
        """Inspect a single process token via Win32 APIs."""
        h_proc = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h_proc:
            return "Unknown", "Unknown", False, []

        h_token = wintypes.HANDLE()
        try:
            res = ctypes.windll.advapi32.OpenProcessToken(h_proc, TOKEN_QUERY, ctypes.byref(h_token))
            if not res:
                return "Unknown", "Unknown", False, []

            integ = self._get_integrity_level(h_token)
            elev_type, is_elev = self._get_elevation_type(h_token)
            privs = self._get_privileges(h_token)
            return integ, elev_type, is_elev, privs
        finally:
            if h_token:
                ctypes.windll.kernel32.CloseHandle(h_token)
            ctypes.windll.kernel32.CloseHandle(h_proc)

    def _get_integrity_level(self, h_token) -> str:
        """Query TokenIntegrityLevel."""
        try:
            req_len = wintypes.DWORD(0)
            ctypes.windll.advapi32.GetTokenInformation(h_token, TokenIntegrityLevel, None, 0, ctypes.byref(req_len))
            if req_len.value == 0:
                return "Unknown"

            buf = ctypes.create_string_buffer(req_len.value)
            if not ctypes.windll.advapi32.GetTokenInformation(
                h_token, TokenIntegrityLevel, buf, req_len.value, ctypes.byref(req_len)
            ):
                return "Unknown"

            # TOKEN_MANDATORY_LABEL contains SID_AND_ATTRIBUTES
            psid = ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0]
            if not psid:
                return "Unknown"

            ctypes.windll.advapi32.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
            ctypes.windll.advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
            ctypes.windll.advapi32.GetSidSubAuthority.argtypes = [ctypes.c_void_p, wintypes.DWORD]
            ctypes.windll.advapi32.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)

            sub_auth_count = ctypes.windll.advapi32.GetSidSubAuthorityCount(psid)
            if not sub_auth_count:
                return "Unknown"
            count = sub_auth_count[0]

            rid_ptr = ctypes.windll.advapi32.GetSidSubAuthority(psid, count - 1)
            if not rid_ptr:
                return "Unknown"
            rid = rid_ptr[0]

            if rid < SECURITY_MANDATORY_LOW_RID:
                return "Untrusted"
            elif rid < SECURITY_MANDATORY_MEDIUM_RID:
                return "Low"
            elif rid < SECURITY_MANDATORY_HIGH_RID:
                return "Medium"
            elif rid < SECURITY_MANDATORY_SYSTEM_RID:
                return "High"
            else:
                return "System"
        except Exception:
            return "Unknown"

    def _get_elevation_type(self, h_token) -> tuple[str, bool]:
        """Query TokenElevationType."""
        elev_val = wintypes.DWORD(0)
        req_len = wintypes.DWORD(0)
        res = ctypes.windll.advapi32.GetTokenInformation(
            h_token,
            TokenElevationType,
            ctypes.byref(elev_val),
            ctypes.sizeof(elev_val),
            ctypes.byref(req_len),
        )
        if not res:
            return "Default", False

        # 1: Default, 2: Full (elevated admin), 3: Limited (standard user in admin split token)
        if elev_val.value == 2:
            return "Full/Elevated", True
        elif elev_val.value == 3:
            return "Limited", False
        return "Default", False

    def _get_privileges(self, h_token) -> list[str]:
        """Query enabled privileges on the token."""
        # Query TOKEN_PRIVILEGES size
        req_len = wintypes.DWORD(0)
        ctypes.windll.advapi32.GetTokenInformation(h_token, TokenPrivileges, None, 0, ctypes.byref(req_len))
        if req_len.value == 0:
            return []

        buf = ctypes.create_string_buffer(req_len.value)
        if not ctypes.windll.advapi32.GetTokenInformation(
            h_token, TokenPrivileges, buf, req_len.value, ctypes.byref(req_len)
        ):
            return []

        count = ctypes.cast(buf, ctypes.POINTER(wintypes.DWORD))[0]
        privs = []

        # Each LUID_AND_ATTRIBUTES is 12 bytes (8 bytes LUID + 4 bytes Attributes)
        # offset starts at 4 bytes (after count)
        offset = 4
        for _ in range(min(count, 64)):
            luid_low = ctypes.cast(ctypes.byref(buf, offset), ctypes.POINTER(wintypes.DWORD))[0]
            luid_high = ctypes.cast(ctypes.byref(buf, offset + 4), ctypes.POINTER(wintypes.LONG))[0]
            attrs = ctypes.cast(ctypes.byref(buf, offset + 8), ctypes.POINTER(wintypes.DWORD))[0]
            offset += 12

            # Lookup privilege name
            name_buf = ctypes.create_unicode_buffer(128)
            name_len = wintypes.DWORD(128)
            class LUID(ctypes.Structure):
                """L U I D."""
                _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

            l = LUID(luid_low, luid_high)
            if ctypes.windll.advapi32.LookupPrivilegeNameW(None, ctypes.byref(l), name_buf, ctypes.byref(name_len)):
                # SE_PRIVILEGE_ENABLED = 0x00000002
                if attrs & 2:
                    privs.append(name_buf.value)

        return privs
