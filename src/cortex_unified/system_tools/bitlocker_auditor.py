"""Cortex Cleaner — BitLocker & Drive Encryption Auditor.

Audits hardware and volume encryption status across all storage volumes:
- Queries BitLocker protection state, encryption percentage, and conversion status.
- Audits encryption ciphers (XTS-AES 128, XTS-AES 256, AES-CBC).
- Identifies active Key Protectors (TPM, PIN, Recovery Password).
- Alerts on unprotected volumes containing sensitive user data or system files.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("cortex.system_tools.bitlocker_auditor")


@dataclass
class EncryptedVolumeInfo:
    """Encrypted Volume Info data container."""
    drive_letter: str
    volume_name: str
    size_str: str
    bitlocker_version: str
    conversion_status: str
    percent_encrypted: float
    encryption_method: str
    protection_status: str
    lock_status: str
    key_protectors: list[str] = field(default_factory=list)

    @property
    def is_protected(self) -> bool:
        """Is protected."""
        return "on" in self.protection_status.lower()

    @property
    def is_fully_encrypted(self) -> bool:
        """Is fully encrypted."""
        return self.percent_encrypted >= 99.9 or "fully encrypted" in self.conversion_status.lower()


@dataclass
class BitLockerAuditReport:
    """Bit Locker Audit Report data container."""
    volumes: list[EncryptedVolumeInfo] = field(default_factory=list)
    fully_protected_count: int = 0
    unprotected_count: int = 0
    overall_compliance: str = "Compliant"
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None


class BitLockerAuditor:
    """Enterprise BitLocker Drive Encryption Auditor."""

    def __init__(self):
        """Initialize Bit Locker Auditor."""
        self._is_windows = os.name == "nt"

    def audit(self) -> BitLockerAuditReport:
        """Run complete BitLocker audit across all physical and logical volumes."""
        if not self._is_windows:
            return BitLockerAuditReport(error="BitLocker auditing requires Windows NT.")

        volumes = self._query_manage_bde()
        if not volumes:
            # Fallback to WMI/PowerShell
            volumes = self._query_wmi_powershell()

        protected = sum(1 for v in volumes if v.is_protected)
        unprotected = len(volumes) - protected

        warnings = []
        for v in volumes:
            if not v.is_protected:
                warnings.append(
                    f"Volume {v.drive_letter} is unprotected and unencrypted. Data at rest is exposed to physical theft."
                )
            elif "xts-aes 128" in v.encryption_method.lower():
                warnings.append(
                    f"Volume {v.drive_letter} uses XTS-AES 128. For top-tier enterprise compliance, XTS-AES 256 is recommended."
                )

        compliance = "Compliant" if unprotected == 0 and len(volumes) > 0 else "Action Required"

        return BitLockerAuditReport(
            volumes=volumes,
            fully_protected_count=protected,
            unprotected_count=unprotected,
            overall_compliance=compliance,
            warnings=warnings,
        )

    def _query_manage_bde(self) -> list[EncryptedVolumeInfo]:
        """Query BitLocker status via manage-bde command line."""
        cmd = ["manage-bde", "-status"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:
            logger.warning("Failed to invoke manage-bde: %s", exc)
            return []

        out = res.stdout or ""
        if "Volume " not in out:
            return []

        volumes: list[EncryptedVolumeInfo] = []
        raw_blocks = re.split(r"\n(?=Volume [A-Za-z0-9:]+)", out)

        for block in raw_blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if not lines or not lines[0].startswith("Volume "):
                continue

            # e.g. 'Volume C: [OSDisk]'
            header = lines[0]
            drive_m = re.search(r"Volume\s+([A-Za-z0-9:]+)(?:\s+\[(.*?)\])?", header)
            drive_letter = drive_m.group(1) if drive_m else "Unknown"
            vol_name = drive_m.group(2) if drive_m and drive_m.group(2) else ""

            size_str = ""
            version = "2.0"
            conversion = "Unknown"
            percent = 0.0
            cipher = "None"
            protection = "Off"
            lock = "Unlocked"
            protectors = []

            for line in lines[1:]:
                if "Size:" in line:
                    size_str = line.split(":", 1)[1].strip()
                elif "BitLocker Version:" in line:
                    version = line.split(":", 1)[1].strip()
                elif "Conversion Status:" in line:
                    conversion = line.split(":", 1)[1].strip()
                elif "Percentage Encrypted:" in line:
                    pct_str = line.split(":", 1)[1].strip().replace("%", "")
                    try:
                        percent = float(pct_str)
                    except ValueError:
                        percent = 0.0
                elif "Encryption Method:" in line:
                    cipher = line.split(":", 1)[1].strip()
                elif "Protection Status:" in line:
                    protection = line.split(":", 1)[1].strip()
                elif "Lock Status:" in line:
                    lock = line.split(":", 1)[1].strip()
                elif "Key Protectors:" in line:
                    pass
                elif any(
                    kp in line
                    for kp in ["TPM", "Numerical Password", "Password", "Recovery Key", "External Key"]
                ):
                    protectors.append(line.strip())

            volumes.append(
                EncryptedVolumeInfo(
                    drive_letter=drive_letter,
                    volume_name=vol_name,
                    size_str=size_str,
                    bitlocker_version=version,
                    conversion_status=conversion,
                    percent_encrypted=percent,
                    encryption_method=cipher,
                    protection_status=protection,
                    lock_status=lock,
                    key_protectors=protectors,
                )
            )

        return volumes

    def _query_wmi_powershell(self) -> list[EncryptedVolumeInfo]:
        """Fallback querying Get-BitLockerVolume via PowerShell."""
        ps_cmd = (
            "Get-BitLockerVolume | Select-Object MountPoint, VolumeStatus, EncryptionPercentage, "
            "ProtectionStatus, EncryptionMethod, KeyProtector | ConvertTo-Json -Depth 2"
        )
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if res.returncode != 0 or not res.stdout.strip():
                return []
            import json

            data = json.loads(res.stdout)
            if isinstance(data, dict):
                data = [data]

            volumes = []
            for item in data:
                mp = str(item.get("MountPoint", ""))
                pct = float(item.get("EncryptionPercentage", 0.0))
                prot = "Protection On" if item.get("ProtectionStatus") == 1 else "Protection Off"
                method = str(item.get("EncryptionMethod", "Unknown"))
                volumes.append(
                    EncryptedVolumeInfo(
                        drive_letter=mp,
                        volume_name="",
                        size_str="N/A",
                        bitlocker_version="2.0",
                        conversion_status="Encrypted" if pct >= 100.0 else "Decrypted",
                        percent_encrypted=pct,
                        encryption_method=method,
                        protection_status=prot,
                        lock_status="Unlocked",
                        key_protectors=[],
                    )
                )
            return volumes
        except Exception:
            return []
