# Integration fixture: run only while HOI4 is closed. Uses a fresh TEMP directory,
# retains fixtures/result.json for inspection, and never touches the real user directory.
$ErrorActionPreference = 'Stop'
if (Get-Process -Name hoi4 -ErrorAction SilentlyContinue) {
    throw 'Fixture test deferred: close HOI4; its global guard must remain effective.'
}
$fixtureRoot = Join-Path $env:TEMP ('rn-test-session-fixture-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixtureRoot | Out-Null
$modern = Join-Path $fixtureRoot 'modern'
$legacy = Join-Path $fixtureRoot 'legacy'
New-Item -ItemType Directory -Path $modern,$legacy | Out-Null
$helper = Join-Path (Split-Path -Parent $PSScriptRoot) 'test-session.ps1'
$legacyText = @'
language="l_english"
graphics={
 size={ x=3440 y=1440 }
 fullScreen=yes
 borderless=yes
}
'@
$pdxText = @'
"System"={
 "language"={ value="l_english" version=0 }
 "other"={ value="keep" version=8 }
}
"Graphics"={
 "windowed_resolution"={ value="3440x1440" version=0 }
 "display_mode"={ value="fullscreen" version=0 }
 "refresh_rate"={ value="144" version=0 }
}
'@
function Assert-Fixture([bool]$Condition, [string]$Message) {
    if (!$Condition) { throw "Fixture assertion failed: $Message" }
}
function Invoke-FixtureHelper([string]$Action, [string]$Directory) {
    & powershell.exe -NoProfile -File $helper -Action $Action -UserDirectory $Directory -Language polish
    Assert-Fixture ($LASTEXITCODE -eq 0) "Helper $Action exit $LASTEXITCODE"
}
$expected = @{}
foreach ($directory in @($modern,$legacy)) {
    [IO.File]::WriteAllText((Join-Path $directory 'dlc_load.json'), '{"enabled_mods":["mod/user.mod"],"disabled_dlcs":["dlc/fixture.dlc"]}', [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $directory 'settings.txt'), $legacyText, [Text.UTF8Encoding]::new($false))
}
[IO.File]::WriteAllText((Join-Path $modern 'pdx_settings.txt'), $pdxText, [Text.UTF8Encoding]::new($false))
foreach ($name in @('dlc_load.json','settings.txt','pdx_settings.txt')) {
    $expected[$name] = (Get-FileHash -LiteralPath (Join-Path $modern $name) -Algorithm SHA256).Hash
}
Invoke-FixtureHelper -Action Begin -Directory $modern
$manifestPath = Join-Path $modern 'rename_anything_test_session.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
Assert-Fixture ($manifest.files.Count -eq 3) 'Modern manifest has three files'
foreach ($entry in $manifest.files) {
    $name = [IO.Path]::GetFileName($entry.path)
    Assert-Fixture ($entry.sha256 -eq $expected[$name]) "Manifest original hash for $name"
    Assert-Fixture ((Get-FileHash -LiteralPath $entry.backup -Algorithm SHA256).Hash -eq $expected[$name]) "Backup hash for $name"
}
$preparedLegacy = Get-Content -LiteralPath (Join-Path $modern 'settings.txt') -Raw
$preparedPdx = Get-Content -LiteralPath (Join-Path $modern 'pdx_settings.txt') -Raw
Assert-Fixture ($preparedLegacy.Contains('language="l_polish"')) 'Legacy Polish language'
Assert-Fixture ($preparedLegacy.Contains('size={ x=1720 y=900 }')) 'Legacy window resolution'
Assert-Fixture ($preparedLegacy.Contains('fullScreen=no') -and $preparedLegacy.Contains('borderless=no')) 'Legacy window mode'
Assert-Fixture ($preparedPdx -match '"language"\s*=\s*\{\s*value="l_polish"\s+version=0\s*\}') 'Modern Polish language'
Assert-Fixture ($preparedPdx -match '"windowed_resolution"\s*=\s*\{\s*value="1720x900"\s+version=0\s*\}') 'Modern window resolution'
Assert-Fixture ($preparedPdx -match '"display_mode"\s*=\s*\{\s*value="windowed"\s+version=0\s*\}') 'Modern window mode'
Assert-Fixture ($preparedPdx.Contains('"other"={ value="keep" version=8 }') -and $preparedPdx.Contains('"refresh_rate"={ value="144" version=0 }')) 'Unrelated modern settings retained'
foreach ($name in @('dlc_load.json','settings.txt','pdx_settings.txt')) {
    [IO.File]::WriteAllText((Join-Path $modern $name), 'changed by fixture after Begin', [Text.UTF8Encoding]::new($false))
}
Invoke-FixtureHelper -Action Restore -Directory $modern
foreach ($name in @('dlc_load.json','settings.txt','pdx_settings.txt')) {
    $path = Join-Path $modern $name
    Assert-Fixture ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -eq $expected[$name]) "Modern roundtrip hash for $name"
    Assert-Fixture (!(Test-Path -LiteralPath "$path.impl_backup")) "Modern backup removed for $name"
}
Assert-Fixture (!(Test-Path -LiteralPath $manifestPath)) 'Modern manifest removed'
# Construct the exact old two-file manifest shape rather than relying on a new Begin.
$oldFiles = @()
foreach ($name in @('dlc_load.json','settings.txt')) {
    $path = Join-Path $legacy $name
    $backup = "$path.impl_backup"
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    Copy-Item -LiteralPath $path -Destination $backup
    $oldFiles += [pscustomobject]@{path=$path;backup=$backup;sha256=$hash}
    [IO.File]::WriteAllText($path, 'changed by legacy fixture', [Text.UTF8Encoding]::new($false))
}
@{files=$oldFiles;started='2026-10-01T00:00:00+02:00'} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $legacy 'rename_anything_test_session.json') -Encoding UTF8
Invoke-FixtureHelper -Action Restore -Directory $legacy
foreach ($entry in $oldFiles) {
    Assert-Fixture ((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -eq $entry.sha256) 'Old manifest byte-for-byte restore'
    Assert-Fixture (!(Test-Path -LiteralPath $entry.backup)) 'Old manifest backup removed'
}
Assert-Fixture (!(Test-Path -LiteralPath (Join-Path $legacy 'pdx_settings.txt'))) 'Old manifest does not create modern settings'
$report = [pscustomobject]@{
    modern_begin_restore='PASS'; modern_manifest_hashes='PASS'; modern_values='PASS'
    unrelated_settings_preserved='PASS'; all_three_sha256_restored='PASS'
    old_two_file_manifest_restore='PASS'; fixture_root=$fixtureRoot
}
$report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $fixtureRoot 'result.json') -Encoding UTF8
$report | ConvertTo-Json

