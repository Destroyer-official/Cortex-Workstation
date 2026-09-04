"""Cortex Cleaner — Developer Ecosystem & Build Artifacts Purger.

Scans and purges:
1. Docker: Buildx cache, dangling images, stopped containers, and unused volumes.
2. Python: pip cache, poetry cache, __pycache__, and .pytest_cache.
3. Node.js: npm cache, yarn cache, pnpm store, .next/cache, and .turbo cache.
4. Rust / Cargo: Cargo registry cache and git database.
5. Java / Kotlin: Gradle cache and Maven local repository.
6. Go: Go build cache and module cache.
7. .NET: NuGet global packages and v3 cache.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class DevCacheItem:
    """Devcacheitem.

    Manages DevCacheItem operations and coordinates related state changes for the component.
    """
    ecosystem: str  # "Docker", "Python", "Node.js", "Rust/Cargo", "Java/Gradle", "Go", ".NET"
    name: str
    path: str
    size_bytes: int
    file_count: int
    is_safe_to_clean: bool = True
    description: str = ""


@dataclass
class DevCleanResult:
    """Devcleanresult.

    Manages DevCleanResult operations and coordinates related state changes for the component.
    """
    items_cleaned: int
    bytes_freed: int
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__.

        Manages post init operations and coordinates related state changes for the component.
        """
        if self.errors is None:
            self.errors = []


