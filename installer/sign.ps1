# Sign every PE artifact for release.
# ------------------------------------
# Usage:
#   .\installer\sign.ps1 -PfxPath C:\certs\my.pfx -PfxPasswordEnvVar CERT_PW
#
# Requirements:
#   * Windows SDK signtool.exe on PATH (or pass -SigTool path)
#   * An OV/EV code-signing certificate as a PFX (or Azure Trusted Signing -
#     swap the signtool invocation accordingly).
#
# Why every file, why timestamping (distribution research):
#   * A SHA-256 digest + RFC 3161 timestamp (/tr /td sha256) keeps signatures
#     valid AFTER the certificate expires.
#   * SmartScreen reputation is per-publisher and builds over weeks of clean
#     installs regardless of OV vs EV; signing everything from day one is the
#     single biggest lever.
param(
    [Parameter(Mandatory = $true)][string]$PfxPath,
    [Parameter(Mandatory = $true)][string]$PfxPasswordEnvVar,
    [string]$SigTool = "signtool",
    [string]$TargetDir = "..\dist\CortexCleaner"
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command $SigTool -ErrorAction SilentlyContinue)) {
    throw "signtool not found. Install the Windows SDK or pass -SigTool."
}
if (-not (Get-ChildItem Env: | Where-Object Name -eq $PfxPasswordEnvVar)) {
    throw "Environment variable '$PfxPasswordEnvVar' (the PFX password) is not set."
}

$files = Get-ChildItem -Path $TargetDir -Recurse -Include *.exe, *.dll |
    Sort-Object FullName
if (-not $files) { throw "No exe/dll files found under $TargetDir" }

$password = (Get-Item "Env:$PfxPasswordEnvVar").Value
$signed = 0
foreach ($f in $files) {
    & $SigTool sign /fd SHA256 `
        /f $PfxPath /p $password `
        /tr http://timestamp.digicert.com /td SHA256 `
        $f.FullName
    if ($LASTEXITCODE -ne 0) { throw "Signing failed: $($f.FullName)" }
    $signed++
}

# Verify: every file must report a valid signature with matching digest.
& $SigTool verify /pa /all `$files.FullName 2>$null
$unsigned = @()
foreach ($f in $files) {
    $ok = & $SigTool verify /pa /all $f.FullName 2>$null
    if ($LASTEXITCODE -ne 0) { $unsigned += $f.FullName }
}
if ($unsigned.Count -gt 0) {
    throw "Unsigned/invalid after signing:`n$($unsigned -join "`n")"
}
Write-Host "Signed and verified $signed files."
