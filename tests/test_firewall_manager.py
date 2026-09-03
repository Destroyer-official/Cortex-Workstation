"""Tests for the Windows Firewall manager (validation, parsing, safety).

We do NOT create real firewall rules here (that needs admin and mutates the
system). We test input validation, PowerShell quoting/escaping, JSON parsing,
and platform gating.
"""

from __future__ import annotations

import platform

from cortex_unified.system_tools.firewall_manager import FirewallManager, FirewallRule

IS_WINDOWS = platform.system() == "Windows"


class TestGating:
    """TestGating."""
    def test_is_supported_matches_platform(self):
        """test_is_supported_matches_platform."""
        assert FirewallManager.is_supported() == IS_WINDOWS

    def test_list_returns_list(self):
        """test_list_returns_list."""
        assert isinstance(FirewallManager().list_rules(), list)


class TestAddressValidation:
    """TestAddressValidation."""
    def test_valid_ipv4(self):
        """test_valid_ipv4."""
        assert FirewallManager._valid_address("8.8.8.8") is True

    def test_valid_cidr(self):
        """test_valid_cidr."""
        assert FirewallManager._valid_address("192.168.0.0/24") is True

    def test_valid_range(self):
        """test_valid_range."""
        assert FirewallManager._valid_address("10.0.0.1-10.0.0.50") is True

    def test_valid_ipv6(self):
        """test_valid_ipv6."""
        assert FirewallManager._valid_address("2001:4860:4860::8888") is True

    def test_invalid_rejected(self):
        """test_invalid_rejected."""
        assert FirewallManager._valid_address("not-an-ip") is False
        assert FirewallManager._valid_address("") is False

    def test_block_bad_address_refused(self):
        """test_block_bad_address_refused."""
        ok, msg = FirewallManager().block_remote_address("garbage")
        assert ok is False
        assert "invalid" in msg.lower()


class TestQuoting:
    """TestQuoting."""
    def test_escapes_single_quotes(self):
        # Prevent PowerShell injection through crafted display names/paths.
        """test_escapes_single_quotes."""
        q = FirewallManager._ps_quote("C:\\evil'; Remove-Item C:\\ -Recurse #")
        assert q.startswith("'") and q.endswith("'")
        assert "''" in q  # the embedded quote was doubled (escaped)

    def test_simple_value(self):
        """test_simple_value."""
        assert FirewallManager._ps_quote("hello") == "'hello'"


class TestParsing:
    """TestParsing."""
    def test_empty(self):
        """test_empty."""
        assert FirewallManager._parse_rules(None) == []
        assert FirewallManager._parse_rules("") == []
        assert FirewallManager._parse_rules("not json") == []

    def test_single_rule(self):
        """test_single_rule."""
        payload = (
            '{"Name":"{abc}","Disp":"Cortex Cleaner: Block chrome","Dir":"Outbound",'
            '"Act":"Block","En":true,"App":"C:\\\\chrome.exe","Addr":"Any","Proto":null}'
        )
        rules = FirewallManager._parse_rules(payload)
        assert len(rules) == 1
        r = rules[0]
        assert isinstance(r, FirewallRule)
        assert r.action == "Block"
        assert r.enabled is True
        assert r.managed_by_cortex is True
        assert r.remote_address == ""   # "Any" normalized away

    def test_non_cortex_rule_flagged_false(self):
        """test_non_cortex_rule_flagged_false."""
        payload = '{"Name":"x","Disp":"Core Networking","Dir":"Inbound","Act":"Allow","En":true}'
        r = FirewallManager._parse_rules(payload)[0]
        assert r.managed_by_cortex is False

    def test_array(self):
        """test_array."""
        payload = (
            '[{"Name":"a","Disp":"Cortex Cleaner: Block x","Dir":"Outbound","Act":"Block","En":true},'
            '{"Name":"b","Disp":"Cortex Cleaner: Allow y","Dir":"Outbound","Act":"Allow","En":false}]'
        )
        rules = FirewallManager._parse_rules(payload)
        assert len(rules) == 2
        assert rules[1].enabled is False


class TestDirectionGuard:
    """TestDirectionGuard."""
    def test_bad_direction_rejected(self):
        """test_bad_direction_rejected."""
        if not IS_WINDOWS:
            import pytest
            pytest.skip("Windows-only path")
        ok, msg = FirewallManager()._new_rule("Block", "Sideways", "x", program="c:\\a.exe")
        assert ok is False
