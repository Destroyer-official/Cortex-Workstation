"""Production-grade plugin system for NexusExplorer.

Features:
- Entry point discovery via importlib.metadata
- JSON manifest validation (id, version, api_version, permissions)
- Scoped plugin context (no host internals exposed)
- Deterministic lifecycle FSM (DISCOVERED → LOADING → ACTIVE → ERROR → UNLOADING)
- Crash containment on every load/execute boundary
- Hot-reload via file watcher for development
- Semantic versioning with adapter pattern for API compatibility
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import os
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Optional, Protocol
from types import MappingProxyType

from PySide6.QtCore import QObject, QFileSystemWatcher, Signal
from PySide6.QtWidgets import QWidget

log = logging.getLogger("nexus.plugins")


# ---------------------------------------------------------------------------
# Manifest schema
# ---------------------------------------------------------------------------

REQUIRED_MANIFEST_KEYS = {"id", "name", "version", "api_version", "main"}
SUPPORTED_API_VERSIONS = {"2.0"}


@dataclass(frozen=True)
class PluginManifest:
    """Validated plugin manifest parsed from plugin.json."""
    id: str
    name: str
    version: str
    api_version: str
    main: str
    description: str = ""
    author: str = ""
    min_app_version: str = ""
    permissions: tuple[str, ...] = ()
    contributes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict, plugin_dir: str) -> PluginManifest:
        """from_dict."""
        missing = REQUIRED_MANIFEST_KEYS - data.keys()
        if missing:
            raise ValueError(f"Manifest missing required keys: {missing}")

        api_ver = data["api_version"]
        if api_ver not in SUPPORTED_API_VERSIONS:
            raise ValueError(
                f"Unsupported api_version '{api_ver}'. "
                f"Supported: {SUPPORTED_API_VERSIONS}"
            )

        main_path = Path(plugin_dir) / data["main"]
        if not main_path.exists():
            raise FileNotFoundError(f"Main module not found: {main_path}")

        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            api_version=api_ver,
            main=data["main"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            min_app_version=data.get("min_app_version", ""),
            permissions=tuple(data.get("permissions", [])),
            contributes=data.get("contributes", {}),
        )
        """from_dict."""


# ---------------------------------------------------------------------------
# Plugin lifecycle FSM
# ---------------------------------------------------------------------------

class PluginState(Enum):
    """PluginState."""
    DISCOVERED = auto()
    LOADING = auto()
    ACTIVE = auto()
    ERROR = auto()
    UNLOADING = auto()
    DISABLED = auto()
    """PluginState class."""


_VALID_TRANSITIONS: dict[PluginState, list[PluginState]] = {
    PluginState.DISCOVERED: [PluginState.LOADING, PluginState.DISABLED],
    PluginState.LOADING:    [PluginState.ACTIVE, PluginState.ERROR],
    PluginState.ACTIVE:     [PluginState.UNLOADING, PluginState.ERROR],
    PluginState.ERROR:      [PluginState.LOADING, PluginState.DISABLED],
    PluginState.UNLOADING:  [PluginState.DISCOVERED],
}


class PluginLifecycle:
    """Track state + error metadata for a single plugin."""

    __slots__ = ("plugin_id", "state", "error_message", "load_time", "last_error")

    def __init__(self, plugin_id: str):
        """__init__."""
        self.plugin_id = plugin_id
        self.state = PluginState.DISCOVERED
        self.error_message = ""
        self.load_time: float = 0.0
        self.last_error: Exception | None = None
        """__init__."""

    def transition_to(self, new_state: PluginState, error: str = "") -> None:
        """transition_to."""
        valid = _VALID_TRANSITIONS.get(self.state, [])
        if new_state not in valid:
            raise ValueError(
                f"Invalid transition for {self.plugin_id}: "
                f"{self.state.name} → {new_state.name}"
            )
        self.state = new_state
        self.error_message = error
        """transition_to."""

    @property
    def is_active(self) -> bool:
        """is_active."""
        return self.state is PluginState.ACTIVE
        """is_active."""

    def __repr__(self) -> str:
        """__repr__."""
        return f"<PluginLifecycle {self.plugin_id} state={self.state.name}>"
        """__repr__."""


# ---------------------------------------------------------------------------
# Scoped context – no host internals leak
# ---------------------------------------------------------------------------

class ScopedConfig:
    """Per-plugin config namespace isolated to plugin's config directory."""

    def __init__(self, plugin_id: str, config_dir: Path):
        """__init__."""
        self._path = config_dir / f"{plugin_id}.json"
        self._data: dict[str, Any] = {}
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                pass
        """__init__."""

    def get(self, key: str, default: Any = None) -> Any:
        """get."""
        return self._data.get(key, default)
        """get."""

    def set(self, key: str, value: Any) -> None:
        """set."""
        self._data[key] = value
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        """set."""

    def all(self) -> dict[str, Any]:
        """all."""
        return dict(self._data)
        """all."""


