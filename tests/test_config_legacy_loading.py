"""Failure-reporting contracts for the legacy YAML config loader.

The loader must stay forgiving (a broken config never crashes the app) while
becoming *honest* (it says why it fell back to defaults). Previously every
failure was swallowed by a bare ``except Exception: return {}``, so a user with
a typo in their YAML saw their settings silently ignored.

All tests use ``tmp_path``; nothing touches the real user config.
"""

from __future__ import annotations

import logging

import pytest

from cortex_unified.core.config import DEFAULT_CONFIG, Config


def test_missing_file_is_silent_and_yields_defaults(tmp_path, caplog):
    """An absent config is the normal case - defaults apply, no warning."""
    target = tmp_path / "nope.yaml"
    with caplog.at_level(logging.WARNING, logger="cortex.core.config"):
        cfg = Config(str(target))
    assert cfg.config_data == DEFAULT_CONFIG
    assert caplog.records == []


def test_valid_yaml_is_loaded_over_the_defaults(tmp_path):
    """test_valid_yaml_is_loaded_over_the_defaults."""
    path = tmp_path / "ok.yaml"
    path.write_text("exclude_dirs:\n  - node_modules\n", encoding="utf-8")
    cfg = Config(str(path))
    assert cfg.exclude_dirs == ["node_modules"]
    # The specified key is replaced; everything else comes from the defaults.
    expected = dict(DEFAULT_CONFIG, exclude_dirs=["node_modules"])
    assert cfg.config_data == expected


def test_malformed_yaml_warns_and_falls_back(tmp_path, caplog):
    """A syntax error must be reported, not silently ignored."""
    path = tmp_path / "bad.yaml"
    path.write_text("exclude_dirs: [unclosed\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="cortex.core.config"):
        cfg = Config(str(path))
    assert cfg.config_data == DEFAULT_CONFIG          # still usable and safe
    assert any("not valid YAML" in r.message for r in caplog.records)


def test_non_mapping_top_level_warns_and_falls_back(tmp_path, caplog):
    """A YAML list/scalar at the top level is a user mistake worth reporting."""
    path = tmp_path / "list.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="cortex.core.config"):
        cfg = Config(str(path))
    assert cfg.config_data == DEFAULT_CONFIG
    assert any("mapping at the top level" in r.message for r in caplog.records)


def test_empty_file_is_treated_as_no_settings(tmp_path, caplog):
    """An empty file parses to None; that is defaults, not an error."""
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="cortex.core.config"):
        cfg = Config(str(path))
    assert cfg.config_data == DEFAULT_CONFIG
    assert caplog.records == []


def test_non_utf8_bytes_warn_and_fall_back(tmp_path, caplog):
    """Explicit UTF-8 decoding means bad bytes are reported, not locale-luck."""
    path = tmp_path / "latin.yaml"
    # 0xFF is not valid UTF-8, so this must be reported as a read failure.
    path.write_bytes(b"exclude_dirs:\n  - caf\xff\n")
    with caplog.at_level(logging.WARNING, logger="cortex.core.config"):
        cfg = Config(str(path))
    assert cfg.config_data == DEFAULT_CONFIG
    assert any("could not read config" in r.message for r in caplog.records)


def test_unicode_paths_load_correctly(tmp_path):
    """Non-ASCII config content must load regardless of system locale."""
    path = tmp_path / "unicode.yaml"
    path.write_text("exclude_dirs:\n  - \u30c6\u30b9\u30c8\n", encoding="utf-8")
    cfg = Config(str(path))
    assert cfg.exclude_dirs == ["\u30c6\u30b9\u30c8"]


# --- DEFAULT_CONFIG must actually be the baseline (safety) ---------------
#
# DEFAULT_CONFIG declares .git / node_modules / __pycache__ as excluded, but
# the properties used to fall back to ``[]``, so with no config file those
# directories were NOT protected from cleanup. Two CLI commands merged the
# defaults by hand; the other seven and every analyzer did not.

_PROTECTED = (".git", "node_modules", "__pycache__")


@pytest.mark.parametrize("name", _PROTECTED)
def test_protected_directories_are_excluded_by_default(tmp_path, name):
    """With no config file, the safety exclusions must still apply."""
    cfg = Config(str(tmp_path / "absent.yaml"))
    assert cfg.matches_exclude_patterns(str(tmp_path / name)), (
        f"{name} must be excluded by default; deleting inside it can corrupt "
        "a repository or a dependency tree"
    )


def test_defaults_are_the_baseline_when_no_file_exists(tmp_path):
    """test_defaults_are_the_baseline_when_no_file_exists."""
    cfg = Config(str(tmp_path / "absent.yaml"))
    assert cfg.exclude_dirs == DEFAULT_CONFIG["exclude_dirs"]
    assert cfg.exclude_patterns == DEFAULT_CONFIG["exclude_patterns"]
    assert cfg.exclude_regex_patterns == DEFAULT_CONFIG["exclude_regex_patterns"]


def test_defaults_still_apply_when_the_file_is_broken(tmp_path, caplog):
    """A malformed file must not silently drop the safety exclusions."""
    path = tmp_path / "bad.yaml"
    path.write_text("exclude_dirs: [unclosed\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="cortex.core.config"):
        cfg = Config(str(path))
    assert cfg.exclude_dirs == DEFAULT_CONFIG["exclude_dirs"]
    assert any("not valid YAML" in r.message for r in caplog.records)


def test_user_settings_override_defaults_key_by_key(tmp_path):
    """An explicit list replaces the default; untouched keys are inherited."""
    path = tmp_path / "c.yaml"
    path.write_text("exclude_dirs:\n  - only_mine\nmin_age_days: 30\n",
                    encoding="utf-8")
    cfg = Config(str(path))
    assert cfg.exclude_dirs == ["only_mine"]      # replaced
    assert cfg.min_age_days == 30                 # replaced
    # Not mentioned in the file -> default retained.
    assert cfg.exclude_regex_patterns == DEFAULT_CONFIG["exclude_regex_patterns"]
    assert cfg.default_action == DEFAULT_CONFIG["default_action"]


def test_config_data_is_mutable_without_corrupting_other_instances(tmp_path):
    """The CLI applies overrides by assigning into ``config_data``.

    That must not leak into ``DEFAULT_CONFIG`` or into later instances, which
    a shared nested list would cause.
    """
    first = Config(str(tmp_path / "absent.yaml"))
    first.config_data["exclude_dirs"].append("leaked")
    first.config_data["exclude_patterns"] = ["replaced"]

    second = Config(str(tmp_path / "absent.yaml"))
    assert "leaked" not in second.exclude_dirs
    assert second.exclude_patterns == DEFAULT_CONFIG["exclude_patterns"]
    assert "leaked" not in DEFAULT_CONFIG["exclude_dirs"]
