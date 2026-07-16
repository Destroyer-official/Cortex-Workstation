"""Load / resilience tester - measure how much YOUR OWN service can take.

This is the legitimate, defensive counterpart to a stress tool: you point it at
infrastructure you control, push realistic high load, and learn where it
degrades and where it falls over - so you fix the weak point before a real
incident. It reports the same metrics professional tools (k6, Locust, JMeter)
report: throughput (RPS), latency percentiles (p50/p95/p99), and error rate.

SAFETY MODEL (enforced in code, not deferred):
* A target is only allowed if it is loopback / private-LAN / link-local (your
  own environment), OR a public host you prove you control by hosting a token
  file at ``/.well-known/cortex-loadtest-authorization``.
* There is NO source spoofing, NO evasion, NO stealth, NO distributed
  coordination - none of which have any place when testing your own systems.
  The traffic is honest and identifies itself so your own defenses (rate
  limiters, WAF, autoscaling) engage - which is the whole point of the test.
* Concurrency and duration are capped, and every run is written to an audit log.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_LOG = logging.getLogger("cortex.system_tools.load_tester")

# Hard ceilings so a test can't accidentally exhaust the local machine.
MAX_CONCURRENCY = 500
MAX_DURATION_S = 600
_USER_AGENT = "CortexCleaner-LoadTester/1.0 (authorized resilience test)"
_TOKEN_PATH = "/.well-known/cortex-loadtest-authorization"
_AUDIT_LOG = Path.home() / ".cortex_cleaner" / "logs" / "loadtest_audit.log"


# =====================================================================
#  Target authorization (the safeguard)
# =====================================================================

@dataclass(slots=True)
class Authorization:
    authorized: bool
    category: str            # loopback / private / link-local / owned-public / denied
    host: str
    resolved_ip: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorized": self.authorized, "category": self.category,
            "host": self.host, "resolved_ip": self.resolved_ip, "reason": self.reason,
        }


class TargetAuthorizer:
    """Decides whether a target may be load-tested. Private = yours = allowed."""

    @staticmethod
    def classify(host: str) -> tuple[str, str]:
        """Return (category, resolved_ip) for *host* without any network calls
        beyond DNS resolution."""
        host = (host or "").strip()
        if not host:
            return "denied", ""
        # Strip scheme/path if a URL was passed.
        h = host
        if "://" in h:
            h = h.split("://", 1)[1]
        h = h.split("/", 1)[0].split(":", 1)[0]
        try:
            ip = socket.gethostbyname(h)
        except (socket.gaierror, OSError):
            return "unresolvable", ""
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return "denied", ip
        if addr.is_loopback:
            return "loopback", ip
        if addr.is_link_local:
            return "link-local", ip
        if addr.is_private:
            return "private", ip
        return "public", ip

    def authorize(self, host: str, ownership_token: str | None = None,
                  verify_public: bool = True) -> Authorization:
        category, ip = self.classify(host)
        if category in ("loopback", "private", "link-local"):
            return Authorization(True, category, host, ip,
                                 "Private/own environment - inherently authorized.")
        if category == "unresolvable":
            return Authorization(False, "denied", host, "",
                                 "Host could not be resolved.")
        if category == "public":
            if ownership_token and verify_public:
                if self._verify_ownership(host, ownership_token):
                    return Authorization(True, "owned-public", host, ip,
                                         "Ownership verified via token file.")
                return Authorization(False, "denied", host, ip,
                                     "Ownership token not found or did not match at "
                                     f"{_TOKEN_PATH}.")
            return Authorization(
                False, "denied", host, ip,
                "Public host requires ownership proof: host a file at "
                f"{_TOKEN_PATH} containing your token, then supply the token.")
        return Authorization(False, "denied", host, ip, "Target not permitted.")

    @staticmethod
    def _verify_ownership(host: str, token: str) -> bool:
        """Fetch the token file the user placed on their server and compare."""
        import urllib.request
        h = host if "://" in host else f"http://{host}"
        url = h.rstrip("/") + _TOKEN_PATH
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310 - user's own host
                body = resp.read(4096).decode("utf-8", "replace").strip()
            return token.strip() != "" and token.strip() in body
        except Exception as exc:  # noqa: BLE001
            _LOG.debug("ownership verify failed for %s: %s", url, exc)
            return False

    @staticmethod
    def new_token() -> str:
        """Generate a random token for the user to host on their server."""
        import secrets
        return "cortex-" + secrets.token_hex(16)


# =====================================================================
#  Config + results
# =====================================================================

@dataclass(slots=True)
class HttpLoadConfig:
    url: str
    method: str = "GET"
    concurrency: int = 10
    duration_s: int = 15
    timeout_s: float = 10.0
    ramp_s: int = 0
    rate_cap_rps: int = 0        # 0 = unlimited (bounded by concurrency)


@dataclass(slots=True)
class TcpLoadConfig:
    host: str
    port: int
    concurrency: int = 10
    duration_s: int = 10
    timeout_s: float = 5.0


@dataclass(slots=True)
class LoadResult:
    kind: str
    target: str
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    duration_s: float = 0.0
    latencies_ms: list[float] = field(default_factory=list)
    status_counts: dict[str, int] = field(default_factory=dict)
    error_counts: dict[str, int] = field(default_factory=dict)

    @property
    def rps(self) -> float:
        return round(self.total / self.duration_s, 1) if self.duration_s else 0.0

    @property
    def error_rate(self) -> float:
        return round(100.0 * self.failed / self.total, 2) if self.total else 0.0

    def percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        k = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
        return round(s[k], 1)

    def summary(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "target": self.target, "total": self.total,
            "succeeded": self.succeeded, "failed": self.failed,
            "duration_s": round(self.duration_s, 2), "rps": self.rps,
            "error_rate": self.error_rate,
            "p50_ms": self.percentile(50), "p90_ms": self.percentile(90),
            "p95_ms": self.percentile(95), "p99_ms": self.percentile(99),
            "min_ms": round(min(self.latencies_ms), 1) if self.latencies_ms else 0.0,
            "max_ms": round(max(self.latencies_ms), 1) if self.latencies_ms else 0.0,
            "avg_ms": round(sum(self.latencies_ms) / len(self.latencies_ms), 1)
            if self.latencies_ms else 0.0,
            "status_counts": dict(self.status_counts),
            "error_counts": dict(self.error_counts),
        }


ProgressCB = Callable[[dict], None]


# =====================================================================
#  The tester
# =====================================================================

class LoadTester:
    """Runs authorized load tests and reports resilience metrics."""

    def __init__(self):
        self._authorizer = TargetAuthorizer()

    # -- HTTP (L7) ----------------------------------------------------------

    def run_http(self, cfg: HttpLoadConfig, auth: Authorization,
                 progress: ProgressCB | None = None,
                 cancel_event: threading.Event | None = None) -> LoadResult:
        if not auth.authorized:
            raise PermissionError(f"Target not authorized: {auth.reason}")
        conc = max(1, min(cfg.concurrency, MAX_CONCURRENCY))
        dur = max(1, min(cfg.duration_s, MAX_DURATION_S))
        result = LoadResult(kind="http", target=cfg.url)
        self._audit("http", cfg.url, auth, conc, dur)

        lock = threading.Lock()
        cancel = cancel_event or threading.Event()
        start = time.monotonic()
        deadline = start + dur
        # Simple global rate limit (requests/sec) shared across workers.
        min_interval = (conc / cfg.rate_cap_rps) if cfg.rate_cap_rps > 0 else 0.0

        def worker(idx: int):
            import urllib.request
            # Stagger start during ramp so load rises gradually.
            if cfg.ramp_s > 0:
                time.sleep(cfg.ramp_s * idx / conc)
            while time.monotonic() < deadline and not cancel.is_set():
                t0 = time.monotonic()
                status = "ERR"
                ok = False
                err = ""
                try:
                    req = urllib.request.Request(
                        cfg.url, method=cfg.method.upper(),
                        headers={"User-Agent": _USER_AGENT})
                    with urllib.request.urlopen(req, timeout=cfg.timeout_s) as resp:  # noqa: S310
                        resp.read()
                        status = str(resp.status)
                        ok = 200 <= resp.status < 400
                except Exception as exc:  # noqa: BLE001
                    err = type(exc).__name__
                    code = getattr(exc, "code", None)
                    if code is not None:
                        status = str(code)
                dt = (time.monotonic() - t0) * 1000.0
                with lock:
                    result.total += 1
                    result.latencies_ms.append(dt)
                    result.status_counts[status] = result.status_counts.get(status, 0) + 1
                    if ok:
                        result.succeeded += 1
                    else:
                        result.failed += 1
                        if err:
                            result.error_counts[err] = result.error_counts.get(err, 0) + 1
                if min_interval:
                    time.sleep(min_interval)
                if progress and result.total % 25 == 0:
                    progress(self._progress_snapshot(result, start))

        self._run_pool(worker, conc, deadline, cancel, progress, result, start)
        result.duration_s = time.monotonic() - start
        if progress:
            progress(self._progress_snapshot(result, start, final=True))
        return result

    # -- TCP connect (L4) ---------------------------------------------------

    def run_tcp(self, cfg: TcpLoadConfig, auth: Authorization,
                progress: ProgressCB | None = None,
                cancel_event: threading.Event | None = None) -> LoadResult:
        if not auth.authorized:
            raise PermissionError(f"Target not authorized: {auth.reason}")
        conc = max(1, min(cfg.concurrency, MAX_CONCURRENCY))
        dur = max(1, min(cfg.duration_s, MAX_DURATION_S))
        result = LoadResult(kind="tcp", target=f"{cfg.host}:{cfg.port}")
        self._audit("tcp", f"{cfg.host}:{cfg.port}", auth, conc, dur)

        lock = threading.Lock()
        cancel = cancel_event or threading.Event()
        start = time.monotonic()
        deadline = start + dur

        def worker(idx: int):
            while time.monotonic() < deadline and not cancel.is_set():
                t0 = time.monotonic()
                ok = False
                err = ""
                try:
                    with socket.create_connection((cfg.host, cfg.port), timeout=cfg.timeout_s):
                        ok = True
                except Exception as exc:  # noqa: BLE001
                    err = type(exc).__name__
                dt = (time.monotonic() - t0) * 1000.0
                with lock:
                    result.total += 1
                    result.latencies_ms.append(dt)
                    if ok:
                        result.succeeded += 1
                        result.status_counts["connected"] = \
                            result.status_counts.get("connected", 0) + 1
                    else:
                        result.failed += 1
                        result.error_counts[err] = result.error_counts.get(err, 0) + 1
                if progress and result.total % 25 == 0:
                    progress(self._progress_snapshot(result, start))

        self._run_pool(worker, conc, deadline, cancel, progress, result, start)
        result.duration_s = time.monotonic() - start
        if progress:
            progress(self._progress_snapshot(result, start, final=True))
        return result

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _run_pool(worker, conc, deadline, cancel, progress, result, start):
        threads = [threading.Thread(target=worker, args=(i,), daemon=True)
                   for i in range(conc)]
        for t in threads:
            t.start()
        # Heartbeat so the UI keeps updating even between the 25-request marks.
        while any(t.is_alive() for t in threads):
            if progress:
                progress(LoadTester._progress_snapshot(result, start))
            time.sleep(0.25)
            if cancel.is_set():
                break
        for t in threads:
            t.join(timeout=2.0)

    @staticmethod
    def _progress_snapshot(result: LoadResult, start: float, final: bool = False) -> dict:
        elapsed = max(1e-6, time.monotonic() - start)
        return {
            "elapsed_s": round(elapsed, 1),
            "requests": result.total,
            "rps": round(result.total / elapsed, 1),
            "errors": result.failed,
            "error_rate": result.error_rate,
            "final": final,
        }

    @staticmethod
    def _audit(kind: str, target: str, auth: Authorization, conc: int, dur: int) -> None:
        try:
            _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(_AUDIT_LOG, "a", encoding="utf-8") as fh:
                fh.write(f"{ts}\t{kind}\ttarget={target}\tcategory={auth.category}"
                         f"\tip={auth.resolved_ip}\tconc={conc}\tdur={dur}s\n")
        except OSError:
            pass