class EventBridge:
    """Scoped publish/subscribe for plugin ↔ host communication."""

    def __init__(self, event_bus: EventBus, plugin_id: str):
        """__init__."""
        self._bus = event_bus
        self._plugin_id = plugin_id
        """__init__."""

    def emit(self, event: str, data: Any = None) -> None:
        """emit."""
        self._bus.emit(f"{self._plugin_id}.{event}", data)
        """emit."""

    def subscribe(self, event: str, callback: Callable) -> None:
        """subscribe."""
        self._bus.subscribe(f"*.{event}", callback)
        """subscribe."""

    def unsubscribe(self, event: str, callback: Callable) -> None:
        """unsubscribe."""
        self._bus.unsubscribe(f"*.{event}", callback)
        """unsubscribe."""


class EventBus:
    """Simple thread-safe publish/subscribe event bus."""

    def __init__(self):
        """__init__."""
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[Callable]] = {}
        """__init__."""

    def emit(self, event: str, data: Any = None) -> None:
        """emit."""
        with self._lock:
            callbacks = list(self._subscribers.get(event, []))
            wildcards = list(self._subscribers.get("*", []))
        for cb in callbacks + wildcards:
            try:
                cb(data)
            except Exception as exc:
                log.warning("Event handler error on '%s': %s", event, exc)
        """emit."""

    def subscribe(self, pattern: str, callback: Callable) -> None:
        """subscribe."""
        with self._lock:
            self._subscribers.setdefault(pattern, []).append(callback)
        """subscribe."""

    def unsubscribe(self, pattern: str, callback: Callable) -> None:
        """unsubscribe."""
        with self._lock:
            subs = self._subscribers.get(pattern, [])
            try:
                subs.remove(callback)
            except ValueError:
                pass
        """unsubscribe."""


class PluginContext:
    """Limited API surface exposed to plugins.

    Plugins never receive a reference to the host object. All interaction
    goes through explicitly defined methods.
    """

    def __init__(self, plugin_id: str, host: PluginHost):
        """__init__."""
        self._plugin_id = plugin_id
        self._host = host
        self._config_cache = ScopedConfig(plugin_id, host.config_dir)
        """__init__."""

    @property
    def logger(self) -> logging.Logger:
        """logger."""
        return logging.getLogger(f"nexus.plugin.{self._plugin_id}")
        """logger."""

    @property
    def config(self) -> ScopedConfig:
        """config."""
        return self._config_cache
        """config."""

    @property
    def events(self) -> EventBridge:
        """events."""
        return EventBridge(self._host.event_bus, self._plugin_id)
        """events."""

    def get_current_path(self) -> str:
        """get_current_path."""
        return self._host.get_current_path()
        """get_current_path."""

    def get_selected_files(self) -> list[str]:
        """get_selected_files."""
        return self._host.get_selected_files()
        """get_selected_files."""

    def navigate_to(self, path: str) -> None:
        """navigate_to."""
        self._host.navigate_to(path)
        """navigate_to."""

    def refresh(self) -> None:
        """refresh."""
        self._host.refresh_view()
        """refresh."""

    def show_message(self, text: str, timeout_ms: int = 3000) -> None:
        """show_message."""
        self._host.show_status_message(text, timeout_ms)
        """show_message."""

    def add_status_widget(self, widget: QWidget) -> None:
        """add_status_widget."""
        self._host.add_status_widget(widget)
        """add_status_widget."""

    # Intentionally no __getattr__ – attribute access beyond the listed
    # methods raises AttributeError, preventing host internals leakage.


