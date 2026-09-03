"""Noninteractive entry point for scheduled private-LAN inventory scans."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from cortex_unified.system_tools.network_discovery import NetworkDiscovery
from cortex_unified.system_tools.network_service_scanner import (
    parse_custom_port_spec,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a bounded Cortex private-LAN inventory scan")
    parser.add_argument(
        "--profile", choices=("targeted", "advanced"), default="targeted")
    parser.add_argument("--scope", action="append", default=[])
    parser.add_argument("--ports", default="")
    parser.add_argument("--output", default="")
    return parser
    """_parser."""
    """_parser."""


def _write_atomic(path: str, payload: dict) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8")
        temporary.replace(target)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    """_write_atomic."""
    """_write_atomic."""


def main(argv: list[str] | None = None) -> int:
    """Main."""
    args = _parser().parse_args(argv)
    try:
        ports = parse_custom_port_spec(args.ports)
        result = NetworkDiscovery().scan(
            deep=True,
            rounds=2 if args.profile == "targeted" else 3,
            audit_profile=args.profile,
            include_upnp_wan=False,
            record_history=True,
            requested_networks=args.scope or None,
            custom_ports=ports,
        )
        payload = result.to_dict()
        if args.output:
            _write_atomic(args.output, payload)
        return 2 if result.cancelled else 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Scheduled network scan failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
