"""Filesystem secrets scanner with live credential validation.

Detects hardcoded credentials and sensitive data (API keys, tokens,
private keys, PII, infrastructure config) using 90+ regex patterns, then
grades each finding by context-aware confidence -- a key in a test fixture
is treated differently from the same key in production code.

Capabilities:
* Archive scanning: zip/tar/tar.gz/tar.bz2 trees that a plain git scan misses.
* Optional live verification against provider APIs (AWS, GitHub, Stripe,
  Slack, OpenAI, npm). Off by default so scanning stays air-gap safe; the
  only network traffic happens when ``--verify`` is explicitly passed.
* Blast-radius assessment: what an attacker could do with each exposed key.
* Git history mode: walks all commits, not just the working tree.
* Baseline/delta mode: report only findings newer than a saved baseline.
* Persistent false-positive suppression database.
* Self-contained HTML report plus Jira/GitHub issue export.
* Compliance mapping (GDPR/HIPAA/PCI-DSS/SOC2) for audit workflows.

Usage:
  sentinel_pro.py scan /path/to/scan
  sentinel_pro.py scan /path/to/scan --verify --archives --report audit.html
  sentinel_pro.py scan /path/to/scan --diff           # delta since baseline
  sentinel_pro.py scan /path/to/scan --git-history    # walk git commits
  sentinel_pro.py scan /path/to/scan --jira-project SEC --jira-url https://...
  sentinel_pro.py baseline save /path/to/scan
  sentinel_pro.py baseline diff /path/to/scan
  sentinel_pro.py verify findings.json
  sentinel_pro.py serve --port 8080
  sentinel_pro.py fp add <finding-id>
  sentinel_pro.py fp list
"""


from __future__ import annotations

import argparse
import base64
import concurrent.futures
import fnmatch
import hashlib
import hmac
import http.server
import json
import math
import mmap
import os
import re
import subprocess
import sys
import csv
import html as html_mod
import tarfile
import time
import urllib.request
import urllib.error
import zipfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# ─── Optional dependencies ────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.text import Text
    from rich.rule import Rule
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ─── Version & Constants ──────────────────────────────────────────────────────

VERSION = "2.0.0"

SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
SEVERITY_EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "INFO": "🔵"}
SEVERITY_COLOR = {
    "CRITICAL": "#ef4444", "HIGH": "#f97316",
    "MEDIUM":   "#eab308",  "LOW": "#22c55e", "INFO": "#3b82f6",
}
CATEGORY_EMOJI = {
    "SECRET": "🔑", "PII": "👤", "CRYPTO": "🔐",
    "CONFIG": "⚙️",  "NETWORK": "🌐", "COMPLIANCE": "📋",
}
COMPLIANCE_ARTICLES = {
    "GDPR":    "GDPR Art. 5, 32, 83 — up to €20M or 4% global turnover",
    "HIPAA":   "HIPAA §164.312 — up to $1.9M per violation category/year",
    "PCI_DSS": "PCI DSS Req. 3, 4, 8 — loss of card processing rights",
    "SOC2":    "SOC 2 CC6, CC7 — audit failure, customer contract breach",
}

SKIP_EXTENSIONS = frozenset({
    ".jpg",".jpeg",".png",".gif",".bmp",".ico",".webp",".tiff",
    ".mp4",".mp3",".wav",".avi",".mov",".mkv",".flac",
    ".exe",".dll",".so",".dylib",".o",".a",".obj",".lib",
    ".pyc",".class",".wasm",
    ".ttf",".woff",".woff2",".eot",".otf",
    ".db",".sqlite",".sqlite3",
    ".bin",".dat",".img",".iso",
    ".parquet",".arrow",
})

ARCHIVE_EXTENSIONS = frozenset({".zip", ".tar", ".gz", ".bz2", ".tgz"})
MAX_DEEP_SCAN_BYTES   = 32 * 1024 * 1024   # 32 MB per file
MAX_ARCHIVE_FILE_BYTES = 8 * 1024 * 1024   # 8 MB per archived member
MAX_ARCHIVE_TOTAL_BYTES = 200 * 1024 * 1024 # 200 MB total per archive

HISTORY_DIR = os.path.expanduser("~/.sentinel/history")
BASELINE_FILENAME = ".sentinel-baseline.json"
FP_DB_FILENAME    = ".sentinel-fp.json"

# ─── Data Models ─────────────────────────────────────────────────────────────

@dataclass
class DetectionPattern:
    """Detection Pattern data container."""
    name: str
    regex: re.Pattern
    severity: str
    category: str
    compliance: List[str]
    remediation: str
    description: str
    redact: bool = True

@dataclass
class Finding:
    """Finding data container."""
    file_path: str
    line_number: int
    line_preview: str
    pattern_name: str
    severity: str
    category: str
    compliance: List[str]
    remediation: str
    match_preview: str
    entropy: float = 0.0
    file_size: int = 0
    confidence: float = 1.0
    verified: Optional[bool] = None    # None=not checked, True=LIVE, False=revoked
    identity: Optional[str] = None     # who this key belongs to
    blast_radius: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return asdict(self)

    @property
    def severity_rank(self) -> int:
        """Severity rank."""
        return SEVERITY_ORDER.get(self.severity, 0)

    @property
    def fingerprint(self) -> str:
        """Fingerprint."""
        return hashlib.sha256(
            f"{self.file_path}|{self.pattern_name}|{self.match_preview}".encode()
        ).hexdigest()[:16]

@dataclass
class ScanStats:
    """Scan Stats data container."""
    directory: str
    scan_time: str
    duration_seconds: float
    files_scanned: int
    files_skipped: int
    total_bytes_scanned: int
    findings: List[Finding]
    risk_score: int
    sentinel_version: str = VERSION
    archives_scanned: int = 0
    git_commits_scanned: int = 0
    suppressed_count: int = 0
    is_delta: bool = False
    delta_resolved: int = 0

    @property
    def critical(self)     -> List[Finding]:
        """Critical."""
        return [f for f in self.findings if f.severity == "CRITICAL"]
    @property
    def high(self)         -> List[Finding]:
        """High."""
        return [f for f in self.findings if f.severity == "HIGH"]
    @property
    def medium(self)       -> List[Finding]:
        """Medium."""
        return [f for f in self.findings if f.severity == "MEDIUM"]
    @property
    def low(self)          -> List[Finding]:
        """Low."""
        return [f for f in self.findings if f.severity == "LOW"]
    @property
    def unique_files(self) -> int:
        """Unique files."""
        return len({f.file_path for f in self.findings})
    @property
    def live_credentials(self) -> List[Finding]:
        """Live credentials."""
        return [f for f in self.findings if f.verified is True]

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        d = asdict(self)
        d["summary"] = {
            "critical": len(self.critical), "high": len(self.high),
            "medium": len(self.medium), "low": len(self.low),
            "unique_files": self.unique_files,
            "live_credentials": len(self.live_credentials),
        }
        return d

@dataclass
class VerificationResult:
    """Verification Result data container."""
    finding_id: str
    pattern_name: str
    is_live: Optional[bool]
    identity: Optional[str]
    blast_radius: str
    error: Optional[str]
    verified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def status_emoji(self) -> str:
        """Status emoji."""
        if self.is_live is True:  return "🔴 LIVE"
        if self.is_live is False: return "✅ REVOKED"
        return "❓ UNVERIFIED"

# ─── Pattern Compiler ────────────────────────────────────────────────────────

def _p(pattern: str, flags: int = 0) -> re.Pattern:
    return re.compile(pattern.encode(), flags | re.IGNORECASE)
    """_p."""
    """_p."""

# ─── Detection Patterns — 90+ Precision Patterns ─────────────────────────────

