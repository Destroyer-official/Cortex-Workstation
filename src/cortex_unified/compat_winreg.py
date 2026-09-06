"""Cross-platform compatibility wrapper for winreg.

Provides standard winreg constants and stub functions when running on non-Windows
platforms or in environments where the native C winreg extension is unavailable.
"""
from __future__ import annotations

import sys
import types

try:
    import winreg
    HAS_WINREG = True
except (ImportError, ModuleNotFoundError):
    winreg = None  # type: ignore
    HAS_WINREG = False

if winreg is None or "winreg" not in sys.modules or sys.modules["winreg"] is None:
    _stub = types.ModuleType("winreg")
    _stub.REG_NONE = 0
    _stub.REG_SZ = 1
    _stub.REG_EXPAND_SZ = 2
    _stub.REG_BINARY = 3
    _stub.REG_DWORD = 4
    _stub.REG_DWORD_LITTLE_ENDIAN = 4
    _stub.REG_DWORD_BIG_ENDIAN = 5
    _stub.REG_LINK = 6
    _stub.REG_MULTI_SZ = 7
    _stub.REG_RESOURCE_LIST = 8
    _stub.REG_FULL_RESOURCE_DESCRIPTOR = 9
    _stub.REG_RESOURCE_REQUIREMENTS_LIST = 10
    _stub.REG_QWORD = 11
    _stub.REG_QWORD_LITTLE_ENDIAN = 11
    _stub.HKEY_CLASSES_ROOT = 0x80000000
    _stub.HKEY_CURRENT_USER = 0x80000001
    _stub.HKEY_LOCAL_MACHINE = 0x80000002
    _stub.HKEY_USERS = 0x80000003
    _stub.HKEY_PERFORMANCE_DATA = 0x80000004
    _stub.HKEY_CURRENT_CONFIG = 0x80000005
    _stub.HKEY_DYN_DATA = 0x80000006
    _stub.KEY_READ = 0x20019
    _stub.KEY_WRITE = 0x20006
    _stub.KEY_ALL_ACCESS = 0xF003F
    _stub.KEY_SET_VALUE = 0x0002
    _stub.KEY_QUERY_VALUE = 0x0001
    _stub.KEY_ENUMERATE_SUB_KEYS = 0x0008
    _stub.KEY_NOTIFY = 0x0010
    _stub.KEY_CREATE_SUB_KEY = 0x0004
    _stub.KEY_CREATE_LINK = 0x0020
    _stub.KEY_WOW64_64KEY = 0x0100
    _stub.KEY_WOW64_32KEY = 0x0200

    def _unsupported(*args, **kwargs):
        """Raise OSError indicating winreg operations are unsupported on non-Windows platforms."""
        raise OSError("winreg operations are only supported on Windows")

    _stub.OpenKey = _unsupported
    _stub.CloseKey = _unsupported
    _stub.QueryValueEx = _unsupported
    _stub.SetValueEx = _unsupported
    _stub.EnumValue = _unsupported
    _stub.EnumKey = _unsupported
    _stub.CreateKey = _unsupported
    _stub.DeleteKey = _unsupported
    _stub.DeleteValue = _unsupported

    sys.modules["winreg"] = _stub
    winreg = _stub
