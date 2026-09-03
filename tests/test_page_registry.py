"""Contracts for the declarative page registry.

Navigation was previously three hand-synchronised structures in ``window.py``
(``_NAV`` for order/labels/icons, ``_NAV_GROUPS`` for the sidebar hierarchy, and
``_PAGE_FACTORIES`` for construction), policed by a runtime ``RuntimeError``
that existed only to catch the inevitable desync. Adding one tool meant editing
three places correctly.

A page is now declared once as a :class:`PageSpec`, and everything else is
derived. These tests pin that property, so nobody reintroduces a second source
of truth.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cortex_unified.ui.premium import registry  # noqa: E402


def test_registry_is_internally_consistent():
    """Ids unique, groups known, factories well formed."""
    ids = [spec.id for spec in registry.PAGES]
    assert len(ids) == len(set(ids)), "duplicate page id"
    group_ids = {group.id for group in registry.GROUPS}
    for spec in registry.PAGES:
        assert spec.group in group_ids, spec.id
        assert ":" in spec.factory, spec.id
        assert spec.title and spec.icon, spec.id


def test_every_declared_factory_actually_resolves():
    """A typo must fail here, not when a user clicks the tool."""
    for spec in registry.PAGES:
        cls = spec.load()
        assert isinstance(cls, type), spec.id
        assert cls.__name__.endswith("Page"), spec.id


def test_malformed_factory_is_rejected_with_a_clear_message():
    """test_malformed_factory_is_rejected_with_a_clear_message."""
    bad = registry.PageSpec("x", "X", "!", registry.GROUPS[0].id, "no-colon")
    with pytest.raises(ValueError, match="malformed factory"):
        bad.load()


def test_ordering_is_group_order_then_declaration_order():
    """Sidebar order must be predictable and total."""
    expected: list[str] = []
    for group in registry.GROUPS:
        expected += [s.id for s in registry.PAGES if s.group == group.id]
    assert list(registry.ordered_ids()) == expected
    # Every page appears exactly once.
    assert len(registry.ordered_ids()) == len(registry.PAGES)


def test_grouped_covers_every_page_exactly_once():
    """test_grouped_covers_every_page_exactly_once."""
    seen: list[str] = []
    for group, specs in registry.grouped():
        assert specs, f"group {group.id} has no pages"
        seen += [s.id for s in specs]
    assert sorted(seen) == sorted(spec.id for spec in registry.PAGES)


def test_by_id_and_group_of_agree_with_pages():
    """test_by_id_and_group_of_agree_with_pages."""
    for spec in registry.PAGES:
        assert registry.BY_ID[spec.id] is spec
        assert registry.group_of(spec.id) == spec.group


def test_default_page_exists_and_is_reachable():
    """test_default_page_exists_and_is_reachable."""
    assert registry.DEFAULT_PAGE_ID in registry.BY_ID


# --- the shell must derive from the registry, not duplicate it -------------

def test_window_aliases_are_derived_from_the_registry():
    """``_NAV``/``_NAV_GROUPS``/``_PAGE_FACTORIES`` are views, not sources."""
    from cortex_unified.ui.premium import window

    assert [pid for pid, _t, _i in window._NAV] == list(registry.ordered_ids())
    flattened = [
        pid for _gid, _title, pids in window._NAV_GROUPS for pid in pids
    ]
    assert flattened == list(registry.ordered_ids())
    assert set(window._PAGE_FACTORIES) == set(registry.BY_ID)


def test_adding_one_spec_wires_nav_group_search_and_stack(monkeypatch):
    """A single declaration must be sufficient to add a working tool."""
    from PySide6.QtWidgets import QApplication

    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow

    extra = registry.PageSpec(
        id="registry_probe",
        title="Registry Probe",
        icon="\u2692",
        group="system",
        factory="cortex_unified.ui.premium.window:SettingsPage",
    )
    monkeypatch.setattr(registry, "PAGES", registry.PAGES + (extra,))
    monkeypatch.setattr(
        registry, "BY_ID", {s.id: s for s in registry.PAGES})

    app = QApplication.instance() or QApplication([])
    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    try:
        assert "registry_probe" in win._nav_buttons_by_page
        assert win._nav_sections_by_page["registry_probe"] == "system"
        assert "registry_probe" in win._nav_sections["system"]["pages"]
        win._select("registry_probe")
        assert win._stack.currentWidget() is win._pages["registry_probe"]
    finally:
        win.close()
