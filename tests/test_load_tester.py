"""Tests for the authorized load/resilience tester.

The most important tests here are the SAFETY ones: the tool must refuse public
targets without ownership proof, and must never run a test against an
unauthorized target. We also test the metrics math and a real localhost run
against a throwaway HTTP server.
"""

from __future__ import annotations

import threading
import time

import pytest

from cortex_unified.system_tools.load_tester import (
    Authorization,
    HttpLoadConfig,
    LoadResult,
    LoadTester,
    TargetAuthorizer,
    TcpLoadConfig,
)


# ---------------------------------------------------------------------------
# Safety gate
# ---------------------------------------------------------------------------

class TestAuthorization:
    def test_loopback_authorized(self):
        a = TargetAuthorizer().authorize("127.0.0.1")
        assert a.authorized is True
        assert a.category == "loopback"

    def test_localhost_authorized(self):
        a = TargetAuthorizer().authorize("localhost")
        assert a.authorized is True

    def test_private_lan_authorized(self):
        # 10.x / 192.168.x resolve to themselves (they're already IPs).
        assert TargetAuthorizer().authorize("192.168.1.50").authorized is True
        assert TargetAuthorizer().authorize("10.0.0.5").authorized is True

    def test_public_denied_without_token(self):
        a = TargetAuthorizer().authorize("8.8.8.8")
        assert a.authorized is False
        assert a.category == "denied"
        assert "ownership" in a.reason.lower()

    def test_public_denied_with_unverifiable_token(self):
        # verify_public defaults on; a random token won't be hosted on 8.8.8.8.
        a = TargetAuthorizer().authorize("8.8.8.8", ownership_token="cortex-xyz",
                                        verify_public=False)
        # With verify_public=False we still must NOT auto-authorize a public host.
        assert a.authorized is False

    def test_unresolvable_denied(self):
        a = TargetAuthorizer().authorize("no.such.host.invalid.zzz")
        assert a.authorized is False

    def test_classify_loopback(self):
        cat, ip = TargetAuthorizer.classify("127.0.0.1")
        assert cat == "loopback"

    def test_token_generation_unique(self):
        t1, t2 = TargetAuthorizer.new_token(), TargetAuthorizer.new_token()
        assert t1 != t2 and t1.startswith("cortex-")


class TestRefusesUnauthorized:
    def test_run_http_refuses_unauthorized(self):
        auth = Authorization(False, "denied", "8.8.8.8", "8.8.8.8", "nope")
        with pytest.raises(PermissionError):
            LoadTester().run_http(HttpLoadConfig(url="http://8.8.8.8/"), auth)

    def test_run_tcp_refuses_unauthorized(self):
        auth = Authorization(False, "denied", "example.com", "93.184.216.34", "nope")
        with pytest.raises(PermissionError):
            LoadTester().run_tcp(TcpLoadConfig(host="example.com", port=80), auth)


# ---------------------------------------------------------------------------
# Metrics math
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_percentiles(self):
        r = LoadResult(kind="http", target="x")
        r.latencies_ms = [float(i) for i in range(1, 101)]  # 1..100
        assert r.percentile(50) == 50.0 or r.percentile(50) == 51.0
        assert r.percentile(99) >= 99.0
        assert r.percentile(0) == 1.0

    def test_rps_and_error_rate(self):
        r = LoadResult(kind="http", target="x")
        r.total, r.succeeded, r.failed, r.duration_s = 100, 90, 10, 10.0
        assert r.rps == 10.0
        assert r.error_rate == 10.0

    def test_empty_latencies_safe(self):
        r = LoadResult(kind="http", target="x")
        assert r.percentile(95) == 0.0
        assert r.rps == 0.0
        assert r.error_rate == 0.0

    def test_summary_keys(self):
        r = LoadResult(kind="http", target="x")
        r.latencies_ms = [10.0, 20.0, 30.0]
        r.total, r.succeeded = 3, 3
        s = r.summary()
        assert set(s) >= {"rps", "error_rate", "p50_ms", "p95_ms", "p99_ms",
                          "avg_ms", "max_ms", "status_counts"}


# ---------------------------------------------------------------------------
# Real localhost run (authorized, harmless)
# ---------------------------------------------------------------------------

class TestLocalRun:
    def test_http_against_local_server(self):
        import http.server
        import socketserver

        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def do_GET(self):  # noqa: N802
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"ok")

        with socketserver.TCPServer(("127.0.0.1", 0), Quiet) as srv:
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            try:
                auth = TargetAuthorizer().authorize("127.0.0.1")
                assert auth.authorized
                cfg = HttpLoadConfig(url=f"http://127.0.0.1:{port}/",
                                     concurrency=4, duration_s=2)
                res = LoadTester().run_http(cfg, auth, confirm=True)
                assert res.total > 0
                assert res.succeeded > 0
                assert res.rps > 0
                # All responses were 200 -> zero error rate.
                assert res.error_rate == 0.0
                assert "200" in res.status_counts
            finally:
                srv.shutdown()

    def test_cancel_stops_run(self):
        auth = TargetAuthorizer().authorize("127.0.0.1")
        cancel = threading.Event()
        cancel.set()  # already cancelled -> should return almost immediately
        cfg = HttpLoadConfig(url="http://127.0.0.1:1/", concurrency=2, duration_s=30)
        t0 = time.monotonic()
        res = LoadTester().run_http(cfg, auth, cancel_event=cancel, confirm=True)
        assert (time.monotonic() - t0) < 10
        assert isinstance(res, LoadResult)