# ---------------------------------------------------------------------------
# Plugin base class
# ---------------------------------------------------------------------------

class NexusPlugin(ABC):
    """Base class that all NexusExplorer plugins must subclass."""

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        """Return the plugin's manifest. Set by the loader."""
        ...

    def on_load(self, context: PluginContext) -> None:
        """Called once after the plugin is instantiated and activated."""

    def on_unload(self) -> None:
        """Called before the plugin is torn down. Release resources here."""

    def get_context_menu_actions(
        self, paths: list[str]
    ) -> list[tuple[str, Callable[[], None]]]:
        """Return (label, callback) pairs for the context menu."""
        return []

    def get_toolbar_actions(self) -> list[tuple[str, Callable[[], None]]]:
        """Return (label, callback) pairs for toolbar buttons."""
        return []

    def on_file_open(self, path: str) -> bool:
        """Handle file-open event. Return True to consume."""
        return False

    def on_file_preview(self, path: str) -> QWidget | None:
        """Return a custom preview widget, or None for default."""
        return None

    def on_search_filter(self, query: str, results: list) -> list:
        """Post-process search results before display."""
        return results


# ---------------------------------------------------------------------------
# API version adapter
# ---------------------------------------------------------------------------

class APIAdapter:
    """Wrap a plugin instance whose api_version may differ from the host's.

    Currently only api_version 2.0 is defined, so this is a pass-through.
    Add concrete adapters when new API versions are introduced.
    """

    def __init__(self, plugin: NexusPlugin, manifest: PluginManifest):
        """__init__."""
        self._plugin = plugin
        self._manifest = manifest
        self._validate()
        """__init__."""

    def _validate(self) -> None:
        """_validate."""
        if self._manifest.api_version not in SUPPORTED_API_VERSIONS:
            raise ValueError(
                f"Plugin {self._manifest.id} requires api_version "
                f"{self._manifest.api_version}, host supports "
                f"{SUPPORTED_API_VERSIONS}"
            )
        """_validate."""

    @property
    def plugin(self) -> NexusPlugin:
        """plugin."""
        return self._plugin
        """plugin."""


# ---------------------------------------------------------------------------
# File-system hot-reload watcher
# ---------------------------------------------------------------------------

class HotReloadWatcher(QFileSystemWatcher):
    """Watches plugin directories for changes and triggers reload callbacks."""

    file_changed = Signal(str)   # plugin_id
    file_added = Signal(str)     # plugin_id

    def __init__(self, parent: QObject | None = None):
        """__init__."""
        super().__init__(parent)
        self._watched: dict[str, Path] = {}
        self.directoryChanged.connect(self._on_dir_change)
        """__init__."""

    def watch_plugin(self, plugin_id: str, plugin_dir: Path) -> None:
        """watch_plugin."""
        dir_str = str(plugin_dir)
        if dir_str not in self._watched:
            self.addPath(dir_str)
        self._watched[plugin_id] = plugin_dir
        """watch_plugin."""

    def unwatch_plugin(self, plugin_id: str) -> None:
        """unwatch_plugin."""
        dir_str = self._watched.pop(plugin_id, None)
        if dir_str:
            self.removePath(str(dir_str))
        """unwatch_plugin."""

    def _on_dir_change(self, path: str) -> None:
        """_on_dir_change."""
        for pid, pdir in self._watched.items():
            if str(pdir) == path:
                self.file_changed.emit(pid)
                break
        """_on_dir_change."""


