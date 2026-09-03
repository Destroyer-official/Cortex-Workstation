"""Contracts for on-demand page construction in the premium shell.

Building all 43 pages in ``PremiumMainWindow.__init__`` cost ~2.6 s before the
window could appear, even though a session typically opens a handful of tools.
Pages are now built on first view by :class:`_LazyPageRegistry`.

These tests pin both halves of that change:

* the laziness itself (an unvisited page must not be constructed), and
* the backwards-compatible mapping contract, because call sites and older tests
  treat ``win._pages`` as a plain ``dict[str, QWidget]``.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow
    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    yield win
    win.close()


def test_only_the_initial_page_is_built_at_startup(window):
    """Startup must construct the landing page and nothing else."""
    built = window._pages.built_ids
    assert built == {"dashboard"}, (
        f"expected only the dashboard at startup, got {sorted(built)}")


def test_registry_reports_every_page_without_building_them(window):
    """``len``/iteration/``in`` must describe all pages, not just built ones."""
    from cortex_unified.ui.premium import registry
    from cortex_unified.ui.premium.window import _NAV

    nav_ids = [pid for pid, _label, _glyph in _NAV]
    assert len(window._pages) == len(nav_ids) == len(registry.PAGES)
    assert set(window._pages) == set(nav_ids)
    # Iteration order follows navigation so it matches what the user sees.
    assert list(window._pages) == nav_ids
    for pid in nav_ids:
        assert pid in window._pages
    # Describing the pages must not have constructed them.
    assert window._pages.built_ids == {"dashboard"}


def test_getitem_builds_on_demand_and_caches(window):
    """Indexing behaves like a dict and returns a stable widget instance."""
    assert not window._pages.is_built("firewall")
    page = window._pages["firewall"]
    assert isinstance(page, QWidget)
    assert window._pages.is_built("firewall")
    # Same object on a second read - never rebuilt.
    assert window._pages["firewall"] is page


def test_selecting_a_page_builds_it_and_shows_it(window):
    """Navigation must build the target page and make it current."""
    assert not window._pages.is_built("landevices")
    window._select("landevices")
    assert window._pages.is_built("landevices")
    assert window._stack.currentWidget() is window._pages["landevices"]


def test_navigation_works_for_every_page(window):
    """Every page must build and become current when selected."""
    for pid in list(window._pages):
        window._select(pid)
        assert window._stack.currentWidget() is window._pages[pid], pid
    # After visiting everything, all pages are built.
    assert window._pages.built_ids == set(window._pages)


def test_unknown_page_id_raises_key_error(window):
    """A typo must fail loudly rather than silently build nothing."""
    with pytest.raises(KeyError):
        window._pages["no-such-page"]


def test_selecting_unknown_page_is_ignored(window):
    """``_select`` guards on the nav registry and must not raise."""
    current = window._stack.currentWidget()
    window._select("no-such-page")
    assert window._stack.currentWidget() is current


def test_page_factory_registry_matches_navigation():
    """A page in navigation without a factory would fail only on click."""
    from cortex_unified.ui.premium.window import _NAV, _PAGE_FACTORIES

    nav_ids = {pid for pid, _label, _glyph in _NAV}
    assert set(_PAGE_FACTORIES) == nav_ids


def test_lazily_built_page_is_added_to_the_stack(window):
    """A page must be parented into the stack, or it would never display."""
    before = window._stack.count()
    page = window._pages["telemetry"]
    assert window._stack.count() == before + 1
    assert window._stack.indexOf(page) >= 0