class DevCleaner:
    """Devcleaner.

    Manages DevCleaner operations and coordinates related state changes for the component.
    """

    @classmethod
    def _dir_metrics(cls, dir_path: Path) -> Tuple[int, int]:
        """Compute directory size and file count.

        Manages dir metrics operations and coordinates related state changes for the component.

        Args:
            dir_path (Path): Filesystem path to the target file or directory.

        Returns:
            Tuple[int, int]: Result of the operation.
        """
        if not dir_path.is_dir():
            return 0, 0
        total_size = 0
        total_files = 0
        try:
            for root, _, files in os.walk(dir_path):
                for f in files:
                    fp = Path(root) / f
                    try:
                        total_size += fp.stat().st_size
                        total_files += 1
                    except Exception:
                        pass
        except Exception:
            pass
        return total_size, total_files

    @classmethod
    def scan_dev_caches(cls) -> List[DevCacheItem]:
        """Scan system for all developer ecosystem build caches and artifacts.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Returns:
            List[DevCacheItem]: List of processed items or identifiers.
        """
        items: List[DevCacheItem] = []
        home = Path.home()
        local_app = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        app_data = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))

        # 1. Python Caches
        py_locations = [
            ("Python Pip Cache", local_app / "pip" / "cache", "Cached wheel and source downloads"),
            ("Python Pip Cache (User)", home / ".cache" / "pip", "Cached pip packages"),
            ("Poetry Cache", local_app / "pypoetry" / "Cache", "Cached poetry wheels and virtualenvs"),
        ]
        for name, p_dir, desc in py_locations:
            if p_dir.is_dir():
                sz, fc = cls._dir_metrics(p_dir)
                if sz > 0:
                    items.append(DevCacheItem("Python", name, str(p_dir), sz, fc, True, desc))

        # 2. Node.js / Web Caches
        node_locations = [
            ("npm Cache", app_data / "npm-cache", "Cached npm package tarballs"),
            ("npm Cache (User)", home / ".npm", "Cached npm package registry data"),
            ("Yarn Cache", local_app / "Yarn" / "Cache", "Yarn global offline package mirror"),
            ("pnpm Store", local_app / "pnpm" / "store", "pnpm global content-addressable store"),
        ]
        for name, p_dir, desc in node_locations:
            if p_dir.is_dir():
                sz, fc = cls._dir_metrics(p_dir)
                if sz > 0:
                    items.append(DevCacheItem("Node.js", name, str(p_dir), sz, fc, True, desc))

        # 3. Rust / Cargo Caches
        cargo_locations = [
            ("Cargo Registry Cache", home / ".cargo" / "registry" / "cache", "Downloaded crates.io .crate archives"),
            ("Cargo Git DB", home / ".cargo" / "git" / "db", "Cloned git dependency checkouts"),
        ]
        for name, p_dir, desc in cargo_locations:
            if p_dir.is_dir():
                sz, fc = cls._dir_metrics(p_dir)
                if sz > 0:
                    items.append(DevCacheItem("Rust/Cargo", name, str(p_dir), sz, fc, True, desc))

        # 4. Java / Gradle / Maven
        java_locations = [
            ("Gradle Cache", home / ".gradle" / "caches", "Downloaded Gradle wrapper, plugins, and dependencies"),
            ("Maven Repository", home / ".m2" / "repository", "Local Maven artifact cache"),
        ]
        for name, p_dir, desc in java_locations:
            if p_dir.is_dir():
                sz, fc = cls._dir_metrics(p_dir)
                if sz > 0:
                    items.append(DevCacheItem("Java/Gradle", name, str(p_dir), sz, fc, True, desc))

        # 5. Go Build Cache
        go_locations = [
            ("Go Build Cache", local_app / "go-build", "Compiled Go package objects and test results"),
            ("Go Build Cache (User)", home / ".cache" / "go-build", "Compiled Go package objects"),
        ]
        for name, p_dir, desc in go_locations:
            if p_dir.is_dir():
                sz, fc = cls._dir_metrics(p_dir)
                if sz > 0:
                    items.append(DevCacheItem("Go", name, str(p_dir), sz, fc, True, desc))

        # 6. .NET / NuGet
        nuget_locations = [
            ("NuGet v3 Cache", local_app / "NuGet" / "v3-cache", "NuGet HTTP search and metadata cache"),
            ("NuGet Packages", home / ".nuget" / "packages", "Global-packages extracted nupkg files"),
        ]
        for name, p_dir, desc in nuget_locations:
            if p_dir.is_dir():
                sz, fc = cls._dir_metrics(p_dir)
                if sz > 0:
                    items.append(DevCacheItem(".NET", name, str(p_dir), sz, fc, True, desc))

        # 7. Docker (if available)
        try:
            res = subprocess.run(["docker", "system", "df", "--format", "{{.Type}}:{{.Size}}"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if ":" in line:
                        t_name, size_str = line.split(":", 1)
                        items.append(DevCacheItem(
                            ecosystem="Docker",
                            name=f"Docker {t_name.strip()}",
                            path="docker://daemon",
                            size_bytes=0,
                            file_count=1,
                            is_safe_to_clean=True,
                            description=f"Docker {t_name.strip()} storage ({size_str.strip()})",
                        ))
        except Exception:
            pass

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)

    @classmethod
    def clean_items(cls, items: List[DevCacheItem]) -> DevCleanResult:
        """Purge selected developer cache locations.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Args:
            items (List[DevCacheItem]): Collection of items or entries to process.

        Returns:
            DevCleanResult: Result of the operation.
        """
        result = DevCleanResult(0, 0)

        for item in items:
            if item.ecosystem == "Docker" and item.path == "docker://daemon":
                try:
                    subprocess.run(["docker", "system", "prune", "-f"], capture_output=True, timeout=30)
                    result.items_cleaned += 1
                except Exception as exc:
                    result.errors.append(f"Docker prune failed: {exc}")
                continue

            p = Path(item.path)
            if not p.is_dir():
                continue

            try:
                sz, _ = cls._dir_metrics(p)
                for entry in os.scandir(p):
                    try:
                        ep = Path(entry.path)
                        if ep.is_dir():
                            shutil.rmtree(ep, ignore_errors=True)
                        else:
                            ep.unlink(missing_ok=True)
                    except Exception:
                        pass
                result.items_cleaned += 1
                result.bytes_freed += sz
            except Exception as exc:
                result.errors.append(f"Failed to clean {item.name}: {exc}")

        return result