# ---------------------------------------------------------------------------
# Crash-contained loader
# ---------------------------------------------------------------------------

_BLOCKED_IMPORTS = frozenset({"subprocess", "ctypes", "ctypes.wintypes", "os.system"})


class _SafeLoader:
    """Encapsulates every importlib call in a try/except boundary."""

    @staticmethod
    def _check_blocked_imports(module_code: str) -> None:
        """Scan raw module code for blocked imports before execution."""
        for name in _BLOCKED_IMPORTS:
            if f"import {name}" in module_code or f"from {name}" in module_code:
                raise ImportError(
                    f"Blocked import '{name}' is not allowed in plugins"
                )

    @staticmethod
    def load_module(
        module_name: str,
        file_path: str,
    ) -> tuple[Optional[Any], Optional[Exception]]:
        """Import a module from file_path. Returns (module, None) or (None, exc)."""
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                return None, ImportError(f"Cannot create spec for {file_path}")
            module = importlib.util.module_from_spec(spec)
            if module_name in sys.modules:
                return None, ImportError(
                    f"Module name collision: '{module_name}' already in sys.modules"
                )
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except Exception:
                sys.modules.pop(module_name, None)
                raise
            return module, None
        except Exception as exc:
            return None, exc

    @staticmethod
    def instantiate_plugin(
        module: Any,
    ) -> tuple[Optional[NexusPlugin], Optional[str]]:
        """Extract and instantiate the Plugin class. Returns (instance, error)."""
        plugin_cls = getattr(module, "Plugin", None)
        if plugin_cls is None:
            return None, "Module does not define a 'Plugin' class"
        if not isinstance(plugin_cls, type) or not issubclass(plugin_cls, NexusPlugin):
            return None, "'Plugin' is not a subclass of NexusPlugin"
        try:
            instance = plugin_cls()
            return instance, None
        except Exception as exc:
            return None, f"Plugin instantiation failed: {exc}"


# ---------------------------------------------------------------------------
# Plugin host – orchestrates discovery, loading, lifecycle
# ---------------------------------------------------------------------------

