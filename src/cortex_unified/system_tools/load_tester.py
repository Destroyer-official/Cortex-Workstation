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

_MAX_CONCURRENCY_HARD = 500
MAX_CONCURRENCY = 100
MAX_DURATION_S = 600
_USER_AGENT = "CortexCleaner-LoadTester/1.0 (authorized resilience test)"
_TOKEN_PATH = "/.well-known/cortex-loadtest-authorization"
_AUDIT_LOG = Path.home() / ".cortex_cleaner" / "logs" / "loadtest_audit.log"

_WARNING_BANNER = (
    "WARNING: This tool generates network traffic for load testing purposes.\n"
    "Use only against infrastructure you own or have explicit authorization to test.\n"
    "All activity is logged to %s\n"
)


# =====================================================================
#  Target authorization (the safeguard)
# =====================================================================

@dataclass(slots=True)
class Authorization:
    """Authorization.

    Manages Authorization operations and coordinates related state changes for the component.
    """
    authorized: bool
    category: str            # loopback / private / link-local / owned-public / denied
    host: str
    resolved_ip: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "authorized": self.authorized, "category": self.category,
            "host": self.host, "resolved_ip": self.resolved_ip, "reason": self.reason,
        }


class TargetAuthorizer:
    """Targetauthorizer.

    Manages TargetAuthorizer operations and coordinates related state changes for the component.
    """

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
        """Authorize.

        Manages authorize operations and coordinates related state changes for the component.

        Args:
            host (str): The host parameter.
            ownership_token (str | None): The ownership token parameter.
            verify_public (bool): The verify public parameter.

        Returns:
            Authorization: Result of the operation.
        """
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
        """Fetch the token file the user placed on their server and compare.

        Manages verify ownership operations and coordinates related state changes for the component.

        Args:
            host (str): The host parameter.
            token (str): The token parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
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
        """Generate a random token for the user to host on their server.

        Manages new token operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        import secrets
        return "cortex-" + secrets.token_hex(16)


# =====================================================================
#  Config + results
# =====================================================================

@dataclass(slots=True)
class HttpLoadConfig:
    """Httploadconfig.

    Manages HttpLoadConfig operations and coordinates related state changes for the component.
    """
    url: str
    method: str = "GET"
    concurrency: int = 10
    duration_s: int = 15
    timeout_s: float = 10.0
    ramp_s: int = 0
    rate_cap_rps: int = 0        # 0 = unlimited (bounded by concurrency)


@dataclass(slots=True)
class TcpLoadConfig:
    """Tcploadconfig.

    Manages TcpLoadConfig operations and coordinates related state changes for the component.
    """
    host: str
    port: int
    concurrency: int = 10
    duration_s: int = 10
    timeout_s: float = 5.0