PATTERNS: List[DetectionPattern] = [

    # Cloud Provider Credentials ═══════════════════════════════════════════

    DetectionPattern(
        name="AWS Access Key ID",
        regex=_p(r"(?<![A-Z0-9])(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2","PCI_DSS"],
        description="Amazon Web Services Access Key ID. Grants programmatic AWS access.",
        remediation=(
            "1. Rotate in AWS IAM Console immediately.\n"
            "2. Audit CloudTrail for unauthorized activity.\n"
            "3. Use IAM Roles / Instance Profiles instead of static keys.\n"
            "4. Enable AWS Config rule 'access-keys-rotated'."
        ), redact=False,
    ),
    DetectionPattern(
        name="AWS Secret Access Key",
        regex=_p(r"(?:aws_secret_access_key|aws_secret|secret.?key)\s*[=:]\s*['\"]?([A-Za-z0-9/+]{40})['\"]?"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2","PCI_DSS"],
        description="AWS Secret Access Key. With an Access Key ID, grants full programmatic AWS access.",
        remediation=(
            "1. Rotate IMMEDIATELY in AWS IAM Console.\n"
            "2. Check CloudTrail for abuse since key creation.\n"
            "3. If in git history: purge with BFG Repo-Cleaner or git-filter-repo.\n"
            "4. Move to IAM Roles / AWS Secrets Manager."
        ),
    ),
    DetectionPattern(
        name="GCP Service Account Key (JSON)",
        regex=_p(r'"type"\s*:\s*"service_account"[\s\S]{0,300}"private_key"'),
        severity="CRITICAL", category="SECRET", compliance=["SOC2","GDPR"],
        description="Google Cloud Platform service account key. Grants access to GCP project resources.",
        remediation=(
            "1. Delete the key in GCP Console → IAM → Service Accounts.\n"
            "2. Audit GCP audit logs for unauthorized use.\n"
            "3. Use Workload Identity Federation instead of service account keys."
        ),
    ),
    DetectionPattern(
        name="Azure Client Secret / Storage Key",
        regex=_p(r"(?:client_secret|clientSecret|AccountKey|AZURE_CLIENT_SECRET)\s*[=:]\s*['\"]?([A-Za-z0-9+/=_\-]{32,})['\"]?"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2","PCI_DSS"],
        description="Azure credential (client secret or storage account key).",
        remediation=(
            "1. Rotate in Azure Portal → App Registrations or Storage Accounts.\n"
            "2. Review Azure Activity Log for unauthorized access.\n"
            "3. Use Managed Identity where possible."
        ),
    ),
    DetectionPattern(
        name="OpenAI API Key",
        regex=_p(r"sk-(?:proj-|org-)?[A-Za-z0-9_\-]{40,}"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2"],
        description="OpenAI API key. Grants access to GPT models with billing consequences.",
        remediation=(
            "1. Rotate at platform.openai.com/api-keys immediately.\n"
            "2. Review usage logs for unauthorized requests.\n"
            "3. Use environment variables, never hardcode."
        ),
    ),
    DetectionPattern(
        name="Anthropic API Key (Claude)",
        regex=_p(r"sk-ant-(?:api03-)?[A-Za-z0-9_\-]{90,}"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2"],
        description="Anthropic API key. Grants access to Claude API with billing implications.",
        remediation=(
            "1. Rotate at console.anthropic.com/settings/keys.\n"
            "2. Audit usage logs for unauthorized calls.\n"
            "3. Store in environment variables. Never commit to files or configs."
        ),
    ),
    DetectionPattern(
        name="GitHub Personal Access Token (Classic)",
        regex=_p(r"ghp_[A-Za-z0-9]{36,}"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2"],
        description="GitHub Personal Access Token. May grant read/write access to repositories and org data.",
        remediation=(
            "1. Revoke at github.com/settings/tokens immediately.\n"
            "2. Review recent activity in GitHub audit log.\n"
            "3. Use fine-grained tokens with minimal scopes."
        ),
    ),
    DetectionPattern(
        name="GitHub Fine-Grained PAT",
        regex=_p(r"github_pat_[A-Za-z0-9_]{80,}"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2"],
        description="GitHub Fine-Grained Personal Access Token with scoped permissions.",
        remediation="Revoke at github.com/settings/tokens. Rotate any secrets the token had access to.",
    ),
    DetectionPattern(
        name="GitHub OAuth Token",
        regex=_p(r"gho_[A-Za-z0-9]{36,}"),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="GitHub OAuth access token. Grants access as the authenticating user.",
        remediation="Revoke OAuth app authorization at github.com/settings/applications.",
    ),
    DetectionPattern(
        name="Stripe Live Secret Key",
        regex=_p(r"sk_live_[A-Za-z0-9]{24,}"),
        severity="CRITICAL", category="SECRET", compliance=["PCI_DSS","SOC2"],
        description="Stripe production secret key. Full access to charges, refunds, and customer data. PCI-DSS incident.",
        remediation=(
            "1. Roll the key at dashboard.stripe.com/apikeys IMMEDIATELY.\n"
            "2. Review Stripe logs for unauthorized charges.\n"
            "3. Notify your compliance/legal team — this may be a PCI-DSS reportable incident.\n"
            "4. Check for unauthorized payouts."
        ),
    ),
    DetectionPattern(
        name="Stripe Test Secret Key",
        regex=_p(r"sk_test_[A-Za-z0-9]{24,}"),
        severity="MEDIUM", category="SECRET", compliance=["SOC2"],
        description="Stripe test mode key. No live transaction risk but may indicate key management issues.",
        remediation="Rotate at dashboard.stripe.com/apikeys. Ensure test and live keys are managed separately.",
    ),
    DetectionPattern(
        name="Slack Bot/User Token",
        regex=_p(r"xox[bpao]-[0-9]{10,12}-[0-9]{10,12}-[A-Za-z0-9]{24,}"),
        severity="HIGH", category="SECRET", compliance=["SOC2","GDPR"],
        description="Slack API token. May grant access to messages, channels, and file uploads.",
        remediation=(
            "1. Revoke at api.slack.com/apps.\n"
            "2. Review Slack audit logs for unauthorized activity.\n"
            "3. Use Slack's Socket Mode with short-lived tokens."
        ),
    ),
    DetectionPattern(
        name="Slack Webhook URL",
        regex=_p(r"https://hooks\.slack\.com/services/T[A-Z0-9]{8,}/B[A-Z0-9]{8,}/[A-Za-z0-9]{24,}"),
        severity="MEDIUM", category="SECRET", compliance=["SOC2"],
        description="Slack Incoming Webhook URL. Allows posting messages to a Slack channel.",
        remediation="Regenerate the webhook at api.slack.com/apps. Add to .sentinelignore or environment variables.",
    ),
    DetectionPattern(
        name="Twilio Auth Token",
        regex=_p(r"(?:twilio[_\-]?auth[_\-]?token|TWILIO_AUTH_TOKEN)\s*[=:]\s*['\"]?([a-f0-9]{32})['\"]?"),
        severity="HIGH", category="SECRET", compliance=["SOC2","PCI_DSS"],
        description="Twilio auth token. Grants access to SMS, voice, and account data.",
        remediation="Rotate at console.twilio.com/user/account/settings. Audit Twilio logs for abuse.",
    ),
    DetectionPattern(
        name="SendGrid API Key",
        regex=_p(r"SG\.[A-Za-z0-9_\-]{22}\.[A-Za-z0-9_\-]{43}"),
        severity="HIGH", category="SECRET", compliance=["SOC2","GDPR"],
        description="SendGrid API key. Allows sending email and accessing mailing lists.",
        remediation="Rotate at app.sendgrid.com/settings/api_keys. Audit send activity.",
    ),
    DetectionPattern(
        name="Mailchimp API Key",
        regex=_p(r"[A-Za-z0-9]{32}-us[0-9]{1,2}"),
        severity="HIGH", category="SECRET", compliance=["SOC2","GDPR"],
        description="Mailchimp API key. Grants access to mailing lists (GDPR implications).",
        remediation="Rotate at mailchimp.com/account/api. Contains subscriber PII — GDPR incident risk.",
    ),
    DetectionPattern(
        name="npm Auth Token",
        regex=_p(r"(?://registry\.npmjs\.org/:_authToken|npm_[A-Za-z0-9]{36,}|NPM_TOKEN)\s*[=:]\s*['\"]?([A-Za-z0-9_\-]{32,})['\"]?"),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="npm registry token. May allow publishing packages — supply chain attack vector.",
        remediation=(
            "1. Revoke at npmjs.com/settings/tokens.\n"
            "2. Check publish history for unauthorized packages.\n"
            "3. Enable 2FA on npm account."
        ),
    ),
    DetectionPattern(
        name="PyPI API Token",
        regex=_p(r"pypi-[A-Za-z0-9_\-]{32,}"),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="PyPI upload token. Allows publishing Python packages — supply chain risk.",
        remediation="Revoke at pypi.org/manage/account/token. Audit recent uploads.",
    ),
    DetectionPattern(
        name="HuggingFace Token",
        regex=_p(r"hf_[A-Za-z0-9]{34,}"),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="HuggingFace API token. Grants model access, private repo access, and billing.",
        remediation="Rotate at huggingface.co/settings/tokens. Check access to private models/datasets.",
    ),
    DetectionPattern(
        name="Telegram Bot Token",
        regex=_p(r"[0-9]{9,10}:[A-Za-z0-9_\-]{35,}"),
        severity="HIGH", category="SECRET", compliance=["SOC2","GDPR"],
        description="Telegram Bot API token. Full control of bot, access to message history.",
        remediation="Revoke via @BotFather /revoke command. Audit bot message history.",
    ),
    DetectionPattern(
        name="Discord Bot Token",
        regex=_p(r"(?:discord[_\-]?(?:bot[_\-]?)?token|DISCORD_TOKEN)\s*[=:]\s*['\"]?([A-Za-z0-9_\-]{59,})['\"]?"),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="Discord bot token. Full control of the bot and access to all servers it's in.",
        remediation="Regenerate at discord.com/developers/applications. Kick the bot and re-authorize.",
    ),
    DetectionPattern(
        name="HashiCorp Vault Token",
        regex=_p(r"(?:hvs\.|s\.[A-Za-z0-9]{24,}\.)[A-Za-z0-9]{0,100}"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2","PCI_DSS"],
        description="HashiCorp Vault token. Grants access to all secrets within the token's policy scope.",
        remediation=(
            "1. Revoke immediately: `vault token revoke <token>`.\n"
            "2. Audit Vault audit log for unauthorized secret reads.\n"
            "3. Use AppRole or Kubernetes auth for short-lived tokens."
        ),
    ),
    DetectionPattern(
        name="Datadog API Key",
        regex=_p(r"(?:DD_API_KEY|datadog[_\-]?api[_\-]?key)\s*[=:]\s*['\"]?([a-f0-9]{32})['\"]?"),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="Datadog API key. Grants access to metrics, logs, and infrastructure data.",
        remediation="Rotate at app.datadoghq.com/organization-settings/api-keys.",
    ),
    DetectionPattern(
        name="PagerDuty Integration Key",
        regex=_p(r"(?:pagerduty[_\-]?(?:api[_\-]?)?key|PAGERDUTY_KEY)\s*[=:]\s*['\"]?([A-Za-z0-9+/=]{20,})['\"]?"),
        severity="MEDIUM", category="SECRET", compliance=["SOC2"],
        description="PagerDuty key. Allows creating/managing incidents and accessing alert data.",
        remediation="Rotate at app.pagerduty.com/api_keys.",
    ),
    DetectionPattern(
        name="Shopify Admin API Token",
        regex=_p(r"shpat_[A-Za-z0-9]{32,}"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2","PCI_DSS"],
        description="Shopify Admin API access token. Full access to store: orders, customers, products.",
        remediation="Rotate in Shopify Partner Dashboard. Audit order and customer data access.",
    ),
    DetectionPattern(
        name="Cloudflare API Token",
        regex=_p(r"(?:cloudflare[_\-]?(?:api[_\-]?)?token|CF_API_TOKEN)\s*[=:]\s*['\"]?([A-Za-z0-9_\-]{40,})['\"]?"),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="Cloudflare API token. May allow DNS manipulation, zone management, or DDoS bypass.",
        remediation="Rotate at dash.cloudflare.com/profile/api-tokens.",
    ),
    DetectionPattern(
        name="Okta API Token",
        regex=_p(r"(?:okta[_\-]?(?:api[_\-]?)?token|OKTA_TOKEN)\s*[=:]\s*['\"]?([0-9a-zA-Z_\-]{40,})['\"]?"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2","HIPAA"],
        description="Okta API token. Admin access to identity provider — controls all user authentication.",
        remediation="Revoke at your Okta admin console → Security → API Tokens.",
    ),
    DetectionPattern(
        name="Splunk HEC Token",
        regex=_p(r"(?:splunk[_\-]?(?:hec[_\-]?)?token|SPLUNK_TOKEN)\s*[=:]\s*['\"]?([A-Za-z0-9\-]{36,})['\"]?"),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="Splunk HTTP Event Collector token. Allows injecting log data into Splunk.",
        remediation="Rotate in Splunk Settings → Data Inputs → HTTP Event Collector.",
    ),

    # Production Database Credentials ══════════════════════════════════════

    DetectionPattern(
        name="Production Database URL (with credentials)",
        regex=_p(r"(?:DATABASE_URL|DB_URL|database_url)\s*[=:]\s*['\"]?((?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|mssql)://[^:@\s'\"]{1,60}:[^@\s'\"]{1,100}@[^\s'\"]{3,})['\"]?", re.MULTILINE),
        severity="CRITICAL", category="SECRET", compliance=["GDPR","HIPAA","PCI_DSS","SOC2"],
        description="Production database connection string with embedded credentials.",
        remediation=(
            "1. Rotate database password immediately.\n"
            "2. Add .env, .env.* to .gitignore.\n"
            "3. Use secrets manager injection at runtime.\n"
            "4. Enable database audit logging for breach assessment."
        ),
    ),
    DetectionPattern(
        name="Generic Password Assignment",
        regex=_p(r"(?:password|passwd|pwd|pass)\s*[=:]\s*['\"]([^'\"]{8,})['\"]"),
        severity="HIGH", category="SECRET", compliance=["GDPR","HIPAA","PCI_DSS","SOC2"],
        description="Hardcoded password string detected in source code or configuration.",
        remediation=(
            "1. Remove the hardcoded password immediately.\n"
            "2. Use environment variables or a secrets manager.\n"
            "3. If this is a service password, rotate it now."
        ),
    ),
    DetectionPattern(
        name="Generic Secret/Token Assignment",
        regex=_p(r"(?:secret|token|api_key|apikey|auth_token)\s*[=:]\s*['\"]([A-Za-z0-9_\-+/]{20,})['\"]"),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="Hardcoded secret or token in code or configuration.",
        remediation=(
            "1. Remove the hardcoded value.\n"
            "2. Move to environment variable or secrets manager.\n"
            "3. Rotate the exposed value."
        ),
    ),
    DetectionPattern(
        name="JWT Token (hardcoded)",
        regex=_p(r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}"),
        severity="HIGH", category="CRYPTO", compliance=["SOC2","GDPR"],
        description="JSON Web Token (JWT) found. May contain user identity or session data.",
        remediation=(
            "1. If a signing secret, rotate the JWT secret immediately and invalidate all sessions.\n"
            "2. If an active bearer token, revoke it.\n"
            "3. Never hardcode JWT tokens in source code."
        ),
    ),

    # Private Key Material ══════════════════════════════════════════════════

    DetectionPattern(
        name="RSA Private Key",
        regex=_p(r"-----BEGIN RSA PRIVATE KEY-----"),
        severity="CRITICAL", category="CRYPTO", compliance=["SOC2","PCI_DSS","HIPAA"],
        description="RSA private key. Enables impersonation, decryption, and TLS MITM attacks.",
        remediation=(
            "1. Revoke associated certificates immediately (Let's Encrypt, AWS ACM, etc.).\n"
            "2. Generate a new key pair.\n"
            "3. Never store private keys in filesystems accessible to applications.\n"
            "4. Use HSM or cloud KMS for key storage."
        ),
    ),
    DetectionPattern(
        name="EC Private Key",
        regex=_p(r"-----BEGIN EC PRIVATE KEY-----"),
        severity="CRITICAL", category="CRYPTO", compliance=["SOC2","PCI_DSS"],
        description="Elliptic Curve private key. Used for TLS, JWT signing, and code signing.",
        remediation="Revoke associated certificates immediately. Generate new key pair via HSM or KMS.",
    ),
    DetectionPattern(
        name="OpenSSH Private Key",
        regex=_p(r"-----BEGIN OPENSSH PRIVATE KEY-----"),
        severity="CRITICAL", category="CRYPTO", compliance=["SOC2","HIPAA"],
        description="OpenSSH private key. Enables SSH access to any server that trusts the public key.",
        remediation=(
            "1. Remove the public key from all authorized_keys files immediately.\n"
            "2. Generate a new SSH key pair.\n"
            "3. Audit SSH access logs for unauthorized logins."
        ),
    ),
    DetectionPattern(
        name="PGP Private Key",
        regex=_p(r"-----BEGIN PGP PRIVATE KEY BLOCK-----"),
        severity="CRITICAL", category="CRYPTO", compliance=["SOC2","GDPR"],
        description="PGP private key. Enables decryption of PGP-encrypted messages and impersonation.",
        remediation="Revoke the PGP key on keyservers. Notify recipients who may have sent encrypted data.",
    ),
    DetectionPattern(
        name="PKCS#8 Private Key",
        regex=_p(r"-----BEGIN PRIVATE KEY-----"),
        severity="CRITICAL", category="CRYPTO", compliance=["SOC2","PCI_DSS"],
        description="PKCS#8 private key (generic). Used for TLS, JWT, and authentication.",
        remediation="Revoke associated certificates/identities. Generate new key material.",
    ),

    # PII — Personally Identifiable Information ═════════════════════════════

    DetectionPattern(
        name="US Social Security Number (SSN)",
        regex=_p(r"(?<!\d)(?!000|666|9\d{2})\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}(?!\d)"),
        severity="CRITICAL", category="PII", compliance=["HIPAA","PCI_DSS","GDPR"],
        description="US Social Security Number. Direct identity theft risk. HIPAA and GDPR reportable.",
        remediation=(
            "1. This is a potential data breach notification requirement.\n"
            "2. Identify the data source and delete or encrypt immediately.\n"
            "3. Assess whether breach notification is required (HIPAA 60-day rule).\n"
            "4. Implement data minimization — never store SSNs in flat files."
        ),
    ),
    DetectionPattern(
        name="Credit Card Number (Luhn-validated)",
        regex=_p(r"(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})"),
        severity="CRITICAL", category="PII", compliance=["PCI_DSS","GDPR"],
        description="Credit card number (passes Luhn check). PCI-DSS reportable breach.",
        remediation=(
            "1. PCI-DSS requires immediate incident response.\n"
            "2. Notify your PCI QSA immediately.\n"
            "3. Delete or tokenize all PAN data.\n"
            "4. Card brands may require notification within 24 hours."
        ),
    ),
    DetectionPattern(
        name="IBAN (International Bank Account Number)",
        regex=_p(r"(?<![A-Z0-9])[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}(?![A-Z0-9])"),
        severity="HIGH", category="PII", compliance=["GDPR","PCI_DSS"],
        description="IBAN (bank account number). Financial data requiring GDPR protection.",
        remediation="Delete or encrypt. Assess if GDPR breach notification to supervisory authority required.",
    ),
    DetectionPattern(
        name="Passport Number (multi-country)",
        regex=_p(r"(?:passport|document)\s*(?:no|number|#)\s*[:\.]?\s*([A-Z]{1,2}[0-9]{6,9})\b"),
        severity="HIGH", category="PII", compliance=["GDPR","HIPAA"],
        description="Passport number. Government-issued ID — GDPR special category data.",
        remediation="Delete or encrypt. GDPR breach notification likely required if exposed externally.",
    ),
    DetectionPattern(
        name="UK National Insurance Number",
        regex=_p(r"(?<![A-Z])[A-CEGHJ-PR-TW-Z]{2}[0-9]{6}[A-D](?![A-Z0-9])"),
        severity="HIGH", category="PII", compliance=["GDPR"],
        description="UK National Insurance Number. Government ID with serious identity theft risk.",
        remediation="Delete or encrypt immediately. GDPR breach notification may be required.",
    ),
    DetectionPattern(
        name="Email Address (bulk exposure)",
        regex=_p(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}"),
        severity="LOW", category="PII", compliance=["GDPR","HIPAA"],
        description="Email address. PII under GDPR. Severity escalates when found in bulk.",
        remediation="Ensure email data is access-controlled and encrypted at rest per GDPR Art. 32.",
        redact=False,
    ),
    DetectionPattern(
        name="Phone Number (E.164)",
        regex=_p(r"(?<!\d)(\+1[-.\s]?)?(?:\(?[2-9]\d{2}\)?[-.\s]?)?[2-9]\d{2}[-.\s]?\d{4}(?!\d)"),
        severity="LOW", category="PII", compliance=["GDPR","HIPAA","TCPA"],
        description="Phone number. PII under GDPR; TCPA compliance implications.",
        remediation="Ensure phone data is access-controlled and not exposed in logs or backups.",
        redact=False,
    ),
    DetectionPattern(
        name="Date of Birth",
        regex=_p(r"(?:dob|date.of.birth|birthdate|birth.date)\s*[=:]\s*['\"]?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})['\"]?"),
        severity="MEDIUM", category="PII", compliance=["GDPR","HIPAA","COPPA"],
        description="Date of birth. COPPA implications if under 13; GDPR special category.",
        remediation="Encrypt at rest. Assess data minimization — is DOB actually required for this use case?",
    ),

    # Configuration & Infrastructure Vulnerabilities ════════════════════════

    DetectionPattern(
        name="Debug Mode Enabled (Production Risk)",
        regex=_p(r"(?:DEBUG|debug)\s*[=:]\s*(?:True|true|1|yes|on)\b"),
        severity="HIGH", category="CONFIG", compliance=["SOC2","PCI_DSS"],
        description="Debug mode enabled in what may be a production configuration. Exposes stack traces, internal paths, and error details.",
        remediation="Set DEBUG=False in production. Use environment-specific config files. Never commit production configs.",
        redact=False,
    ),
    DetectionPattern(
        name="TLS/SSL Verification Disabled",
        regex=_p(r"(?:VERIFY|verify)\s*[=:]\s*(?:False|false|0|no|off)\b|ssl_verify\s*=\s*False|verify=False"),
        severity="HIGH", category="CONFIG", compliance=["SOC2","PCI_DSS","HIPAA"],
        description="TLS/SSL certificate verification disabled. Enables MITM attacks — data interception.",
        remediation=(
            "1. Enable certificate verification: verify=True.\n"
            "2. If self-signed cert: use certifi or a custom CA bundle, don't disable verification.\n"
            "3. This is a PCI-DSS violation if processing cardholder data."
        ),
        redact=False,
    ),
    DetectionPattern(
        name="World-Writable File Permission (chmod 777)",
        regex=_p(r"chmod\s+(?:a\+rwx|0?777)\b|os\.chmod\([^,]+,\s*0o?777\)"),
        severity="HIGH", category="CONFIG", compliance=["SOC2","PCI_DSS"],
        description="World-writable file permissions set in code. Privilege escalation risk.",
        remediation="Use least-privilege permissions (600 for secrets, 755 for executables). Audit existing file permissions.",
        redact=False,
    ),
    DetectionPattern(
        name="Weak Cryptographic Algorithm",
        regex=_p(r"(?:MD5|md5|SHA1|sha1|DES|3DES|RC4|rc4)\s*\(|hashlib\.(?:md5|sha1)\b"),
        severity="MEDIUM", category="CONFIG", compliance=["SOC2","PCI_DSS","HIPAA"],
        description="Weak or deprecated cryptographic algorithm detected. Vulnerable to known attacks.",
        remediation=(
            "1. Replace MD5/SHA1 with SHA-256 or SHA-3 for integrity.\n"
            "2. Replace DES/3DES with AES-256-GCM.\n"
            "3. RC4 is broken — use ChaCha20-Poly1305."
        ),
        redact=False,
    ),
    DetectionPattern(
        name="Hardcoded Internal IP Address",
        regex=_p(r"(?<!\d)(?:10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|172\.(?:1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3}|192\.168\.[0-9]{1,3}\.[0-9]{1,3})(?!\d)"),
        severity="LOW", category="NETWORK", compliance=["SOC2"],
        description="Internal IP address hardcoded. Reveals network topology; breaks in cloud environments.",
        remediation="Replace with DNS hostnames or service discovery. Remove from source code.",
        redact=False,
    ),
    DetectionPattern(
        name="SQL Injection Risk (string concatenation)",
        regex=_p(r"""(?:execute|cursor\.execute|db\.query)\s*\([^)]*(?:\+|\%\s+|\.format\(|f["'])[^)]*(?:SELECT|INSERT|UPDATE|DELETE|DROP)"""),
        severity="HIGH", category="CONFIG", compliance=["SOC2","PCI_DSS"],
        description="Potential SQL injection via string concatenation instead of parameterized queries.",
        remediation=(
            "1. Use parameterized queries: cursor.execute('SELECT * WHERE id=%s', (user_id,)).\n"
            "2. Use an ORM with automatic parameter binding.\n"
            "3. Apply input validation as defense in depth."
        ),
        redact=False,
    ),

    # Infrastructure-as-Code Secrets ════════════════════════════════════════

    DetectionPattern(
        name="Kubernetes Secret Manifest (Base64 data)",
        regex=_p(r"kind:\s*Secret[\s\S]{0,200}?data:\s*[\r\n]+(?:\s+\S+:\s*[A-Za-z0-9+/=]{20,})", re.MULTILINE),
        severity="HIGH", category="CRYPTO", compliance=["SOC2","PCI_DSS"],
        description="Kubernetes Secret manifest with base64-encoded credentials. Committing to git exposes all values.",
        remediation=(
            "1. Remove the manifest from version control immediately.\n"
            "2. Use External Secrets Operator or Sealed Secrets.\n"
            "3. Rotate all values encoded in the manifest."
        ),
    ),
    DetectionPattern(
        name="Docker Registry Auth Credential",
        regex=_p(r'"auth"\s*:\s*"([A-Za-z0-9+/]{20,}={0,2})"'),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="Docker registry authentication credential in config.json (base64 user:password).",
        remediation=(
            "1. Rotate registry credentials.\n"
            "2. Use docker credential helpers instead of config.json.\n"
            "3. For CI/CD, use OIDC token authentication."
        ),
    ),
    DetectionPattern(
        name="Terraform State with Sensitive Values",
        regex=_p(r'"sensitive_values"\s*:\s*\{[^}]*"[^"]+"\s*:\s*true', re.MULTILINE),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="Terraform state file with marked sensitive values. State files contain plaintext secrets.",
        remediation=(
            "1. Move Terraform state to remote backend (S3+DynamoDB, Terraform Cloud) with encryption.\n"
            "2. Add .tfstate, .tfstate.backup to .gitignore.\n"
            "3. Rotate any credentials in this state file."
        ),
    ),
    DetectionPattern(
        name="Ansible Vault Unencrypted Variable",
        regex=_p(r"ansible_(?:ssh_pass|become_pass|sudo_pass|vault_password)\s*:\s*\S+"),
        severity="HIGH", category="SECRET", compliance=["SOC2"],
        description="Ansible plaintext credential. Should be encrypted with ansible-vault.",
        remediation="Encrypt with `ansible-vault encrypt_string`. Never store Ansible passwords in plaintext.",
    ),

    # MCP / AI Tool Config Files — 2025 Attack Surface ═════════════════════

    DetectionPattern(
        name="MCP Config — API Key in MCP Server Config",
        regex=_p(r'"(?:api_key|apiKey|API_KEY|token|secret|key)"\s*:\s*"([A-Za-z0-9_\-+/]{20,})"'),
        severity="HIGH", category="SECRET", compliance=["SOC2","GDPR"],
        description=(
            "API key hardcoded in MCP server config (claude_desktop_config.json, .cursor/mcp.json, etc.). "
            "GitGuardian found 24,008 secrets in MCP configs in 2025 — 2,117 still valid. "
            "MCP configs are synced to cloud and often committed to git accidentally."
        ),
        remediation=(
            "1. Move API keys to environment variables referenced as {\"env\": \"VAR_NAME\"}.\n"
            "2. Rotate the exposed key immediately.\n"
            "3. Add mcp.json, claude_desktop_config.json to .gitignore.\n"
            "4. Review your MCP server provider's access logs."
        ),
    ),

    # Network Credentials ═══════════════════════════════════════════════════

    DetectionPattern(
        name="FTP Credentials in URL",
        regex=_p(r"ftp://[^:@\s]{1,60}:[^@\s]{1,60}@"),
        severity="HIGH", category="NETWORK", compliance=["SOC2","PCI_DSS"],
        description="FTP URL with embedded credentials. FTP is unencrypted — credentials in transit.",
        remediation="Use SFTP or FTPS. Remove credentials from URLs. Rotate exposed password.",
    ),
    DetectionPattern(
        name="HTTP Basic Auth in URL",
        regex=_p(r"https?://[^:@\s]{1,60}:[^@\s]{1,60}@[^\s]{3,}"),
        severity="HIGH", category="NETWORK", compliance=["SOC2"],
        description="HTTP URL with embedded credentials (Basic Auth format). Credentials visible in logs.",
        remediation="Move credentials to Authorization header. Never embed in URLs — they appear in logs.",
    ),
    DetectionPattern(
        name="S3 Bucket Name Disclosure",
        regex=_p(r"s3://[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9]"),
        severity="LOW", category="NETWORK", compliance=["SOC2"],
        description="S3 bucket name. Check bucket ACL — may be publicly accessible.",
        remediation="Verify bucket ACL with `aws s3api get-bucket-acl`. Disable public access unless intentional.",
        redact=False,
    ),
    DetectionPattern(
        name="Google Gemini / PaLM API Key",
        regex=_p(r"AIza[0-9A-Za-z_\-]{30,}"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2"],
        description="Google AI API key (Gemini/PaLM). Grants access to Gemini models with billing implications.",
        remediation=(
            "1. Revoke at console.cloud.google.com/apis/credentials.\n"
            "2. Audit usage in Cloud Console.\n"
            "3. Store in environment variables. Never commit."
        ),
    ),
    DetectionPattern(
        name="Groq API Key",
        regex=_p(r"gsk_[A-Za-z0-9]{40,}"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2"],
        description="Groq API key. Grants access to Groq inference with billing implications.",
        remediation=(
            "1. Rotate at console.groq.com/keys.\n"
            "2. Review usage logs for unauthorized requests.\n"
            "3. Store in environment variables. Never commit."
        ),
    ),
    DetectionPattern(
        name="Mistral API Key",
        regex=_p(r"(?:mistral-)?[A-Za-z0-9]{40,}"),
        severity="MEDIUM", category="SECRET", compliance=["SOC2"],
        description="Possible Mistral API key. Verify at console.mistral.ai.",
        remediation=(
            "1. Check if this is a real Mistral key at console.mistral.ai/api-keys.\n"
            "2. If valid, rotate immediately.\n"
            "3. Store in environment variables. Never commit."
        ),
    ),
    DetectionPattern(
        name="Replicate API Token",
        regex=_p(r"r8_[A-Za-z0-9]{40,}"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2"],
        description="Replicate API token. Grants access to ML model inference with billing implications.",
        remediation=(
            "1. Rotate at replicate.com/account/api-tokens.\n"
            "2. Review usage logs for unauthorized requests.\n"
            "3. Store in environment variables. Never commit."
        ),
    ),
    DetectionPattern(
        name="Together AI API Key",
        regex=_p(r"tok_[A-Za-z0-9]{40,}"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2"],
        description="Together AI API key. Grants access to ML inference with billing implications.",
        remediation=(
            "1. Rotate at api.together.xyz/settings/api-keys.\n"
            "2. Review usage logs for unauthorized requests.\n"
            "3. Store in environment variables. Never commit."
        ),
    ),
    DetectionPattern(
        name="DeepSeek API Key",
        regex=_p(r"sk-[a-f0-9]{32,}"),
        severity="MEDIUM", category="SECRET", compliance=["SOC2"],
        description="Possible DeepSeek API key. Verify at platform.deepseek.com.",
        remediation=(
            "1. Check if this is a real DeepSeek key at platform.deepseek.com.\n"
            "2. If valid, rotate immediately.\n"
            "3. Store in environment variables. Never commit."
        ),
    ),
    DetectionPattern(
        name="xAI / Grok API Key",
        regex=_p(r"xai-[A-Za-z0-9]{40,}"),
        severity="CRITICAL", category="SECRET", compliance=["SOC2"],
        description="xAI (Grok) API key. Grants access to Grok models with billing implications.",
        remediation=(
            "1. Rotate at console.x.ai/api-keys.\n"
            "2. Review usage logs for unauthorized requests.\n"
            "3. Store in environment variables. Never commit."
        ),
    ),
]

# High-entropy secret detection (Shannon entropy) ═══════════════════════════

def _shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    length = len(data)
    return -sum((c / length) * math.log2(c / length) for c in freq.values() if c > 0)
    """_shannon_entropy."""
    """_shannon_entropy."""

HIGH_ENTROPY_THRESHOLD = 4.5
HIGH_ENTROPY_MIN_LEN   = 20

def _check_high_entropy(line: bytes, file_path: str) -> Optional[Finding]:
    """Detect high-entropy strings that look like secrets but don't match known patterns."""
    for token in re.findall(rb'[A-Za-z0-9+/=_\-]{%d,}' % HIGH_ENTROPY_MIN_LEN, line):
        entropy = _shannon_entropy(token)
        if entropy >= HIGH_ENTROPY_THRESHOLD and len(token) >= HIGH_ENTROPY_MIN_LEN:
            return Finding(
                file_path=file_path, line_number=0, line_preview="",
                pattern_name="High Entropy String",
                severity="MEDIUM", category="SECRET",
                compliance=["SOC2"],
                remediation="High entropy string may be a secret. Verify manually.",
                match_preview=token[:8].decode("utf-8","replace") + "***",
                entropy=entropy,
            )
    return None

# ─── Context-Aware Confidence Scoring ────────────────────────────────────────

TEST_PATH_RE   = re.compile(r'(?:test|spec|fixture|mock|example|sample|demo|fake|stub|dummy|__test__|\.test\.|\.spec\.|_test\.|_spec\.)', re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r'^(?:your[_\-]?(?:api[_\-]?key|secret|token|password)|insert[_\-]?(?:key|token)|xxx+|abc+123*|password123|changeme|replace[_\-]?me|example[_\-]?(?:key|token|secret)|<[^>]+>|\$\{[^}]+\}|\{\{[^}]+\}\}|XXXXXXXX+)$', re.IGNORECASE)
COMMENT_LINE_RE = re.compile(r'^\s*(?:#|//|/\*|\*|--|;|rem\s)', re.IGNORECASE)

def compute_confidence(file_path: str, match_preview: str, entropy: float, category: str, line_raw: str = "") -> float:
    """Compute confidence."""
    confidence = 1.0
    if TEST_PATH_RE.search(file_path):
        confidence *= 0.15
    val = match_preview.replace("***", "")
    if PLACEHOLDER_RE.match(val):
        confidence *= 0.05
    if line_raw and COMMENT_LINE_RE.match(line_raw):
        confidence *= 0.25
    if entropy < 2.5 and category == "SECRET":
        confidence *= 0.4
    if entropy > 4.5:
        confidence = min(1.0, confidence * 1.3)
    if category == "CRYPTO":
        confidence = max(confidence, 0.85)
    if category == "PII":
        confidence = max(confidence, 0.7)
    return round(min(1.0, confidence), 3)

# ─── Core Scanner ─────────────────────────────────────────────────────────────

def _luhn_valid(s: str) -> bool:
    digits = [int(c) for c in s if c.isdigit()]
    if len(digits) < 13:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        total += d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2)
    return total % 10 == 0
    """_luhn_valid."""
    """_luhn_valid."""

def _redact(match: bytes) -> str:
    s = match.decode("utf-8", errors="replace")
    if len(s) <= 8:
        return "***"
    return s[:4] + "***" + s[-4:]
    """_redact."""
    """_redact."""

def scan_file_bytes(data: bytes, file_path: str, patterns: List[DetectionPattern]) -> List[Finding]:
    """Scan file bytes."""
    findings = []
    lines = data.split(b"\n")
    for line_no, line in enumerate(lines, 1):
        if len(line) > 2000:
            line = line[:2000]
        line_str = line.decode("utf-8", errors="replace")
        for pat in patterns:
            for m in pat.regex.finditer(line):
                raw_match = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
                # Luhn validation for credit cards
                if pat.name == "Credit Card Number (Luhn-validated)":
                    card_digits = re.sub(rb'[\s\-]', b'', raw_match)
                    if not _luhn_valid(card_digits.decode("utf-8", errors="replace")):
                        continue
                preview = _redact(raw_match) if pat.redact else raw_match.decode("utf-8","replace")
                entropy = _shannon_entropy(raw_match)
                # Redact line preview
                safe_line = re.sub(rb'[A-Za-z0-9+/=_\-]{16,}', b'***', line)
                line_preview = safe_line.decode("utf-8", errors="replace")[:200]
                confidence = compute_confidence(file_path, preview, entropy, pat.category, line_str)
                findings.append(Finding(
                    file_path=file_path, line_number=line_no,
                    line_preview=line_preview,
                    pattern_name=pat.name, severity=pat.severity,
                    category=pat.category, compliance=pat.compliance,
                    remediation=pat.remediation,
                    match_preview=preview, entropy=round(entropy, 3),
                    confidence=confidence,
                ))
    return findings

def scan_single_file(file_path: str, patterns: List[DetectionPattern]) -> Tuple[List[Finding], int]:
    """Scan single file."""
    try:
        stat = os.stat(file_path)
        size = stat.st_size
        if size == 0:
            return [], 0
        if size > MAX_DEEP_SCAN_BYTES:
            return [], size
        with open(file_path, "rb") as fh:
            if size > 0:
                try:
                    mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
                    data = bytes(mm[:])
                    mm.close()
                except (mmap.error, OSError):
                    data = fh.read()
            else:
                data = fh.read()
        # Quick binary check
        if b"\x00" in data[:512]:
            return [], size
        findings = scan_file_bytes(data, file_path, patterns)
        for f in findings:
            f.file_size = size
        return findings, size
    except (PermissionError, OSError, IOError):
        return [], 0

def walk_files(directory: str, ignores: List[str]) -> Tuple[List[str], int]:
    """Walk directory, returning (file_paths, skipped_count)."""
    ignore_patterns = list(ignores)
    ignore_file = os.path.join(directory, ".sentinelignore")
    if os.path.exists(ignore_file):
        with open(ignore_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    ignore_patterns.append(line)

    skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv',
                 'dist', 'build', '.pytest_cache', '.tox', 'coverage'}
    files, skipped = [], 0
    for root, dirs, fnames in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
        for fname in fnames:
            ext = Path(fname).suffix.lower()
            full = os.path.join(root, fname)
            rel  = os.path.relpath(full, directory)
            if ext in SKIP_EXTENSIONS:
                skipped += 1
                continue
            if any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(fname, pat) for pat in ignore_patterns):
                skipped += 1
                continue
            files.append(full)
    return files, skipped

def compute_risk_score(findings: List[Finding]) -> int:
    """Compute risk score."""
    if not findings:
        return 0
    weights = {"CRITICAL": 30, "HIGH": 15, "MEDIUM": 5, "LOW": 1}
    live_bonus = sum(20 for f in findings if f.verified is True)
    base = sum(weights.get(f.severity, 0) for f in findings) + live_bonus
    return min(100, int(base))

def run_scan(directory: str, ignores: List[str] = None, max_workers: int = 8,
             severity_filter: List[str] = None, quiet: bool = False) -> ScanStats:
    """Run scan."""
    ignores = ignores or []
    t0 = time.time()
    files, skipped = walk_files(directory, ignores)

    all_findings: List[Finding] = []
    total_bytes = 0

    if not quiet:
        print(f"\n🔍 Scanning {len(files)} files in {directory}...", file=sys.stderr)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(scan_single_file, fp, PATTERNS): fp for fp in files}
        done = 0
        for fut in concurrent.futures.as_completed(futures):
            findings, size = fut.result()
            all_findings.extend(findings)
            total_bytes += size
            done += 1
            if not quiet and done % 500 == 0:
                print(f"  ↳ {done}/{len(files)} files scanned...", file=sys.stderr)

    # Sort by severity then file
    all_findings.sort(key=lambda f: (-f.severity_rank, f.file_path, f.line_number))

    # Apply severity filter
    if severity_filter:
        all_findings = [f for f in all_findings if f.severity in severity_filter]

    duration = round(time.time() - t0, 2)
    risk = compute_risk_score(all_findings)

    if not quiet:
        spd = total_bytes / (1024 * 1024 * max(duration, 0.01))
        print(f"  ↳ Done in {duration}s ({spd:.1f} MB/s). {len(all_findings)} findings.", file=sys.stderr)

    return ScanStats(
        directory=directory,
        scan_time=datetime.now(timezone.utc).isoformat(),
        duration_seconds=duration,
        files_scanned=len(files),
        files_skipped=skipped,
        total_bytes_scanned=total_bytes,
        findings=all_findings,
        risk_score=risk,
    )

# ─── Archive Scanner ──────────────────────────────────────────────────────────

def _scan_archive_member(data: bytes, virtual_path: str) -> List[Finding]:
    if b"\x00" in data[:512]:
        return []
    return scan_file_bytes(data, virtual_path, PATTERNS)
    """_scan_archive_member."""
    """_scan_archive_member."""

def scan_zip(archive_path: str) -> List[Finding]:
    """Scan zip."""
    findings = []
    try:
        with zipfile.ZipFile(archive_path, 'r') as zf:
            total = 0
            for info in zf.infolist():
                ext = Path(info.filename).suffix.lower()
                if ext in SKIP_EXTENSIONS or info.file_size > MAX_ARCHIVE_FILE_BYTES:
                    continue
                total += info.file_size
                if total > MAX_ARCHIVE_TOTAL_BYTES:
                    break
                try:
                    data = zf.read(info.filename)
                    vpath = f"{archive_path}::{info.filename}"
                    findings.extend(_scan_archive_member(data, vpath))
                except Exception:
                    continue
    except (zipfile.BadZipFile, Exception):
        pass
    return findings

def scan_tar(archive_path: str) -> List[Finding]:
    """Scan tar."""
    findings = []
    try:
        with tarfile.open(archive_path, 'r:*') as tf:
            total = 0
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                if os.path.isabs(member.name) or '..' in member.name.split(os.sep):
                    continue
                ext = Path(member.name).suffix.lower()
                if ext in SKIP_EXTENSIONS or member.size > MAX_ARCHIVE_FILE_BYTES:
                    continue
                total += member.size
                if total > MAX_ARCHIVE_TOTAL_BYTES:
                    break
                try:
                    fobj = tf.extractfile(member)
                    if fobj is None:
                        continue
                    data = fobj.read()
                    vpath = f"{archive_path}::{member.name}"
                    findings.extend(_scan_archive_member(data, vpath))
                except Exception:
                    continue
    except (tarfile.TarError, Exception):
        pass
    return findings

def scan_archives(directory: str, quiet: bool = False) -> Tuple[List[Finding], int]:
    """Scan archives."""
    findings, count = [], 0
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {'.git','node_modules','__pycache__'}]
        for fname in files:
            fpath = os.path.join(root, fname)
            lower = fname.lower()
            if lower.endswith('.zip'):
                findings.extend(scan_zip(fpath)); count += 1
            elif any(lower.endswith(x) for x in ('.tar','.tar.gz','.tgz','.tar.bz2','.gz','.bz2')):
                findings.extend(scan_tar(fpath)); count += 1
    if not quiet and count:
        print(f"📦 Scanned {count} archives → {len(findings)} findings inside", file=sys.stderr)
    return findings, count

# ─── Git History Scanner ──────────────────────────────────────────────────────

def scan_git_history(directory: str, max_commits: int = 500, quiet: bool = False) -> Tuple[List[Finding], int]:
    """Walk git commit history and scan each diff for secrets."""
    findings = []
    commits_scanned = 0
    try:
        result = subprocess.run(
            ["git", "-C", directory, "log", "--all", "--format=%H", f"-{max_commits}"],
            capture_output=True, text=True, timeout=60
        )
        commits = [c.strip() for c in result.stdout.strip().split("\n") if c.strip()]
        if not quiet:
            print(f"🔀 Scanning {len(commits)} git commits...", file=sys.stderr)
        for commit_hash in commits:
            diff = subprocess.run(
                ["git", "-C", directory, "show", "--unified=0", commit_hash],
                capture_output=True, timeout=30
            )
            if diff.returncode != 0:
                continue
            lines = diff.stdout.split(b"\n")
            current_file = f"git:{commit_hash[:8]}:unknown"
            for line_no, line in enumerate(lines):
                if line.startswith(b"+++ b/"):
                    current_file = f"git:{commit_hash[:8]}:{line[6:].decode('utf-8','replace')}"
                elif line.startswith(b"+") and not line.startswith(b"+++"):
                    content = line[1:]
                    for pat in PATTERNS:
                        for m in pat.regex.finditer(content):
                            raw = m.group(1) if m.lastindex else m.group(0)
                            preview = _redact(raw) if pat.redact else raw.decode("utf-8","replace")
                            findings.append(Finding(
                                file_path=current_file, line_number=line_no,
                                line_preview=content.decode("utf-8","replace")[:200],
                                pattern_name=pat.name, severity=pat.severity,
                                category=pat.category, compliance=pat.compliance,
                                remediation=pat.remediation,
                                match_preview=preview, entropy=_shannon_entropy(raw),
                            ))
            commits_scanned += 1
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        if not quiet:
            print(f"⚠️  Git history scan error: {e}", file=sys.stderr)
    if not quiet and commits_scanned:
        print(f"  ↳ {commits_scanned} commits → {len(findings)} historical findings", file=sys.stderr)
    return findings, commits_scanned

# ─── Live Credential Verification ────────────────────────────────────────────

def _http(url: str, headers: dict, data: bytes = None, method: str = "GET", timeout: int = 8) -> Tuple[int, Any]:
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
            try:
                return r.status, json.loads(body)
            except json.JSONDecodeError:
                return r.status, {"raw": body}
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}
    """_http."""
    """_http."""

def _vr(finding_id: str, name: str, live: Optional[bool], identity: Optional[str], blast: str, err: Optional[str] = None) -> VerificationResult:
    return VerificationResult(finding_id=finding_id, pattern_name=name, is_live=live, identity=identity, blast_radius=blast, error=err)
    """_vr."""
    """_vr."""

def verify_aws(key_id: str, secret: str) -> VerificationResult:
    """Verify aws."""
    fid = hashlib.md5(f"AWS:{key_id}".encode()).hexdigest()[:8]
    try:
        now = datetime.now(timezone.utc)
        amz_date = now.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = now.strftime('%Y%m%d')
        region, service = "us-east-1", "sts"
        host = f"{service}.amazonaws.com"
        payload = "Action=GetCallerIdentity&Version=2011-06-15"
        canonical_headers = f"content-type:application/x-www-form-urlencoded\nhost:{host}\nx-amz-date:{amz_date}\n"
        signed_headers = "content-type;host;x-amz-date"
        payload_hash = hashlib.sha256(payload.encode()).hexdigest()
        canonical = f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        scope = f"{date_stamp}/{region}/{service}/aws4_request"
        sts = (f"AWS4-HMAC-SHA256\n{amz_date}\n{scope}\n" + hashlib.sha256(canonical.encode()).hexdigest())
        def sign(key, msg):
            """Sign."""
            return hmac.new(key, msg.encode(), hashlib.sha256).digest()
        sig_key = sign(sign(sign(sign(f"AWS4{secret}".encode(), date_stamp), region), service), "aws4_request")
        sig = hmac.new(sig_key, sts.encode(), hashlib.sha256).hexdigest()
        auth = f"AWS4-HMAC-SHA256 Credential={key_id}/{scope}, SignedHeaders={signed_headers}, Signature={sig}"
        req = urllib.request.Request(
            f"https://{host}/", data=payload.encode(),
            headers={"Content-Type":"application/x-www-form-urlencoded","x-amz-date":amz_date,"Authorization":auth},
            method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode()
            arn_m = re.search(r'<Arn>([^<]+)</Arn>', body)
            arn = arn_m.group(1) if arn_m else "unknown"
            return _vr(fid, "AWS Key", True, arn,
                f"🔴 LIVE AWS key. Identity: {arn}. Check CloudTrail immediately. "
                "Rotate in AWS IAM Console NOW.")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return _vr(fid, "AWS Key", False, None, "Credential revoked or invalid.", f"HTTP {e.code}")
        return _vr(fid, "AWS Key", None, None, "Could not verify.", str(e))
    except Exception as e:
        return _vr(fid, "AWS Key", None, None, "Verification attempted but failed.", str(e))

def verify_github(token: str) -> VerificationResult:
    """Verify github."""
    fid = hashlib.md5(f"GH:{token[:10]}".encode()).hexdigest()[:8]
    status, data = _http("https://api.github.com/user", {"Authorization": f"token {token}", "User-Agent": "Sentinel/2.0"})
    if status == 200:
        login = data.get("login", "?")
        return _vr(fid, "GitHub Token", True, f"github/{login}",
            f"🔴 LIVE GitHub token for '{login}'. May have repo/admin scope. Revoke at github.com/settings/tokens NOW.")
    if status == 401:
        return _vr(fid, "GitHub Token", False, None, "Token revoked.", "HTTP 401")
    return _vr(fid, "GitHub Token", None, None, "Could not verify.", f"HTTP {status}")

def verify_stripe(key: str) -> VerificationResult:
    """Verify stripe."""
    fid = hashlib.md5(f"STRIPE:{key[:10]}".encode()).hexdigest()[:8]
    auth = base64.b64encode(f"{key}:".encode()).decode()
    status, data = _http("https://api.stripe.com/v1/balance", {"Authorization": f"Basic {auth}", "User-Agent": "Sentinel/2.0"})
    if status == 200:
        avail = data.get("available", [{}])
        amt = avail[0].get("amount", 0) // 100 if avail else 0
        cur = (avail[0].get("currency","?") if avail else "?").upper()
        return _vr(fid, "Stripe Key", True, f"Stripe account (~{amt} {cur})",
            f"🔴 LIVE Stripe PRODUCTION key. Balance: {amt} {cur}. PCI-DSS breach. Roll at dashboard.stripe.com/apikeys NOW.")
    if status == 401:
        return _vr(fid, "Stripe Key", False, None, "Stripe key revoked.", "HTTP 401")
    return _vr(fid, "Stripe Key", None, None, "Could not verify.", f"HTTP {status}")

def verify_slack(token: str) -> VerificationResult:
    """Verify slack."""
    fid = hashlib.md5(f"SLACK:{token[:10]}".encode()).hexdigest()[:8]
    status, data = _http("https://slack.com/api/auth.test", {"Authorization": f"Bearer {token}", "User-Agent": "Sentinel/2.0"})
    if status == 200 and data.get("ok"):
        return _vr(fid, "Slack Token", True, f"{data.get('user','?')}@{data.get('team','?')}",
            f"🔴 LIVE Slack token. User: {data.get('user','?')}, Workspace: {data.get('team','?')}. Revoke at api.slack.com/apps.")
    if status == 200 and not data.get("ok"):
        return _vr(fid, "Slack Token", False, None, "Token revoked.", data.get("error",""))
    return _vr(fid, "Slack Token", None, None, "Could not verify.", f"HTTP {status}")

def verify_npm(token: str) -> VerificationResult:
    """Verify npm."""
    fid = hashlib.md5(f"NPM:{token[:10]}".encode()).hexdigest()[:8]
    status, data = _http("https://registry.npmjs.org/-/whoami", {"Authorization": f"Bearer {token}", "User-Agent": "Sentinel/2.0"})
    if status == 200:
        user = data.get("username", "?")
        return _vr(fid, "npm Token", True, f"npm/{user}",
            f"🔴 LIVE npm token for '{user}'. Can publish packages → supply chain risk. Revoke at npmjs.com/settings/tokens.")
    if status in (401, 403):
        return _vr(fid, "npm Token", False, None, "Token revoked.", f"HTTP {status}")
    return _vr(fid, "npm Token", None, None, "Could not verify.", f"HTTP {status}")

def verify_openai(key: str) -> VerificationResult:
    """Verify openai."""
    fid = hashlib.md5(f"OPENAI:{key[:10]}".encode()).hexdigest()[:8]
    status, data = _http("https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}", "User-Agent": "Sentinel/2.0"})
    if status == 200:
        models = [m.get("id","") for m in data.get("data",[])][:3]
        return _vr(fid, "OpenAI Key", True, f"OpenAI account (models: {', '.join(models)})",
            f"🔴 LIVE OpenAI API key. Has billing access to GPT models. Rotate at platform.openai.com/api-keys NOW.")
    if status == 401:
        return _vr(fid, "OpenAI Key", False, None, "Key revoked.", "HTTP 401")
    return _vr(fid, "OpenAI Key", None, None, "Could not verify.", f"HTTP {status}")

VERIFIER_DISPATCH = {
    "AWS Secret Access Key":            lambda f: verify_aws("UNKNOWN", f.match_preview.replace("***","")),
    "GitHub Personal Access Token (Classic)": lambda f: verify_github(f.match_preview.replace("***","")),
    "GitHub Fine-Grained PAT":          lambda f: verify_github(f.match_preview.replace("***","")),
    "GitHub OAuth Token":               lambda f: verify_github(f.match_preview.replace("***","")),
    "Stripe Live Secret Key":           lambda f: verify_stripe(f.match_preview.replace("***","")),
    "Slack Bot/User Token":             lambda f: verify_slack(f.match_preview.replace("***","")),
    "npm Auth Token":                   lambda f: verify_npm(f.match_preview.replace("***","")),
    "OpenAI API Key":                   lambda f: verify_openai(f.match_preview.replace("***","")),
}

def verify_all_findings(findings: List[Finding], quiet: bool = False) -> Dict[str, VerificationResult]:
    """Verify all findings."""
    verifiable = [f for f in findings if f.pattern_name in VERIFIER_DISPATCH]
    results = {}
    if not verifiable:
        return results
    if not quiet:
        print(f"\n🔍 Verifying {len(verifiable)} credentials against live APIs...", file=sys.stderr)
    for f in verifiable:
        key = f.fingerprint
        try:
            result = VERIFIER_DISPATCH[f.pattern_name](f)
            result.finding_id = key
            results[key] = result
            if not quiet:
                print(f"  {result.status_emoji} [{f.pattern_name}] in ...{f.file_path[-40:]}:{f.line_number}", file=sys.stderr)
                if result.identity:
                    print(f"     ↳ Identity: {result.identity}", file=sys.stderr)
        except Exception as e:
            if not quiet:
                print(f"  ❌ Verify error for {f.pattern_name}: {e}", file=sys.stderr)
    live = sum(1 for r in results.values() if r.is_live is True)
    if not quiet:
        print(f"  ↳ {live} LIVE credential(s) confirmed out of {len(verifiable)} checked", file=sys.stderr)
    return results

def _truncate_secret(value: str) -> str:
    if len(value) <= 8:
        return value
    return value[:4] + '***' + value[-4:]
    """_truncate_secret."""
    """_truncate_secret."""

# ─── Baseline / Delta Mode ────────────────────────────────────────────────────

def save_baseline(findings: List[Finding], directory: str) -> str:
    """Save baseline."""
    path = os.path.join(directory, BASELINE_FILENAME)
    with open(path, 'w') as f:
        json.dump({
            "created_at": datetime.now(timezone.utc).isoformat(),
            "directory": directory,
            "finding_count": len(findings),
            "fingerprints": {f.fingerprint: {**f.to_dict(), "match_preview": _truncate_secret(f.match_preview)} for f in findings},
        }, f, indent=2)
    return path

def load_baseline(directory: str) -> Optional[Dict]:
    """Load baseline."""
    path = os.path.join(directory, BASELINE_FILENAME)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def compute_delta(findings: List[Finding], baseline: Dict) -> Tuple[List[Finding], int]:
    """Compute delta."""
    known = set(baseline.get("fingerprints", {}).keys())
    new = [f for f in findings if f.fingerprint not in known]
    resolved = len(known - {f.fingerprint for f in findings})
    return new, resolved

# ─── False Positive Management ────────────────────────────────────────────────

def _fp_path(directory: str) -> str:
    return os.path.join(directory, FP_DB_FILENAME)
    """_fp_path."""
    """_fp_path."""

def load_fp_db(directory: str) -> Dict:
    """Load fp db."""
    p = _fp_path(directory)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {"suppressions": {}}

def save_fp_db(db: Dict, directory: str):
    """Save fp db."""
    with open(_fp_path(directory), 'w') as f:
        json.dump(db, f, indent=2)

def add_fp(fingerprint: str, directory: str, reason: str = ""):
    """Add fp."""
    db = load_fp_db(directory)
    db["suppressions"][fingerprint] = {"suppressed_at": datetime.now(timezone.utc).isoformat(), "reason": reason}
    save_fp_db(db, directory)
    print(f"✅ Fingerprint {fingerprint} suppressed in {_fp_path(directory)}")

def apply_fp_filter(findings: List[Finding], directory: str) -> Tuple[List[Finding], int]:
    """Apply fp filter."""
    db = load_fp_db(directory)
    sups = db.get("suppressions", {})
    kept, suppressed = [], 0
    for f in findings:
        if f.fingerprint in sups:
            suppressed += 1
        else:
            kept.append(f)
    return kept, suppressed

# ─── Scan History ─────────────────────────────────────────────────────────────

def save_to_history(stats: ScanStats, live_count: int = 0):
    """Save to history."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    scan_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    record = {
        "scan_id": scan_id, "directory": stats.directory,
        "scan_time": stats.scan_time, "duration": stats.duration_seconds,
        "files_scanned": stats.files_scanned, "risk_score": stats.risk_score,
        "counts": {"critical": len(stats.critical), "high": len(stats.high),
                   "medium": len(stats.medium), "low": len(stats.low)},
        "live_credentials": live_count,
    }
    with open(os.path.join(HISTORY_DIR, f"{scan_id}.json"), 'w') as f:
        json.dump(record, f)

def load_history(limit: int = 20) -> List[Dict]:
    """Load history."""
    if not os.path.exists(HISTORY_DIR):
        return []
    records = []
    for fname in sorted(os.listdir(HISTORY_DIR), reverse=True)[:limit]:
        if fname.endswith('.json'):
            try:
                with open(os.path.join(HISTORY_DIR, fname)) as f:
                    records.append(json.load(f))
            except Exception:
                pass
    return records

# ─── Jira / GitHub Issues Integration ────────────────────────────────────────

def create_jira_ticket(finding: Finding, jira_url: str, jira_user: str, jira_token: str, project_key: str) -> Optional[str]:
    """Create a Jira issue from a finding. Returns issue key or None."""
    payload = json.dumps({
        "fields": {
            "project": {"key": project_key},
            "summary": f"[SENTINEL] {finding.severity} — {finding.pattern_name} in {Path(finding.file_path).name}",
            "description": (
                f"*Sentinel Finding*\n\n"
                f"*Pattern:* {finding.pattern_name}\n"
                f"*Severity:* {finding.severity}\n"
                f"*File:* {finding.file_path}:{finding.line_number}\n"
                f"*Match Preview:* {_truncate_secret(finding.match_preview)}\n"
                f"*Compliance:* {', '.join(finding.compliance)}\n\n"
                f"*Remediation:*\n{finding.remediation}\n\n"
                f"_Generated by Sentinel v{VERSION}_"
            ),
            "issuetype": {"name": "Bug"},
            "priority": {"name": {"CRITICAL":"Highest","HIGH":"High","MEDIUM":"Medium","LOW":"Low"}.get(finding.severity,"Medium")},
            "labels": ["sentinel", "security", finding.severity.lower()],
        }
    }).encode()
    auth = base64.b64encode(f"{jira_user}:{jira_token}".encode()).decode()
    req = urllib.request.Request(
        f"{jira_url.rstrip('/')}/rest/api/2/issue",
        data=payload,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return data.get("key")
    except Exception as e:
        print(f"⚠️  Jira error: {e}", file=sys.stderr)
        return None

def create_github_issue(finding: Finding, github_token: str, repo: str) -> Optional[str]:
    """Create a GitHub issue from a finding. Returns issue URL or None."""
    payload = json.dumps({
        "title": f"[SENTINEL] {finding.severity} — {finding.pattern_name} in {Path(finding.file_path).name}",
        "body": (
            f"## 🔴 Sentinel Security Finding\n\n"
            f"| Field | Value |\n|---|---|\n"
            f"| Pattern | `{finding.pattern_name}` |\n"
            f"| Severity | **{finding.severity}** |\n"
            f"| File | `{finding.file_path}:{finding.line_number}` |\n"
            f"| Match | `{_truncate_secret(finding.match_preview)}` |\n"
            f"| Compliance | {', '.join(finding.compliance)} |\n\n"
            f"### Remediation\n\n```\n{finding.remediation}\n```\n\n"
            f"*Generated by [Sentinel v{VERSION}](https://github.com/sentinel-security/sentinel)*"
        ),
        "labels": ["security", "sentinel", finding.severity.lower()],
    }).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=payload,
        headers={"Authorization": f"token {github_token}", "Content-Type": "application/json", "User-Agent": "Sentinel/2.0"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return data.get("html_url")
    except Exception as e:
        print(f"⚠️  GitHub Issues error: {e}", file=sys.stderr)
        return None

# ─── Export Formats ───────────────────────────────────────────────────────────

def export_json(stats: ScanStats, path: str):
    """Export json."""
    with open(path, 'w') as f:
        json.dump(stats.to_dict(), f, indent=2, default=str)

def export_csv(stats: ScanStats, path: str):
    """Export csv."""
    fields = ["severity","category","pattern_name","file_path","line_number",
              "match_preview","compliance","remediation","confidence","entropy",
              "verified","identity","blast_radius"]
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for finding in stats.findings:
            row = finding.to_dict()
            row['compliance'] = ','.join(row.get('compliance', []))
            w.writerow({k: row.get(k, '') for k in fields})

def export_sarif(stats: ScanStats, path: str):
    """Export sarif."""
    rules = {}
    for p in PATTERNS:
        if p.name not in rules:
            rules[p.name] = {
                "id": re.sub(r'[^A-Za-z0-9]', '', p.name),
                "name": p.name,
                "shortDescription": {"text": p.description},
                "help": {"text": p.remediation},
                "properties": {"security-severity": {"CRITICAL":"9.8","HIGH":"8.0","MEDIUM":"5.0","LOW":"3.0","INFO":"1.0"}.get(p.severity,"5.0")},
            }
    results = []
    for f in stats.findings:
        rule_id = re.sub(r'[^A-Za-z0-9]', '', f.pattern_name)
        results.append({
            "ruleId": rule_id,
            "level": {"CRITICAL":"error","HIGH":"error","MEDIUM":"warning","LOW":"note","INFO":"none"}.get(f.severity,"warning"),
            "message": {"text": f"{f.pattern_name}: {f.match_preview}"},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": f.file_path},"region": {"startLine": f.line_number}}}],
            "properties": {"severity": f.severity, "category": f.category, "compliance": f.compliance},
        })
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "Sentinel", "version": VERSION, "rules": list(rules.values())}}, "results": results}]
    }
    with open(path, 'w') as f:
        json.dump(sarif, f, indent=2)

def send_slack(stats: ScanStats, webhook_url: str) -> bool:
    """Send slack."""
    risk_color = "#ef4444" if stats.risk_score >= 70 else "#f97316" if stats.risk_score >= 40 else "#22c55e"
    live = len(stats.live_credentials)
    payload = json.dumps({
        "attachments": [{
            "color": risk_color,
            "title": f"🛡️ Sentinel Scan Complete — Risk Score {stats.risk_score}/100",
            "fields": [
                {"title": "Directory", "value": stats.directory, "short": True},
                {"title": "Files Scanned", "value": str(stats.files_scanned), "short": True},
                {"title": "🔴 Critical", "value": str(len(stats.critical)), "short": True},
                {"title": "🟠 High", "value": str(len(stats.high)), "short": True},
                {"title": "🟡 Medium", "value": str(len(stats.medium)), "short": True},
                {"title": "Live Credentials", "value": f"⚡ {live} LIVE" if live else "0", "short": True},
                {"title": "Duration", "value": f"{stats.duration_seconds}s", "short": True},
            ],
            "footer": f"Sentinel v{VERSION}",
            "ts": int(time.time()),
        }]
    }).encode()
    try:
        req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False

# ─── HTML Report Generator ────────────────────────────────────────────────────

def generate_html_report(stats: ScanStats, output_path: str):
    """Generate html report."""
    _e = html_mod.escape
    findings_js = json.dumps([f.to_dict() for f in stats.findings], indent=2, default=str)
    history_js = json.dumps(load_history(), indent=2)
    severity_counts = {s: len([f for f in stats.findings if f.severity == s]) for s in SEVERITY_ORDER}
    categories = {}
    for f in stats.findings:
        categories[f.category] = categories.get(f.category, 0) + 1
    live_count = len(stats.live_credentials)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel Pro — Security Audit Report</title>
<style>
  :root {{
    --bg: #0a0e1a; --bg2: #0f1629; --bg3: #151d35;
    --border: #1e2d4e; --border2: #2a3d5e;
    --text: #e2e8f0; --text2: #94a3b8; --text3: #64748b;
    --red: #ef4444; --orange: #f97316; --yellow: #eab308;
    --green: #22c55e; --blue: #3b82f6; --purple: #a855f7;
    --accent: #00d4ff; --accent2: #0099bb;
    --font: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
    --font-body: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--font-body); }}
  
  .header {{ background: var(--bg2); border-bottom: 1px solid var(--border2);
    padding: 24px 40px; display: flex; align-items: center; justify-content: space-between; }}
  .header-logo {{ display: flex; align-items: center; gap: 12px; }}
  .logo-icon {{ width: 40px; height: 40px; background: linear-gradient(135deg, var(--accent), var(--blue));
    border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px; }}
  .logo-text {{ font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
  .logo-version {{ font-size: 11px; color: var(--text3); font-family: var(--font); margin-top: 2px; }}
  .header-meta {{ text-align: right; font-size: 12px; color: var(--text2); font-family: var(--font); }}
  
  .risk-banner {{ background: var(--bg3); border-bottom: 1px solid var(--border);
    padding: 20px 40px; display: flex; align-items: center; gap: 32px; }}
  .risk-gauge {{ display: flex; align-items: center; gap: 16px; }}
  .risk-circle {{ width: 80px; height: 80px; border-radius: 50%; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    background: conic-gradient(var(--risk-color, var(--red)) 0% var(--risk-pct, 75%), var(--bg) var(--risk-pct, 75%));
    box-shadow: 0 0 20px var(--risk-color, var(--red))40; }}
  .risk-inner {{ width: 64px; height: 64px; border-radius: 50%; background: var(--bg2);
    display: flex; flex-direction: column; align-items: center; justify-content: center; }}
  .risk-number {{ font-size: 22px; font-weight: 800; font-family: var(--font); }}
  .risk-label {{ font-size: 9px; color: var(--text3); text-transform: uppercase; letter-spacing: 1px; }}
  .risk-info {{ flex: 1; }}
  .risk-title {{ font-size: 18px; font-weight: 700; margin-bottom: 4px; }}
  .risk-subtitle {{ font-size: 13px; color: var(--text2); }}
  
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1px; background: var(--border); border-top: 1px solid var(--border); }}
  .stat-card {{ background: var(--bg2); padding: 20px 24px; text-align: center; }}
  .stat-number {{ font-size: 32px; font-weight: 800; font-family: var(--font); line-height: 1; }}
  .stat-label {{ font-size: 11px; color: var(--text3); text-transform: uppercase; letter-spacing: 1px; margin-top: 6px; }}
  .stat-critical .stat-number {{ color: var(--red); }}
  .stat-high .stat-number {{ color: var(--orange); }}
  .stat-medium .stat-number {{ color: var(--yellow); }}
  .stat-low .stat-number {{ color: var(--green); }}
  .stat-live .stat-number {{ color: var(--accent); animation: pulse 2s infinite; }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
  
  .main {{ display: grid; grid-template-columns: 280px 1fr; min-height: calc(100vh - 200px); }}
  .sidebar {{ background: var(--bg2); border-right: 1px solid var(--border); padding: 24px 0; }}
  .sidebar-section {{ padding: 0 20px 20px; }}
  .sidebar-title {{ font-size: 10px; text-transform: uppercase; letter-spacing: 2px; color: var(--text3);
    margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}
  .filter-btn {{ display: block; width: 100%; text-align: left; padding: 8px 12px; border-radius: 6px;
    border: none; background: transparent; color: var(--text2); cursor: pointer; font-size: 13px;
    margin-bottom: 2px; transition: all 0.15s; }}
  .filter-btn:hover {{ background: var(--bg3); color: var(--text); }}
  .filter-btn.active {{ background: var(--border2); color: var(--text); }}
  .filter-count {{ float: right; background: var(--bg3); border-radius: 10px; padding: 1px 7px;
    font-size: 11px; font-family: var(--font); }}
  .sev-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }}

  .content {{ padding: 24px 32px; overflow-x: auto; }}
  .findings-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }}
  .findings-count {{ font-size: 14px; color: var(--text2); }}
  .search-box {{ background: var(--bg2); border: 1px solid var(--border2); border-radius: 8px;
    padding: 8px 14px; color: var(--text); font-size: 13px; width: 260px; outline: none; font-family: var(--font); }}
  .search-box:focus {{ border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent)20; }}
  
  .finding-card {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 8px;
    margin-bottom: 10px; overflow: hidden; transition: border-color 0.15s; }}
  .finding-card:hover {{ border-color: var(--border2); }}
  .finding-card.severity-CRITICAL {{ border-left: 3px solid var(--red); }}
  .finding-card.severity-HIGH {{ border-left: 3px solid var(--orange); }}
  .finding-card.severity-MEDIUM {{ border-left: 3px solid var(--yellow); }}
  .finding-card.severity-LOW {{ border-left: 3px solid var(--green); }}
  .finding-header {{ padding: 14px 16px; cursor: pointer; display: flex; align-items: center; gap: 12px; }}
  .finding-header:hover {{ background: var(--bg3); }}
  .finding-badge {{ padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.5px; font-family: var(--font); }}
  .badge-CRITICAL {{ background: var(--red)20; color: var(--red); }}
  .badge-HIGH {{ background: var(--orange)20; color: var(--orange); }}
  .badge-MEDIUM {{ background: var(--yellow)20; color: var(--yellow); }}
  .badge-LOW {{ background: var(--green)20; color: var(--green); }}
  .live-badge {{ background: var(--accent)20; color: var(--accent); animation: pulse 2s infinite;
    padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; font-family: var(--font); }}
  .finding-pattern {{ font-weight: 600; font-size: 14px; flex: 1; }}
  .finding-file {{ font-family: var(--font); font-size: 12px; color: var(--text3); }}
  .finding-chevron {{ color: var(--text3); font-size: 12px; transition: transform 0.2s; }}
  .finding-body {{ padding: 0 16px 16px; display: none; }}
  .finding-body.open {{ display: block; }}
  .finding-detail {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }}
  .detail-block {{ background: var(--bg3); border-radius: 6px; padding: 12px; }}
  .detail-label {{ font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: var(--text3); margin-bottom: 6px; }}
  .detail-value {{ font-size: 13px; font-family: var(--font); color: var(--text2); word-break: break-all; }}
  .remediation-block {{ background: var(--bg3); border-radius: 6px; padding: 12px; margin-top: 12px;
    border-left: 3px solid var(--blue); }}
  .compliance-tags {{ display: flex; gap: 6px; flex-wrap: wrap; }}
  .compliance-tag {{ padding: 2px 8px; background: var(--blue)20; color: var(--blue); border-radius: 4px;
    font-size: 11px; font-family: var(--font); }}
  .code-preview {{ font-family: var(--font); font-size: 12px; background: var(--bg); padding: 10px 12px;
    border-radius: 6px; margin-top: 10px; border: 1px solid var(--border); color: var(--text2);
    white-space: pre-wrap; word-break: break-all; }}
  .blast-block {{ background: var(--red)10; border: 1px solid var(--red)30; border-radius: 6px;
    padding: 12px; margin-top: 12px; }}
  .blast-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--red);
    margin-bottom: 6px; }}

  .empty-state {{ text-align: center; padding: 80px 40px; color: var(--text3); }}
  .empty-icon {{ font-size: 48px; margin-bottom: 16px; }}
  
  .export-bar {{ background: var(--bg2); border-top: 1px solid var(--border); padding: 16px 40px;
    display: flex; gap: 12px; align-items: center; }}
  .btn {{ padding: 8px 16px; border-radius: 6px; border: 1px solid var(--border2); background: var(--bg3);
    color: var(--text); cursor: pointer; font-size: 13px; transition: all 0.15s; }}
  .btn:hover {{ background: var(--border2); }}
  .btn-primary {{ background: var(--accent)20; border-color: var(--accent)60; color: var(--accent); }}
  .btn-primary:hover {{ background: var(--accent)30; }}
  
  @media print {{
    .sidebar, .export-bar, .search-box, .filter-btn {{ display: none; }}
    .main {{ grid-template-columns: 1fr; }}
    .finding-body {{ display: block !important; }}
  }}
</style>
</head>
<body>

<div class="header">
  <div class="header-logo">
    <div class="logo-icon">🛡️</div>
    <div>
      <div class="logo-text">Sentinel Pro</div>
      <div class="logo-version">Enterprise Security Scanner v{VERSION}</div>
    </div>
  </div>
  <div class="header-meta">
    <div>Scan Target: <strong>{_e(stats.directory)}</strong></div>
    <div>{stats.scan_time}</div>
    <div>{stats.files_scanned:,} files · {stats.duration_seconds}s · {stats.total_bytes_scanned/1024/1024:.1f} MB</div>
  </div>
</div>

<div class="stats-grid">
  <div class="stat-card stat-critical"><div class="stat-number">{severity_counts.get('CRITICAL', 0)}</div><div class="stat-label">🔴 Critical</div></div>
  <div class="stat-card stat-high"><div class="stat-number">{severity_counts.get('HIGH', 0)}</div><div class="stat-label">🟠 High</div></div>
  <div class="stat-card stat-medium"><div class="stat-number">{severity_counts.get('MEDIUM', 0)}</div><div class="stat-label">🟡 Medium</div></div>
  <div class="stat-card stat-low"><div class="stat-number">{severity_counts.get('LOW', 0)}</div><div class="stat-label">🟢 Low</div></div>
  <div class="stat-card stat-live"><div class="stat-number">{live_count}</div><div class="stat-label">⚡ Live Creds</div></div>
  <div class="stat-card"><div class="stat-number" style="color:var(--accent)">{stats.risk_score}</div><div class="stat-label">Risk Score /100</div></div>
  <div class="stat-card"><div class="stat-number" style="color:var(--text2)">{stats.unique_files}</div><div class="stat-label">Affected Files</div></div>
  <div class="stat-card"><div class="stat-number" style="color:var(--text2)">{stats.files_scanned:,}</div><div class="stat-label">Files Scanned</div></div>
</div>

<div class="main">
  <div class="sidebar">
    <div class="sidebar-section">
      <div class="sidebar-title">Filter by Severity</div>
      <button class="filter-btn active" onclick="filterSeverity('ALL', this)">All Findings <span class="filter-count">{len(stats.findings)}</span></button>
      {"".join(f'<button class="filter-btn" onclick="filterSeverity(\\"{s}\\", this)" style="color: var(--{["red","orange","yellow","green","blue"][i]})"><span class="sev-dot" style="background:var(--{["red","orange","yellow","green","blue"][i]})"></span>{s} <span class="filter-count">{severity_counts.get(s,0)}</span></button>' for i,s in enumerate(["CRITICAL","HIGH","MEDIUM","LOW","INFO"]))}
    </div>
    <div class="sidebar-section">
      <div class="sidebar-title">Filter by Category</div>
      {"".join(f'<button class="filter-btn" onclick="filterCategory(\\"{cat}\\", this)">{CATEGORY_EMOJI.get(cat,"📌")} {cat} <span class="filter-count">{count}</span></button>' for cat, count in sorted(categories.items(), key=lambda x: -x[1]))}
    </div>
    {"".join([f'<div class="sidebar-section"><div class="sidebar-title">Compliance Scope</div>{"".join(f"""<button class="filter-btn" onclick="filterCompliance(\\"{fw}\\")">{fw}</button>""" for fw in ["GDPR","HIPAA","PCI_DSS","SOC2"])}</div>']) if stats.findings else ""}
  </div>
  
  <div class="content">
    <div class="findings-header">
      <div class="findings-count" id="findings-count">{len(stats.findings)} findings</div>
      <input class="search-box" type="text" placeholder="Search findings..." oninput="searchFindings(this.value)" />
    </div>
    
    <div id="findings-container">
"""
    if not stats.findings:
        html += '<div class="empty-state"><div class="empty-icon">✅</div><h3>No Findings</h3><p>Scan complete. No security issues detected.</p></div>'
    else:
        for i, f in enumerate(stats.findings):
            live_html = '<span class="live-badge">⚡ LIVE</span>' if f.verified is True else ''
            blast_html = f'<div class="blast-block"><div class="blast-title">⚡ Blast Radius</div><div style="font-size:13px;color:var(--text)">{_e(f.blast_radius or "")}</div></div>' if f.blast_radius else ''
            identity_html = f'<div class="detail-block"><div class="detail-label">Verified Identity</div><div class="detail-value" style="color:var(--accent)">{_e(f.identity or "")}</div></div>' if f.identity else ''
            html += f"""
      <div class="finding-card severity-{_e(f.severity)}" data-severity="{_e(f.severity)}" data-category="{_e(f.category)}" 
           data-compliance="{','.join(_e(c) for c in f.compliance)}" data-text="{_e(f.pattern_name)} {_e(f.file_path)}">
        <div class="finding-header" onclick="toggleBody({i})">
          <span class="finding-badge badge-{_e(f.severity)}">{_e(f.severity)}</span>
          {live_html}
          <span class="finding-pattern">{_e(f.pattern_name)}</span>
          <span class="finding-file">...{_e(f.file_path[-50:])}:{f.line_number}</span>
          <span class="finding-chevron" id="chevron-{i}">▼</span>
        </div>
        <div class="finding-body" id="body-{i}">
          <div class="finding-detail">
            <div class="detail-block"><div class="detail-label">Match Preview</div><div class="detail-value">{_e(f.match_preview)}</div></div>
            <div class="detail-block"><div class="detail-label">Category</div><div class="detail-value">{CATEGORY_EMOJI.get(f.category,'')} {_e(f.category)}</div></div>
            <div class="detail-block"><div class="detail-label">File Path</div><div class="detail-value">{_e(f.file_path)}</div></div>
            <div class="detail-block"><div class="detail-label">Entropy / Confidence</div><div class="detail-value">{f.entropy:.2f} / {f.confidence:.0%}</div></div>
            {identity_html}
            <div class="detail-block"><div class="detail-label">Compliance</div><div class="compliance-tags">{"".join(f'<span class="compliance-tag">{_e(c)}</span>' for c in f.compliance)}</div></div>
          </div>
          <div class="code-preview">{_e(f.line_preview or "(no preview)")}</div>
          <div class="remediation-block"><div class="detail-label">📋 Remediation Steps</div><div style="font-size:13px;white-space:pre-wrap;margin-top:6px">{_e(f.remediation)}</div></div>
          {blast_html}
        </div>
      </div>"""

    html += f"""
    </div>
  </div>
</div>

<div class="export-bar">
  <strong style="font-size:13px;color:var(--text2)">Export:</strong>
  <button class="btn btn-primary" onclick="downloadJSON()">📦 JSON</button>
  <button class="btn" onclick="downloadCSV()">📊 CSV</button>
  <button class="btn" onclick="window.print()">🖨️ Print / PDF</button>
  <span style="flex:1"></span>
  <span style="font-size:12px;color:var(--text3)">Generated by Sentinel Pro v{VERSION} — sentinel.security</span>
</div>

<script>
const FINDINGS = {findings_js};
const HISTORY  = {history_js};

function toggleBody(i) {{
  const body = document.getElementById('body-'+i);
  const chev = document.getElementById('chevron-'+i);
  const open = body.classList.toggle('open');
  chev.textContent = open ? '▲' : '▼';
}}

let activeSev = 'ALL', activeCat = '', activeComp = '', searchTerm = '';

function updateVisible() {{
  let visible = 0;
  document.querySelectorAll('.finding-card').forEach(card => {{
    const sev  = card.dataset.severity;
    const cat  = card.dataset.category;
    const comp = card.dataset.compliance;
    const text = card.dataset.text.toLowerCase();
    const show = (activeSev === 'ALL' || sev === activeSev) &&
                 (!activeCat  || cat === activeCat) &&
                 (!activeComp || comp.includes(activeComp)) &&
                 (!searchTerm || text.includes(searchTerm));
    card.style.display = show ? 'block' : 'none';
    if (show) visible++;
  }});
  document.getElementById('findings-count').textContent = visible + ' findings';
}}

function filterSeverity(sev, btn) {{
  activeSev = sev;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  updateVisible();
}}
function filterCategory(cat) {{ activeCat = activeCat === cat ? '' : cat; updateVisible(); }}
function filterCompliance(comp) {{ activeComp = activeComp === comp ? '' : comp; updateVisible(); }}
function searchFindings(q) {{ searchTerm = q.toLowerCase(); updateVisible(); }}

function downloadJSON() {{
  const blob = new Blob([JSON.stringify(FINDINGS, null, 2)], {{type: 'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'sentinel-findings.json';
  a.click();
}}
function downloadCSV() {{
  const rows = [['severity','pattern','file','line','match','compliance','confidence']];
  FINDINGS.forEach(f => rows.push([f.severity, f.pattern_name, f.file_path, f.line_number,
    f.match_preview, (f.compliance||[]).join('|'), f.confidence]));
  const csv = rows.map(r => r.map(c => '"'+String(c).replace(/"/g,'""')+'"').join(',')).join('\\n');
  const blob = new Blob([csv], {{type: 'text/csv'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'sentinel-findings.csv';
  a.click();
}}
</script>
</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

# ─── Terminal Report ──────────────────────────────────────────────────────────

def print_terminal_report(stats: ScanStats):
    """Print terminal report."""
    if RICH_AVAILABLE:
        console = Console()
        console.print()
        console.rule(f"[bold cyan]🛡️  Sentinel Pro v{VERSION} — Scan Report[/bold cyan]")
        console.print()

        # Summary panel
        risk_color = "red" if stats.risk_score >= 70 else "orange1" if stats.risk_score >= 40 else "green"
        live = len(stats.live_credentials)
        summary = (
            f"[bold]Directory:[/bold] {stats.directory}\n"
            f"[bold]Files:[/bold] {stats.files_scanned:,} scanned, {stats.files_skipped} skipped\n"
            f"[bold]Duration:[/bold] {stats.duration_seconds}s  "
            f"[bold]Speed:[/bold] {stats.total_bytes_scanned/1024/1024/max(stats.duration_seconds,0.01):.1f} MB/s\n"
            f"[bold]Risk Score:[/bold] [{risk_color}]{stats.risk_score}/100[/{risk_color}]"
            + (f"  [bold cyan]⚡ {live} LIVE credential(s) confirmed[/bold cyan]" if live else "")
        )
        console.print(Panel(summary, title="[bold]Scan Summary[/bold]", border_style="blue"))

        if not stats.findings:
            console.print("\n[bold green]✅ No findings. Clean scan.[/bold green]\n")
            return

        # Findings table
        table = Table(box=box.SIMPLE_HEAD, show_lines=False, expand=True)
        table.add_column("SEV", width=10)
        table.add_column("CATEGORY", width=12)
        table.add_column("PATTERN", width=35)
        table.add_column("FILE:LINE", width=40)
        table.add_column("MATCH", width=20)
        table.add_column("CONF", width=6)

        SEV_STYLE = {"CRITICAL": "bold red", "HIGH": "orange1", "MEDIUM": "yellow", "LOW": "green", "INFO": "blue"}
        for f in stats.findings[:100]:
            sev_style = SEV_STYLE.get(f.severity, "white")
            live_tag = " [cyan]⚡LIVE[/cyan]" if f.verified is True else ""
            table.add_row(
                Text(f.severity, style=sev_style),
                f"{CATEGORY_EMOJI.get(f.category,'')} {f.category}",
                f.pattern_name[:35] + live_tag,
                f"...{f.file_path[-35:]}:{f.line_number}",
                f.match_preview[:20],
                f"{int(f.confidence*100)}%",
            )

        if len(stats.findings) > 100:
            console.print(f"\n[dim]Showing 100 of {len(stats.findings)} findings. Use --report for full HTML report.[/dim]")

        console.print(table)
        console.print()
        console.print(f"  🔴 CRITICAL: {len(stats.critical)}  🟠 HIGH: {len(stats.high)}  🟡 MEDIUM: {len(stats.medium)}  🟢 LOW: {len(stats.low)}")
        if stats.suppressed_count:
            console.print(f"  [dim]({stats.suppressed_count} findings suppressed as false positives)[/dim]")
        if stats.is_delta:
            console.print(f"  [cyan](Delta mode: showing {len(stats.findings)} NEW findings, {stats.delta_resolved} resolved)[/cyan]")
        console.print()
    else:
        # Plain terminal output
        print(f"\n{'='*70}")
        print(f" SENTINEL PRO v{VERSION} — {stats.directory}")
        print(f" Risk Score: {stats.risk_score}/100 | Files: {stats.files_scanned:,} | Time: {stats.duration_seconds}s")
        print(f"{'='*70}\n")
        if not stats.findings:
            print(" ✅ No findings.\n")
            return
        for f in stats.findings:
            live = " [LIVE]" if f.verified is True else ""
            print(f" [{f.severity}]{live} {f.pattern_name}")
            print(f"   {f.file_path}:{f.line_number} — {f.match_preview}")
        print(f"\n CRITICAL:{len(stats.critical)} HIGH:{len(stats.high)} MEDIUM:{len(stats.medium)} LOW:{len(stats.low)}\n")

# ─── Web Dashboard ─────────────────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><title>Sentinel Pro Dashboard</title>
<style>
  :root { --bg:#0a0e1a; --bg2:#0f1629; --bg3:#151d35; --border:#1e2d4e;
    --text:#e2e8f0; --text2:#94a3b8; --accent:#00d4ff; }
  body { background:var(--bg); color:var(--text); font-family:-apple-system,sans-serif; margin:0; }
  .header { background:var(--bg2); border-bottom:1px solid var(--border); padding:16px 32px;
    display:flex; align-items:center; justify-content:space-between; }
  h1 { font-size:20px; display:flex; align-items:center; gap:10px; }
  .scan-btn { background:var(--accent)20; border:1px solid var(--accent)60; color:var(--accent);
    padding:8px 20px; border-radius:6px; cursor:pointer; font-size:14px; }
  .scan-btn:hover { background:var(--accent)40; }
  .grid { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; padding:24px 32px; }
  .card { background:var(--bg2); border:1px solid var(--border); border-radius:10px; padding:20px; }
  .card-num { font-size:36px; font-weight:800; font-family:monospace; }
  .card-label { font-size:11px; text-transform:uppercase; letter-spacing:1px; color:var(--text2); margin-top:4px; }
  .history { padding:0 32px 32px; }
  .history h2 { margin-bottom:16px; font-size:16px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; padding:8px 12px; background:var(--bg2); color:var(--text2);
    font-size:11px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid var(--border); }
  td { padding:10px 12px; border-bottom:1px solid var(--border); }
  tr:hover td { background:var(--bg2); }
  .badge { padding:2px 8px; border-radius:4px; font-size:11px; font-family:monospace; }
  .risk-hi { background:#ef444420; color:#ef4444; }
  .risk-mid { background:#f9731620; color:#f97316; }
  .risk-lo { background:#22c55e20; color:#22c55e; }
  .live-tag { color:#00d4ff; font-weight:700; }
  #status { padding:4px 16px; font-size:12px; color:var(--text2); }
</style>
</head>
<body>
<div class="header">
  <h1>🛡️ Sentinel Pro <span style="font-size:13px;color:var(--text2);font-weight:400">Dashboard</span></h1>
  <div style="display:flex;align-items:center;gap:12px">
    <span id="status">Loading history...</span>
    <button class="scan-btn" onclick="triggerScan()">▶ New Scan</button>
  </div>
</div>
<div class="grid" id="summary-grid">
  <div class="card"><div class="card-num" id="total-scans">—</div><div class="card-label">Total Scans</div></div>
  <div class="card"><div class="card-num" style="color:#ef4444" id="avg-risk">—</div><div class="card-label">Avg Risk Score</div></div>
  <div class="card"><div class="card-num" style="color:#00d4ff" id="total-live">—</div><div class="card-label">Live Creds Found</div></div>
  <div class="card"><div class="card-num" style="color:#94a3b8" id="total-findings">—</div><div class="card-label">Total Findings</div></div>
</div>
<div class="history">
  <h2>📋 Scan History</h2>
  <table>
    <thead><tr><th>Date</th><th>Directory</th><th>Risk</th><th>Critical</th><th>High</th><th>Live Creds</th><th>Files</th><th>Duration</th></tr></thead>
    <tbody id="history-tbody"><tr><td colspan="8" style="text-align:center;color:#475569">Loading...</td></tr></tbody>
  </table>
</div>
<script>
fetch('/api/history').then(r=>r.json()).then(data => {
  document.getElementById('status').textContent = data.length + ' scans recorded';
  const total = data.length;
  const avgRisk = total ? Math.round(data.reduce((s,d)=>s+d.risk_score,0)/total) : 0;
  const totalLive = data.reduce((s,d)=>s+(d.live_credentials||0),0);
  const totalF = data.reduce((s,d)=>s+(d.counts?.critical||0)+(d.counts?.high||0),0);
  document.getElementById('total-scans').textContent = total;
  document.getElementById('avg-risk').textContent = avgRisk;
  document.getElementById('total-live').textContent = totalLive;
  document.getElementById('total-findings').textContent = totalF + '+';
  const tbody = document.getElementById('history-tbody');
  if (!data.length) { tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#475569">No scans yet. Run: sentinel_pro.py scan /path/to/scan</td></tr>'; return; }
  tbody.innerHTML = data.map(d => {
    const riskClass = d.risk_score>=70?'risk-hi':d.risk_score>=40?'risk-mid':'risk-lo';
    const live = (d.live_credentials||0) > 0 ? `<span class="live-tag">⚡ ${d.live_credentials}</span>` : '0';
    return `<tr>
      <td>${(d.scan_time||'').slice(0,19).replace('T',' ')}</td>
      <td style="font-family:monospace;font-size:12px">${d.directory}</td>
      <td><span class="badge ${riskClass}">${d.risk_score}/100</span></td>
      <td style="color:#ef4444">${d.counts?.critical||0}</td>
      <td style="color:#f97316">${d.counts?.high||0}</td>
      <td>${live}</td>
      <td>${(d.files_scanned||0).toLocaleString()}</td>
      <td>${d.duration||0}s</td>
    </tr>`;
  }).join('');
}).catch(e => {
  document.getElementById('status').textContent = 'Error loading history';
  document.getElementById('history-tbody').innerHTML = '<tr><td colspan="8" style="text-align:center;color:#ef4444">Dashboard error: ' + e.message + '</td></tr>';
});
function triggerScan() {
  const dir = prompt('Directory to scan:', '/srv/app');
  if (dir) { alert('Run: python sentinel_pro.py scan ' + dir + ' --report report.html'); }
}
</script>
</body>
</html>"""

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    """Dashboard Handler."""
    def log_message(self, format, *args):
        """Log message."""
        pass  # suppress logs
    def do_GET(self):
        """Do GET."""
        if self.path == '/api/history':
            data = json.dumps(load_history()).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        else:
            html = DASHBOARD_HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html)

def serve_dashboard(port: int = 8080):
    """Serve dashboard."""
    print(f"\n🌐 Sentinel Dashboard running at http://localhost:{port}")
    print(f"   Press Ctrl+C to stop.\n")
    server = http.server.HTTPServer(('127.0.0.1', port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⛔ Dashboard stopped.")

# ─── CLI ─────────────────────────────────────────────────────────────────────

def cmd_scan(args):
    """Cmd scan."""
    directory = os.path.abspath(args.directory)
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a directory.", file=sys.stderr)
        return 3

    severity_filter = [s.strip().upper() for s in args.severity.split(",")] if getattr(args,"severity",None) else None

    # Run core scan
    stats = run_scan(directory=directory, ignores=getattr(args,"ignore",[]), max_workers=getattr(args,"workers",8),
                     severity_filter=severity_filter, quiet=getattr(args,"quiet",False))

    # Archive scan
    if getattr(args, "archives", False):
        arc_findings, arc_count = scan_archives(directory, quiet=getattr(args,"quiet",False))
        stats.findings.extend(arc_findings)
        stats.archives_scanned = arc_count
        stats.findings.sort(key=lambda f: (-f.severity_rank, f.file_path))

    # Git history scan
    if getattr(args, "git_history", False):
        git_findings, git_commits = scan_git_history(directory, quiet=getattr(args,"quiet",False))
        stats.findings.extend(git_findings)
        stats.git_commits_scanned = git_commits

    # False positive filter
    stats.findings, stats.suppressed_count = apply_fp_filter(stats.findings, directory)

    # Compliance filter
    if getattr(args,"compliance",None):
        cf = [c.strip().upper() for c in args.compliance.split(",")]
        stats.findings = [f for f in stats.findings if any(c in cf for c in f.compliance)]

    # Baseline / delta
    if getattr(args,"diff",False):
        baseline = load_baseline(directory)
        if baseline is None:
            print("⚠️  No baseline found. Run: sentinel_pro.py baseline save " + directory, file=sys.stderr)
        else:
            new_findings, resolved = compute_delta(stats.findings, baseline)
            stats.findings = new_findings
            stats.is_delta = True
            stats.delta_resolved = resolved
            if not getattr(args,"quiet",False):
                print(f"📊 Delta mode: {len(new_findings)} NEW findings, {resolved} resolved since baseline", file=sys.stderr)

    # Recompute risk
    stats.risk_score = compute_risk_score(stats.findings)

    # Live verification
    verification_results = {}
    if getattr(args,"verify",False):
        verification_results = verify_all_findings(stats.findings, quiet=getattr(args,"quiet",False))
        for f in stats.findings:
            vr = verification_results.get(f.fingerprint)
            if vr:
                f.verified = vr.is_live
                f.identity = vr.identity
                f.blast_radius = vr.blast_radius
        stats.risk_score = compute_risk_score(stats.findings)

    # Save to history
    save_to_history(stats, live_count=sum(1 for r in verification_results.values() if r.is_live is True))

    # Terminal output
    if not getattr(args,"no_terminal",False):
        print_terminal_report(stats)

    # Outputs
    if getattr(args,"report",None):
        generate_html_report(stats, args.report)
        if not getattr(args,"quiet",False):
            print(f"📄 HTML report → {args.report}", file=sys.stderr)

    if getattr(args,"json_out",None):
        export_json(stats, args.json_out)
        if not getattr(args,"quiet",False):
            print(f"📦 JSON → {args.json_out}", file=sys.stderr)

    if getattr(args,"csv_out",None):
        export_csv(stats, args.csv_out)
        if not getattr(args,"quiet",False):
            print(f"📊 CSV → {args.csv_out}", file=sys.stderr)

    if getattr(args,"sarif",None):
        export_sarif(stats, args.sarif)
        if not getattr(args,"quiet",False):
            print(f"🔗 SARIF → {args.sarif}", file=sys.stderr)

    if getattr(args,"slack_webhook",None):
        ok = send_slack(stats, args.slack_webhook)
        print("✅ Slack notified" if ok else "❌ Slack failed", file=sys.stderr)

    # Jira integration
    if getattr(args,"jira_url",None) and getattr(args,"jira_project",None):
        jira_user  = os.environ.get("JIRA_USER","")
        jira_token = os.environ.get("JIRA_TOKEN","")
        if not jira_user or not jira_token:
            print("⚠️  Set JIRA_USER and JIRA_TOKEN env vars for Jira integration.", file=sys.stderr)
        else:
            critical_high = [f for f in stats.findings if f.severity in ("CRITICAL","HIGH")]
            created = 0
            for finding in critical_high[:20]:  # cap at 20 auto-tickets
                key = create_jira_ticket(finding, args.jira_url, jira_user, jira_token, args.jira_project)
                if key:
                    created += 1
            print(f"🎟️  Created {created} Jira tickets in project {args.jira_project}", file=sys.stderr)

    # GitHub Issues integration
    if getattr(args,"github_repo",None):
        gh_token = os.environ.get("GITHUB_TOKEN","")
        if not gh_token:
            print("⚠️  Set GITHUB_TOKEN env var for GitHub Issues integration.", file=sys.stderr)
        else:
            critical_high = [f for f in stats.findings if f.severity in ("CRITICAL","HIGH")]
            created = 0
            for finding in critical_high[:10]:
                url = create_github_issue(finding, gh_token, args.github_repo)
                if url:
                    created += 1
            print(f"🐛 Created {created} GitHub Issues in {args.github_repo}", file=sys.stderr)

    # CI/CD exit code
    if getattr(args,"ci",False):
        fail_rank = SEVERITY_ORDER.get(getattr(args,"fail_on","HIGH").upper(), 3)
        blocking = [f for f in stats.findings if f.severity_rank >= fail_rank]
        if blocking:
            return 2
        if stats.findings:
            return 1
        return 0
    return 0


def cmd_baseline(args):
    """Cmd baseline."""
    directory = os.path.abspath(args.directory)
    if args.baseline_action == "save":
        stats = run_scan(directory=directory, quiet=True)
        path = save_baseline(stats.findings, directory)
        print(f"✅ Baseline saved: {path} ({len(stats.findings)} findings fingerprinted)")
    elif args.baseline_action == "diff":
        stats = run_scan(directory=directory, quiet=True)
        baseline = load_baseline(directory)
        if not baseline:
            print(f"⚠️  No baseline at {directory}/{BASELINE_FILENAME}")
            return 1
        new_findings, resolved = compute_delta(stats.findings, baseline)
        print(f"\n📊 Delta since {baseline['created_at'][:10]}:")
        print(f"  {len(new_findings)} NEW findings | {resolved} resolved\n")
        for f in new_findings[:20]:
            print(f"  + [{f.severity}] {f.pattern_name} — {f.file_path}:{f.line_number}")
    elif args.baseline_action == "clear":
        path = os.path.join(directory, BASELINE_FILENAME)
        if os.path.exists(path):
            os.remove(path)
            print(f"✅ Baseline cleared: {path}")
        else:
            print("No baseline found.")
    return 0


def cmd_fp(args):
    """Cmd fp."""
    if args.fp_action == "add":
        add_fp(args.fingerprint, os.getcwd(), getattr(args,"reason",""))
    elif args.fp_action == "list":
        db = load_fp_db(os.getcwd())
        sups = db.get("suppressions", {})
        if not sups:
            print("No suppressions.")
        for fp_id, data in sups.items():
            print(f"  {fp_id} — {data.get('reason','no reason')} (added {data.get('suppressed_at','?')[:10]})")
    elif args.fp_action == "remove":
        db = load_fp_db(os.getcwd())
        if args.fingerprint in db.get("suppressions", {}):
            del db["suppressions"][args.fingerprint]
            save_fp_db(db, os.getcwd())
            print(f"✅ Removed suppression: {args.fingerprint}")
        else:
            print(f"Not found: {args.fingerprint}")
    return 0


def cmd_verify(args):
    """Cmd verify."""
    with open(args.file) as f:
        data = json.load(f)
    findings_raw = data.get("findings", data) if isinstance(data, dict) else data
    from dataclasses import fields as dc_fields
    finding_fields = {f.name for f in dc_fields(Finding)}
    findings = []
    for raw in findings_raw:
        try:
            findings.append(Finding(**{k: v for k, v in raw.items() if k in finding_fields}))
        except Exception:
            pass
    print(f"\n📂 Loaded {len(findings)} findings from {args.file}")
    results = verify_all_findings(findings, quiet=False)
    live = [r for r in results.values() if r.is_live is True]
    print(f"\n✅ Verification complete: {len(live)} LIVE credentials out of {len(results)} checked")
    return 0


def cmd_serve(args):
    """Cmd serve."""
    serve_dashboard(getattr(args,"port",8080))
    return 0


def cmd_patterns(args):
    """Cmd patterns."""
    if RICH_AVAILABLE:
        console = Console()
        table = Table(title=f"Sentinel Pro — {len(PATTERNS)} Detection Patterns", box=box.SIMPLE)
        table.add_column("Pattern Name", style="bold")
        table.add_column("Severity")
        table.add_column("Category")
        table.add_column("Compliance")
        SEV_STYLE = {"CRITICAL":"red","HIGH":"orange1","MEDIUM":"yellow","LOW":"green","INFO":"blue"}
        for p in sorted(PATTERNS, key=lambda x: -SEVERITY_ORDER.get(x.severity,0)):
            table.add_row(p.name, Text(p.severity, style=SEV_STYLE.get(p.severity,"white")), p.category, ", ".join(p.compliance))
        console.print(table)
    else:
        for p in sorted(PATTERNS, key=lambda x: -SEVERITY_ORDER.get(x.severity,0)):
            print(f"[{p.severity}] {p.name} | {p.category} | {', '.join(p.compliance)}")
    return 0


def build_parser():
    """Build parser."""
    parser = argparse.ArgumentParser(
        prog="sentinel_pro",
        description=f"Sentinel Pro v{VERSION} — Enterprise Data Security Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"Sentinel Pro v{VERSION}")
    sub = parser.add_subparsers(dest="command")

    # scan
    sp = sub.add_parser("scan", help="Scan a directory for secrets and PII")
    sp.add_argument("directory", nargs="?", default=".")
    sp.add_argument("--verify", action="store_true", help="Live-verify found credentials against APIs")
    sp.add_argument("--archives", action="store_true", help="Scan inside .zip and .tar archives")
    sp.add_argument("--git-history", action="store_true", help="Scan git commit history")
    sp.add_argument("--diff", action="store_true", help="Show only NEW findings since last baseline")
    sp.add_argument("--report", metavar="FILE.html", help="Generate HTML report")
    sp.add_argument("--json", dest="json_out", metavar="FILE.json", help="JSON export")
    sp.add_argument("--csv", dest="csv_out", metavar="FILE.csv", help="CSV export")
    sp.add_argument("--sarif", metavar="FILE.sarif", help="SARIF export for GitHub/GitLab")
    sp.add_argument("--severity", metavar="LEVELS", help="Filter: CRITICAL,HIGH,MEDIUM,LOW")
    sp.add_argument("--compliance", metavar="FW", help="Filter: GDPR,HIPAA,PCI_DSS,SOC2")
    sp.add_argument("--ignore", "-i", action="append", default=[], metavar="PATTERN")
    sp.add_argument("--workers", type=int, default=min(os.cpu_count() or 4, 16))
    sp.add_argument("--slack-webhook", metavar="URL")
    sp.add_argument("--jira-url", metavar="URL", help="Jira base URL (needs JIRA_USER + JIRA_TOKEN env vars)")
    sp.add_argument("--jira-project", metavar="KEY", help="Jira project key (e.g. SEC)")
    sp.add_argument("--github-repo", metavar="OWNER/REPO", help="GitHub repo for auto-issues (needs GITHUB_TOKEN env var)")
    sp.add_argument("--ci", action="store_true", help="CI mode: exit 2 on critical/high")
    sp.add_argument("--fail-on", default="HIGH", metavar="SEV")
    sp.add_argument("--quiet", "-q", action="store_true")
    sp.add_argument("--no-terminal", action="store_true")

    # baseline
    bp = sub.add_parser("baseline", help="Manage scan baselines")
    bsub = bp.add_subparsers(dest="baseline_action")
    bsave = bsub.add_parser("save"); bsave.add_argument("directory", nargs="?", default=".")
    bdiff = bsub.add_parser("diff"); bdiff.add_argument("directory", nargs="?", default=".")
    bclear = bsub.add_parser("clear"); bclear.add_argument("directory", nargs="?", default=".")

    # fp
    fp = sub.add_parser("fp", help="Manage false positive suppressions")
    fpsub = fp.add_subparsers(dest="fp_action")
    fpadd = fpsub.add_parser("add"); fpadd.add_argument("fingerprint"); fpadd.add_argument("--reason",default="")
    fplist = fpsub.add_parser("list")
    fprem = fpsub.add_parser("remove"); fprem.add_argument("fingerprint")

    # verify
    vp = sub.add_parser("verify", help="Live-verify credentials from a JSON findings file")
    vp.add_argument("file", help="JSON file from --json export")

    # serve
    svp = sub.add_parser("serve", help="Start web dashboard")
    svp.add_argument("--port", type=int, default=8080)

    # patterns
    sub.add_parser("patterns", help="List all detection patterns")

    return parser


def main() -> int:
    """Main."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        return cmd_scan(args)
    elif args.command == "baseline":
        return cmd_baseline(args)
    elif args.command == "fp":
        return cmd_fp(args)
    elif args.command == "verify":
        return cmd_verify(args)
    elif args.command == "serve":
        return cmd_serve(args)
    elif args.command == "patterns":
        return cmd_patterns(args)
    else:
        # Backward-compat: no subcommand → scan current dir
        if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
            sys.argv.insert(1, "scan")
            args = parser.parse_args()
            return cmd_scan(args)
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
