param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Begin', 'Restore')]
    [string]$Action,
    [string]$UserDirectory = "$env:USERPROFILE\Documents\Paradox Interactive\Hearts of Iron IV",
    [ValidateSet('english', 'polish')]
    [string]$Language = 'english'
)

$ErrorActionPreference = 'Stop'
$manifestPath = Join-Path $UserDirectory 'rename_anything_test_session.json'
$repoDirectory = Split-Path -Parent $PSScriptRoot

if (Get-Process -Name hoi4 -ErrorAction SilentlyContinue) {
    throw 'Close HOI4 before starting or restoring a test session.'
}

if ($Action -eq 'Restore') {
    if (!(Test-Path -LiteralPath $manifestPath)) { throw 'No test-session manifest; nothing restored.' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    # Check every recovery copy before changing or deleting any of them.
    foreach ($entry in $manifest.files) {
        if (!(Test-Path -LiteralPath $entry.backup)) { throw "Missing backup: $($entry.backup)" }
        if ((Get-FileHash -LiteralPath $entry.backup -Algorithm SHA256).Hash -ne $entry.sha256) {
            throw "Backup hash mismatch: $($entry.backup)"
        }
    }
    foreach ($entry in $manifest.files) {
        Copy-Item -LiteralPath $entry.backup -Destination $entry.path -Force
        if ((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256) {
            throw "Restored hash mismatch; backups retained: $($entry.path)"
        }
        Write-Output "Restored $($entry.path) SHA256=$($entry.sha256)"
    }
    foreach ($entry in $manifest.files) { Remove-Item -LiteralPath $entry.backup }
    Remove-Item -LiteralPath $manifestPath
    exit 0
}

if (Test-Path -LiteralPath $manifestPath) { throw 'Existing test-session manifest. Restore it first.' }
$files = @()
foreach ($name in @('dlc_load.json', 'settings.txt')) {
    $path = Join-Path $UserDirectory $name
    $backup = "$path.impl_backup"
    if (Test-Path -LiteralPath $backup) { throw "Existing backup; refusing to overwrite: $backup" }
    if (!(Test-Path -LiteralPath $path)) { throw "Required user file is missing: $path" }
    $files += [pscustomobject]@{ path = $path; backup = $backup; sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
}
foreach ($entry in $files) {
    Copy-Item -LiteralPath $entry.path -Destination $entry.backup
    if ((Get-FileHash -LiteralPath $entry.backup -Algorithm SHA256).Hash -ne $entry.sha256) {
        throw "Backup hash mismatch; original files untouched: $($entry.path)"
    }
}
@{ files = $files; started = [DateTimeOffset]::Now.ToString('o') } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

try {
    $modDirectory = Join-Path $UserDirectory 'mod'
    if (!(Test-Path -LiteralPath $modDirectory)) { New-Item -ItemType Directory -Path $modDirectory | Out-Null }
    $modPath = (Join-Path $repoDirectory 'mod').Replace('\', '/')
    $descriptor = "version=`"0.1.0`"`nname=`"Rename Anything (dev)`"`nsupported_version=`"1.19.*`"`npath=`"$modPath`"`n"
    [IO.File]::WriteAllText((Join-Path $modDirectory 'rename_anything_dev.mod'), $descriptor, [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $UserDirectory 'dlc_load.json'), '{"enabled_mods":["mod/rename_anything_dev.mod"],"disabled_dlcs":[]}', [Text.UTF8Encoding]::new($false))
    $settingsPath = Join-Path $UserDirectory 'settings.txt'
    $settings = [IO.File]::ReadAllText($settingsPath)
    $settings = $settings -replace 'language="l_[^"]+"', "language=`"l_$Language`""
    $settings = $settings -replace 'size=\{ x=\d+ y=\d+ \}', 'size={ x=1720 y=900 }'
    $settings = $settings -replace 'fullScreen=yes', 'fullScreen=no'
    $settings = $settings -replace 'borderless=yes', 'borderless=no'
    [IO.File]::WriteAllText($settingsPath, $settings, [Text.UTF8Encoding]::new($false))
    Write-Output "Test session prepared ($Language, 1720x900). After closing HOI4 run: tools/test-session.ps1 -Action Restore"
    $files | Select-Object path, sha256
} catch {
    # Recovery manifest and verified originals remain available even after a failed setup.
    Write-Error "Test setup failed; run -Action Restore. $($_.Exception.Message)"
}