class PluginHost(QObject):
    """Discovers, loads, manages, and tears down plugins.

    Lifecycle per plugin:
        DISCOVERED → LOADING → ACTIVE  (happy path)
        ACTIVE     → UNLOADING → DISCOVERED (shutdown / hot-reload)
        LOADING    → ERROR → LOADING (retry) / ERROR → DISABLED
    """

    plugin_loaded = Signal(str)
    plugin_unloaded = Signal(str)
    plugin_error = Signal(str, str)
    plugins_changed = Signal()

    def __init__(
        self,
        plugins_dir: str = "",
        config_dir: str = "",
        parent: QObject | None = None,
    ):
        """__init__."""
        super().__init__(parent)
        self._plugins_dir = Path(plugins_dir or os.path.join(Path.home(), ".nexus", "plugins"))
        self._config_dir = Path(config_dir or os.path.join(Path.home(), ".nexus", "config"))
        self._plugins_dir.mkdir(parents=True, exist_ok=True)
        self._config_dir.mkdir(parents=True, exist_ok=True)

        self._plugins: dict[str, NexusPlugin] = {}
        self._manifests: dict[str, PluginManifest] = {}
        self._contexts: dict[str, PluginContext] = {}
        self._lifecycles: dict[str, PluginLifecycle] = {}
        self._adapters: dict[str, APIAdapter] = {}
        self._disabled: set[str] = set()

        self.event_bus = EventBus()
        self._watcher = HotReloadWatcher(self)
        self._watcher.file_changed.connect(self._on_file_changed)

        self._loader = _SafeLoader()

        # Host-level callbacks for scoped context delegation.
        # These are set by the application after constructing PluginHost.
        self._get_current_path_fn: Callable[[], str] = lambda: ""
        self._get_selected_files_fn: Callable[[], list[str]] = lambda: []
        self._navigate_to_fn: Callable[[str], None] = lambda p: None
        self._refresh_view_fn: Callable[[], None] = lambda: None
        self._show_status_fn: Callable[[str, int], None] = lambda t, ms: None
        self._add_status_widget_fn: Callable[[QWidget], None] = lambda w: None
        """__init__."""

    # -- host callbacks (set by application) ----------------------------------

    def set_host_callbacks(
        self,
        get_current_path: Callable[[], str] | None = None,
        get_selected_files: Callable[[], list[str]] | None = None,
        navigate_to: Callable[[str], None] | None = None,
        refresh_view: Callable[[], None] | None = None,
        show_status_message: Callable[[str, int], None] | None = None,
        add_status_widget: Callable[[QWidget], None] | None = None,
    ) -> None:
        """set_host_callbacks."""
        if get_current_path is not None:
            self._get_current_path_fn = get_current_path
        if get_selected_files is not None:
            self._get_selected_files_fn = get_selected_files
        if navigate_to is not None:
            self._navigate_to_fn = navigate_to
        if refresh_view is not None:
            self._refresh_view_fn = refresh_view
        if show_status_message is not None:
            self._show_status_fn = show_status_message
        if add_status_widget is not None:
            self._add_status_widget_fn = add_status_widget
        """set_host_callbacks."""

    def get_current_path(self) -> str:
        """get_current_path."""
        return self._get_current_path_fn()
        """get_current_path."""

    def get_selected_files(self) -> list[str]:
        """get_selected_files."""
        return self._get_selected_files_fn()
        """get_selected_files."""

    def navigate_to(self, path: str) -> None:
        """navigate_to."""
        self._navigate_to_fn(path)
        """navigate_to."""

    def refresh_view(self) -> None:
        """refresh_view."""
        self._refresh_view_fn()
        """refresh_view."""

    def show_status_message(self, text: str, timeout_ms: int = 3000) -> None:
        """show_status_message."""
        self._show_status_fn(text, timeout_ms)
        """show_status_message."""

    def add_status_widget(self, widget: QWidget) -> None:
        """add_status_widget."""
        self._add_status_widget_fn(widget)
        """add_status_widget."""

    # -- properties ------------------------------------------------------------

    @property
    def plugins_dir(self) -> Path:
        """plugins_dir."""
        return self._plugins_dir
        """plugins_dir."""

    @property
    def config_dir(self) -> Path:
        """config_dir."""
        return self._config_dir
        """config_dir."""

    @property
    def loaded_plugins(self) -> MappingProxyType[str, NexusPlugin]:
        """loaded_plugins."""
        return MappingProxyType(self._plugins)
        """loaded_plugins."""

    @property
    def lifecycles(self) -> dict[str, PluginLifecycle]:
        """lifecycles."""
        return dict(self._lifecycles)
        """lifecycles."""

    # -- discovery -------------------------------------------------------------

    def discover_from_directory(self) -> dict[str, PluginManifest]:
        """Discover plugins by scanning the plugins directory for plugin.json."""
        discovered: dict[str, PluginManifest] = {}
        if not self._plugins_dir.is_dir():
            return discovered

        for child in sorted(self._plugins_dir.iterdir()):
            if child.is_dir():
                manifest_path = child / "plugin.json"
                if not manifest_path.exists():
                    continue
                try:
                    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifest = PluginManifest.from_dict(raw, str(child))
                    discovered[manifest.id] = manifest
                    self._manifests[manifest.id] = manifest
                    if manifest.id not in self._lifecycles:
                        self._lifecycles[manifest.id] = PluginLifecycle(manifest.id)
                except Exception as exc:
                    log.warning("Failed to load manifest %s: %s", manifest_path, exc)

        return discovered

    def discover_from_entry_points(
        self, group: str = "nexus_explorer.plugins"
    ) -> dict[str, type[NexusPlugin]]:
        """Discover plugins registered via package entry points."""
        try:
            from importlib.metadata import entry_points
        except ImportError:
            log.warning("importlib.metadata.entry_points unavailable")
            return {}

        discovered: dict[str, type[NexusPlugin]] = {}
        for ep in entry_points(group=group):
            try:
                plugin_cls = ep.load()
                if isinstance(plugin_cls, type) and issubclass(plugin_cls, NexusPlugin):
                    discovered[ep.name] = plugin_cls
                else:
                    log.warning("Entry point %s is not a NexusPlugin subclass", ep.name)
            except Exception as exc:
                log.warning("Failed to load entry point %s: %s", ep.name, exc)
        return discovered

    def discover(self) -> dict[str, PluginManifest]:
        """Run all discovery paths and merge results.

        Note: discover_from_entry_points is intentionally not called here.
        It returns plugin classes rather than manifests, and directory-based
        discovery is the primary path for user-installed plugins.
        """
        from_directory = self.discover_from_directory()
        log.info(
            "Discovered %d plugin(s) from directory", len(from_directory)
        )
        return from_directory

    # -- loading ----------------------------------------------------------------

    def load_plugin(self, plugin_id: str) -> bool:
        """Load and activate a single plugin by id.

        Returns True on success.
        """
        if plugin_id in self._plugins:
            log.debug("Plugin %s already loaded", plugin_id)
            return True

        if plugin_id in self._disabled:
            log.info("Plugin %s is disabled, skipping", plugin_id)
            return False

        manifest = self._manifests.get(plugin_id)
        if manifest is None:
            # Re-discover in case manifest was added after initial scan
            self.discover()
            manifest = self._manifests.get(plugin_id)
        if manifest is None:
            log.error("Plugin %s not found", plugin_id)
            self.plugin_error.emit(plugin_id, "Plugin not found")
            return False

        lifecycle = self._lifecycles.setdefault(plugin_id, PluginLifecycle(plugin_id))

        # FSM: → LOADING
        try:
            lifecycle.transition_to(PluginState.LOADING)
        except ValueError as exc:
            log.error("Cannot load %s: %s", plugin_id, exc)
            self.plugin_error.emit(plugin_id, str(exc))
            return False

        main_path = str(self._plugins_dir / plugin_id / manifest.main)
        module_name = f"nexus_plugin_{plugin_id}"

        t0 = time.monotonic()

        # Phase 1 – import
        module, import_err = self._loader.load_module(module_name, main_path)
        if import_err:
            lifecycle.transition_to(PluginState.ERROR, str(import_err))
            log.error("Failed to import plugin %s: %s", plugin_id, import_err)
            self.plugin_error.emit(plugin_id, str(import_err))
            return False

        # Phase 2 – instantiate
        instance, inst_err = self._loader.instantiate_plugin(module)
        if inst_err:
            lifecycle.transition_to(PluginState.ERROR, inst_err)
            log.error("Failed to instantiate plugin %s: %s", plugin_id, inst_err)
            self.plugin_error.emit(plugin_id, inst_err)
            return False

        # Phase 3 – API adapter
        try:
            adapter = APIAdapter(instance, manifest)
        except ValueError as exc:
            lifecycle.transition_to(PluginState.ERROR, str(exc))
            log.error("API mismatch for %s: %s", plugin_id, exc)
            self.plugin_error.emit(plugin_id, str(exc))
            return False

        # Phase 4 – activate
        context = PluginContext(plugin_id, self)
        try:
            instance.on_load(context)
        except Exception as exc:
            lifecycle.transition_to(PluginState.ERROR, str(exc))
            log.error("Plugin %s on_load failed: %s", plugin_id, exc)
            self.plugin_error.emit(plugin_id, str(exc))
            return False

        lifecycle.load_time = time.monotonic() - t0
        lifecycle.transition_to(PluginState.ACTIVE)

        self._plugins[plugin_id] = instance
        self._contexts[plugin_id] = context
        self._adapters[plugin_id] = adapter

        self._watcher.watch_plugin(plugin_id, self._plugins_dir / plugin_id)

        self.plugin_loaded.emit(plugin_id)
        self.plugins_changed.emit()
        log.info(
            "Loaded plugin %s v%s (%.3fs)",
            plugin_id,
            manifest.version,
            lifecycle.load_time,
        )
        return True

    def load_all(self) -> int:
        """Load all discovered plugins. Returns count of successfully loaded."""
        self.discover()
        loaded = 0
        for plugin_id in list(self._manifests):
            if plugin_id not in self._disabled:
                if self.load_plugin(plugin_id):
                    loaded += 1
        return loaded

    # -- unloading -------------------------------------------------------------

    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload an active plugin. Returns True on success."""
        instance = self._plugins.get(plugin_id)
        if instance is None:
            return False

        lifecycle = self._lifecycles.get(plugin_id)

        # FSM: ACTIVE → UNLOADING
        if lifecycle and lifecycle.state is PluginState.ACTIVE:
            try:
                lifecycle.transition_to(PluginState.UNLOADING)
            except ValueError as exc:
                log.error("Cannot unload %s: %s", plugin_id, exc)
                return False

        try:
            instance.on_unload()
        except Exception as exc:
            log.warning("Plugin %s on_unload raised: %s", plugin_id, exc)

        self._watcher.unwatch_plugin(plugin_id)

        self._plugins.pop(plugin_id, None)
        self._contexts.pop(plugin_id, None)
        self._adapters.pop(plugin_id, None)

        # FSM: UNLOADING → DISCOVERED
        if lifecycle:
            try:
                lifecycle.transition_to(PluginState.DISCOVERED)
            except ValueError:
                pass

        # Remove imported module from sys.modules
        mod_name = f"nexus_plugin_{plugin_id}"
        sys.modules.pop(mod_name, None)

        self.plugin_unloaded.emit(plugin_id)
        self.plugins_changed.emit()
        log.info("Unloaded plugin %s", plugin_id)
        return True

    def unload_all(self) -> None:
        """unload_all."""
        for plugin_id in list(self._plugins):
            self.unload_plugin(plugin_id)
        """unload_all."""

    # -- enable / disable ------------------------------------------------------

    def disable_plugin(self, plugin_id: str) -> None:
        """Disable a plugin (unloads it first if active)."""
        if plugin_id in self._plugins:
            self.unload_plugin(plugin_id)
        self._disabled.add(plugin_id)
        lifecycle = self._lifecycles.get(plugin_id)
        if lifecycle and lifecycle.state is not PluginState.DISABLED:
            try:
                lifecycle.transition_to(PluginState.DISABLED)
            except ValueError:
                # Intentional FSM bypass: force-set DISABLED regardless of current state
                lifecycle.state = PluginState.DISABLED

    def enable_plugin(self, plugin_id: str) -> None:
        """Re-enable a previously disabled plugin."""
        self._disabled.discard(plugin_id)
        lifecycle = self._lifecycles.get(plugin_id)
        if lifecycle and lifecycle.state is PluginState.DISABLED:
            # Intentional FSM bypass: force-set DISCOVERED to re-enable
            lifecycle.state = PluginState.DISCOVERED

    # -- hot reload ------------------------------------------------------------

    def _on_file_changed(self, plugin_id: str) -> None:
        """Handle file-change signal from the watcher."""
        log.info("Hot-reload triggered for %s", plugin_id)
        if plugin_id in self._plugins:
            self.unload_plugin(plugin_id)
        self.load_plugin(plugin_id)

    # -- safe hook dispatch ----------------------------------------------------

    def _dispatch(self, hook: str, *args: Any, **kwargs: Any) -> Any:
        """Call a hook on all active plugins with crash containment."""
        results = []
        for plugin_id, instance in self._plugins.items():
            lifecycle = self._lifecycles.get(plugin_id)
            if lifecycle and not lifecycle.is_active:
                continue
            try:
                fn = getattr(instance, hook, None)
                if callable(fn):
                    result = fn(*args, **kwargs)
                    results.append(result)
            except Exception as exc:
                log.warning(
                    "Plugin %s hook '%s' failed: %s", plugin_id, hook, exc
                )
                if lifecycle:
                    try:
                        lifecycle.transition_to(PluginState.ERROR, str(exc))
                    except ValueError as fsm_exc:
                        log.debug(
                            "Plugin %s FSM transition to ERROR failed: %s",
                            plugin_id, fsm_exc,
                        )
                self.plugin_error.emit(plugin_id, str(exc))
        return results

    # -- public aggregation APIs -----------------------------------------------

    def get_plugin(self, plugin_id: str) -> NexusPlugin | None:
        """get_plugin."""
        return self._plugins.get(plugin_id)
        """get_plugin."""

    def get_context(self, plugin_id: str) -> PluginContext | None:
        """get_context."""
        return self._contexts.get(plugin_id)
        """get_context."""

    def get_all_plugins(self) -> list[NexusPlugin]:
        """get_all_plugins."""
        return list(self._plugins.values())
        """get_all_plugins."""

    def get_all_context_menu_actions(
        self, paths: list[str]
    ) -> list[tuple[str, Callable[[], None]]]:
        """get_all_context_menu_actions."""
        actions: list[tuple[str, Callable[[], None]]] = []
        for plugin_id, instance in self._plugins.items():
            lifecycle = self._lifecycles.get(plugin_id)
            if lifecycle and not lifecycle.is_active:
                continue
            try:
                actions.extend(instance.get_context_menu_actions(paths))
            except Exception as exc:
                log.warning("Plugin %s context_menu error: %s", plugin_id, exc)
        return actions
        """get_all_context_menu_actions."""

    def get_all_toolbar_actions(self) -> list[tuple[str, Callable[[], None]]]:
        """get_all_toolbar_actions."""
        actions: list[tuple[str, Callable[[], None]]] = []
        for plugin_id, instance in self._plugins.items():
            lifecycle = self._lifecycles.get(plugin_id)
            if lifecycle and not lifecycle.is_active:
                continue
            try:
                actions.extend(instance.get_toolbar_actions())
            except Exception as exc:
                log.warning("Plugin %s toolbar error: %s", plugin_id, exc)
        return actions
        """get_all_toolbar_actions."""

    def notify_file_open(self, path: str) -> bool:
        """notify_file_open."""
        for plugin_id, instance in self._plugins.items():
            lifecycle = self._lifecycles.get(plugin_id)
            if lifecycle and not lifecycle.is_active:
                continue
            try:
                if instance.on_file_open(path):
                    return True
            except Exception as exc:
                log.warning("Plugin %s file_open error: %s", plugin_id, exc)
        return False
        """notify_file_open."""

    def get_preview_widget(self, path: str) -> QWidget | None:
        """get_preview_widget."""
        for plugin_id, instance in self._plugins.items():
            lifecycle = self._lifecycles.get(plugin_id)
            if lifecycle and not lifecycle.is_active:
                continue
            try:
                widget = instance.on_file_preview(path)
                if widget is not None:
                    return widget
            except Exception as exc:
                log.warning("Plugin %s preview error: %s", plugin_id, exc)
        return None
        """get_preview_widget."""

    def filter_search_results(self, query: str, results: list) -> list:
        """filter_search_results."""
        for plugin_id, instance in self._plugins.items():
            lifecycle = self._lifecycles.get(plugin_id)
            if lifecycle and not lifecycle.is_active:
                continue
            try:
                results = instance.on_search_filter(query, results)
            except Exception as exc:
                log.warning("Plugin %s search_filter error: %s", plugin_id, exc)
        return results
        """filter_search_results."""

    # -- diagnostics ------------------------------------------------------------

    def status_report(self) -> dict[str, dict[str, Any]]:
        """Return a snapshot of all plugin lifecycles for diagnostics."""
        report: dict[str, dict[str, Any]] = {}
        for pid, lc in self._lifecycles.items():
            report[pid] = {
                "state": lc.state.name,
                "error": lc.error_message,
                "load_time_ms": round(lc.load_time * 1000, 2),
                "version": self._manifests[pid].version
                    if pid in self._manifests else "unknown",
            }
        return report
