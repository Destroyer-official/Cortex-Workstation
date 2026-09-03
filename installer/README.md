# Distribution Runbook (Windows)

This folder contains everything needed to ship Cortex Cleaner as a signed,
installable Windows application. Follow the steps **in order** — signing
before wrapping matters because installed files keep their first-seen
reputation.

## 0. Prerequisites

| Tool | Purpose |
|---|---|
| Python 3.10+ with project deps (`pip install -e .[all]`) | build |
| `pip install pyinstaller` | freeze |
| Windows SDK (signtool.exe) | signing |
| Inno Setup 6 (ISCC.exe) | installer |
| An OV or EV code-signing certificate (PFX) | signing |

## 1. Build

```powershell
pyinstaller CortexCleaner.spec --noconfirm
# -> dist\CortexCleaner\  (onedir - keep it that way, see notes)
```

**Never enable UPX.** Packed Qt plugin DLLs corrupt at load time and packed
executables are a strong AV heuristic for cleaner-type tools.

**Test the artifact on a clean VM without Python** before every release:
launch, run one scan, one leftover clean, close-to-tray, quit. Resource
loading regressions only show outside a dev environment.

## 2. Sign everything

```powershell
$env:CERT_PW = "<pfx password>"
.\installer\sign.ps1 -PfxPath C:\certs\code.pfx -PfxPasswordEnvVar CERT_PW
```

* SHA-256 digest + RFC 3161 timestamp (`/tr ... /td sha256`) so signatures
  outlive the certificate.
* Every `.exe` **and** `.dll` in `dist\CortexCleaner\` gets signed; the
  script verifies afterwards.
* SmartScreen: new publishers get warnings regardless of OV/EV for the first
  weeks of installs. This is reputation-based and unavoidable; plan messaging.
* Submit false-positive reports to major AV vendors per release if flagged;
  test each release artifact on VirusTotal **before** publishing.

## 3. Installer

```powershell
iscc installer\cortex_cleaner.iss
# -> installer_output\CortexCleaner-<version>-setup.exe   (sign this too!)
.\installer\sign.ps1 -PfxPath C:\certs\code.pfx `
    -PfxPasswordEnvVar CERT_PW -TargetDir installer_output
```

Design choices baked into `cortex_cleaner.iss`:

* **onedir** wrapping — onefile self-extractors look like malware to AV
  heuristics and slow every launch.
* **PrivilegesRequired=lowest** with dialog override — standard users can
  install per-user; the app elevates individual privileged operations itself
  instead of running fully admin.
* The output is never named `setup.exe` (DLL-injection vector via the
  compatibility loader).

## 4. Updates

The app ships an update **checker** (`cortex_unified/system_tools/
update_checker.py`) that queries this project's GitHub releases API and
surfaces newer versions non-intrusively (status bar / tray), never
downloading or replacing anything silently.

For a full silent auto-update channel, use one of:

| Option | Notes |
|---|---|
| [tufup](https://github.com/dennisvang/tufup) | The Update Framework: key rotation + threshold signing; good fit for frozen Python apps |
| WinSparkle (`EdDSA`-signed appcast) | C API, toolkit-independent, UI on its own thread |

Whatever the channel: updates MUST be served over HTTPS and
cryptographically verified before execution, and the updater must handle the
elevated-Program-Files case (relaunch elevated or split checker/updater).

## 5. Crash reports

Uncaught exceptions are logged by `app.py`'s excepthook AND written as a
redact-friendly crash report under the app's log directory
(`help → open logs`). If adopting Sentry later: scrub file paths before
upload — crash dumps from a cleaner contain user filenames.

## Release checklist

- [ ] Version bumped in `pyproject.toml` (+ `CHANGELOG.md` entry, Keep-a-Changelog)
- [ ] Clean venv build; artifact tested on a Python-less VM
- [ ] All PEs signed + verified; installer signed
- [ ] VirusTotal scan of artifacts clean (or FPs reported)
- [ ] Git tag `v<version>`; GitHub release with changelog as release notes