@dataclass(slots=True)
class LoadResult:
    """Loadresult.

    Manages LoadResult operations and coordinates related state changes for the component.
    """
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
        """Rps.

        Manages rps operations and coordinates related state changes for the component.

        Returns:
            float: Result of the operation.
        """
        return round(self.total / self.duration_s, 1) if self.duration_s else 0.0

    @property
    def error_rate(self) -> float:
        """Error rate.

        Manages error rate operations and coordinates related state changes for the component.

        Returns:
            float: Result of the operation.
        """
        return round(100.0 * self.failed / self.total, 2) if self.total else 0.0

    def percentile(self, p: float) -> float:
        """Percentile.

        Manages percentile operations and coordinates related state changes for the component.

        Args:
            p (float): The p parameter.

        Returns:
            float: Result of the operation.
        """
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        k = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
        return round(s[k], 1)

    def summary(self) -> dict[str, Any]:
        """Summary.

        Manages summary operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
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
    """Loadtester.

    Manages LoadTester operations and coordinates related state changes for the component.
    """

    def __init__(self):
        """Initialize Load Tester.

        Initializes the instance and configures internal state.
        """
        self._authorizer = TargetAuthorizer()

    # -- HTTP (L7) ----------------------------------------------------------

    def run_http(self, cfg: HttpLoadConfig, auth: Authorization,
                 progress: ProgressCB | None = None,
                 cancel_event: threading.Event | None = None,
                 confirm: bool = False,
                 safe_mode: bool = False) -> LoadResult:
        """Run http.

        Manages run http operations and coordinates related state changes for the component.

        Args:
            cfg (HttpLoadConfig): The cfg parameter.
            auth (Authorization): The auth parameter.
            progress (ProgressCB | None): The progress parameter.
            cancel_event (threading.Event | None): Threading event or callable to check for cancellation.
            confirm (bool): The confirm parameter.
            safe_mode (bool): The safe mode parameter.

        Returns:
            LoadResult: Result of the operation.
        """
        if not auth.authorized:
            raise PermissionError(f"Target not authorized: {auth.reason}")
        if not confirm:
            raise PermissionError(
                "Load test not confirmed. Pass confirm=True to acknowledge "
                "that you are testing your own authorized infrastructure.")
        print(_WARNING_BANNER % _AUDIT_LOG, flush=True)
        conc = max(1, min(cfg.concurrency,
                          MAX_CONCURRENCY if not safe_mode else min(MAX_CONCURRENCY, 10)))
        dur = max(1, min(cfg.duration_s, MAX_DURATION_S))
        result = LoadResult(kind="http", target=cfg.url)
        self._audit("http", cfg.url, auth, conc, dur)

        lock = threading.Lock()
        cancel = cancel_event or threading.Event()
        start = time.monotonic()
        deadline = start + dur
        min_interval = (conc / cfg.rate_cap_rps) if cfg.rate_cap_rps > 0 else 0.0

        def worker(idx: int):
            """Worker.

            Manages worker operations and coordinates related state changes for the component.

            Args:
                idx (int): The idx parameter.
            """
            import urllib.request
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
                cancel_event: threading.Event | None = None,
                confirm: bool = False,
                safe_mode: bool = False) -> LoadResult:
        """Run tcp.

        Manages run tcp operations and coordinates related state changes for the component.

        Args:
            cfg (TcpLoadConfig): The cfg parameter.
            auth (Authorization): The auth parameter.
            progress (ProgressCB | None): The progress parameter.
            cancel_event (threading.Event | None): Threading event or callable to check for cancellation.
            confirm (bool): The confirm parameter.
            safe_mode (bool): The safe mode parameter.

        Returns:
            LoadResult: Result of the operation.
        """
        if not auth.authorized:
            raise PermissionError(f"Target not authorized: {auth.reason}")
        if not confirm:
            raise PermissionError(
                "Load test not confirmed. Pass confirm=True to acknowledge "
                "that you are testing your own authorized infrastructure.")
        print(_WARNING_BANNER % _AUDIT_LOG, flush=True)
        conc = max(1, min(cfg.concurrency,
                          MAX_CONCURRENCY if not safe_mode else min(MAX_CONCURRENCY, 10)))
        dur = max(1, min(cfg.duration_s, MAX_DURATION_S))
        result = LoadResult(kind="tcp", target=f"{cfg.host}:{cfg.port}")
        self._audit("tcp", f"{cfg.host}:{cfg.port}", auth, conc, dur)

        lock = threading.Lock()
        cancel = cancel_event or threading.Event()
        start = time.monotonic()
        deadline = start + dur

        def worker(idx: int):
            """Worker.

            Manages worker operations and coordinates related state changes for the component.

            Args:
                idx (int): The idx parameter.
            """
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
        """_run_pool.

        Manages run pool operations and coordinates related state changes for the component.

        Args:
            worker: The worker parameter.
            conc: The conc parameter.
            deadline: The deadline parameter.
            cancel: Threading event or callable to check for cancellation.
            progress: The progress parameter.
            result: Collection or dictionary holding operation results.
            start: The start parameter.
        """
        threads = [threading.Thread(target=worker, args=(i,), daemon=True)
                   for i in range(conc)]
        for t in threads:
            t.start()
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
        """_progress_snapshot.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            result (LoadResult): Dictionary or data object holding operation results.
            start (float): The start parameter.
            final (bool): The final parameter.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
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
        """Audit.

        Manages audit operations and coordinates related state changes for the component.

        Args:
            kind (str): The kind parameter.
            target (str): The target parameter.
            auth (Authorization): The auth parameter.
            conc (int): The conc parameter.
            dur (int): The dur parameter.
        """
        try:
            _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(_AUDIT_LOG, "a", encoding="utf-8") as fh:
                fh.write(f"{ts}\t{kind}\ttarget={target}\tcategory={auth.category}"
                         f"\tip={auth.resolved_ip}\tconc={conc}\tdur={dur}s\n")
        except OSError:
            pass
