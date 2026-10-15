<#
.SYNOPSIS
    Integration fixture for tools/test-session.ps1 (Begin/Restore round trips).

.DESCRIPTION
    Run only while HOI4 is closed. Uses a fresh folder under $env:TEMP, keeps
    fixtures/result.json for inspection and never touches the real user directory.
    Checks: a modern (three-file) Begin/Restore round trip with exact SHA-256 restore,
    the values written by Begin, that unrelated settings survive, and that an old
    two-file manifest is still restored byte for byte without creating pdx_settings.txt.
    The helper runs in Windows PowerShell 5.1 (powershell.exe -File), as users run it.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:FixtureGameProcessName = 'hoi4'
$script:FixtureFileNames = @('dlc_load.json', 'settings.txt', 'pdx_settings.txt')
$script:FixtureLegacyFileNames = @('dlc_load.json', 'settings.txt')
$script:FixtureManifestName = 'rename_anything_test_session.json'
$script:FixtureBackupSuffix = '.impl_backup'
$script:FixtureUtf8 = New-Object System.Text.UTF8Encoding($false)

function Assert-Fixture {
    <#
    .SYNOPSIS
        Throws "Fixture assertion failed" when a condition is false.
    .DESCRIPTION
        Minimal assertion helper; the fixture stops at the first failure.
    .PARAMETER Condition
        Value that must be true.
    .PARAMETER Message
        What was checked.
    .OUTPUTS
        None.
    .EXAMPLE
        Assert-Fixture -Condition ($x -eq 1) -Message 'x is one'
    #>
    [CmdletBinding()]
    [OutputType([void])]
    param(
        [Parameter(Mandatory)][bool]$Condition,
        [Parameter(Mandatory)][string]$Message
    )
    if (-not $Condition) { throw "Fixture assertion failed: $Message" }
}

function Invoke-FixtureHelper {
    <#
    .SYNOPSIS
        Runs tools/test-session.ps1 in Windows PowerShell 5.1 against a fixture folder.
    .DESCRIPTION
        Always uses -Language polish; fails the fixture on a non-zero exit code.
    .PARAMETER Action
        Begin or Restore.
    .PARAMETER Directory
        Fixture user folder.
    .PARAMETER WithCapieSwitch
        Pass -WithCapieSwitch to the helper.
    .OUTPUTS
        None.
    .EXAMPLE
        Invoke-FixtureHelper -Action Begin -Directory $modern
    #>
    [CmdletBinding()]
    [OutputType([void])]
    param(
        [Parameter(Mandatory)][ValidateSet('Begin', 'Restore')][string]$Action,
        [Parameter(Mandatory)][string]$Directory,
        [switch]$WithCapieSwitch
    )
    if ($WithCapieSwitch) {
        & powershell.exe -NoProfile -File $helper -Action $Action -UserDirectory $Directory -Language polish -WithCapieSwitch | Out-Host
    } else {
        & powershell.exe -NoProfile -File $helper -Action $Action -UserDirectory $Directory -Language polish | Out-Host
    }
    Assert-Fixture -Condition ($LASTEXITCODE -eq 0) -Message "Helper $Action exit $LASTEXITCODE"
}

function Write-FixtureText {
    <#
    .SYNOPSIS
        Writes fixture text as UTF-8 without BOM.
    .DESCRIPTION
        Same encoding the helper writes.
    .PARAMETER Path
        Target file.
    .PARAMETER Text
        Content.
    .OUTPUTS
        None.
    .EXAMPLE
        Write-FixtureText -Path $p -Text 'x'
    #>
    [CmdletBinding()]
    [OutputType([void])]
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Text
    )
    [IO.File]::WriteAllText($Path, $Text, $script:FixtureUtf8)
}

function Get-FixtureHash {
    <#
    .SYNOPSIS
        SHA-256 of a fixture file.
    .DESCRIPTION
        Upper-case hex, same as the helper's manifest.
    .PARAMETER Path
        File to hash.
    .OUTPUTS
        System.String
    .EXAMPLE
        Get-FixtureHash -Path $p
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

if (Get-Process -Name $script:FixtureGameProcessName -ErrorAction SilentlyContinue) {
    throw 'Fixture test deferred: close HOI4; its global guard must remain effective.'
}
$fixtureRoot = Join-Path $env:TEMP ('rn-test-session-fixture-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixtureRoot | Out-Null
$modern = Join-Path $fixtureRoot 'modern'
$legacy = Join-Path $fixtureRoot 'legacy'
New-Item -ItemType Directory -Path $modern, $legacy | Out-Null
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
$expected = @{}
foreach ($directory in @($modern, $legacy)) {
    Write-FixtureText -Path (Join-Path $directory 'dlc_load.json') -Text '{"enabled_mods":["mod/user.mod"],"disabled_dlcs":["dlc/fixture.dlc"]}'
    Write-FixtureText -Path (Join-Path $directory 'settings.txt') -Text $legacyText
}
Write-FixtureText -Path (Join-Path $modern 'pdx_settings.txt') -Text $pdxText
foreach ($name in $script:FixtureFileNames) { $expected[$name] = Get-FixtureHash -Path (Join-Path $modern $name) }

# Modern three-file session: Begin.
Invoke-FixtureHelper -Action Begin -Directory $modern
$manifestPath = Join-Path $modern $script:FixtureManifestName
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
Assert-Fixture -Condition (@($manifest.files).Count -eq 3) -Message 'Modern manifest has three files'
foreach ($entry in $manifest.files) {
    $name = [IO.Path]::GetFileName($entry.path)
    Assert-Fixture -Condition ($entry.sha256 -eq $expected[$name]) -Message "Manifest original hash for $name"
    Assert-Fixture -Condition ((Get-FixtureHash -Path $entry.backup) -eq $expected[$name]) -Message "Backup hash for $name"
}
$preparedLegacy = Get-Content -LiteralPath (Join-Path $modern 'settings.txt') -Raw
$preparedPdx = Get-Content -LiteralPath (Join-Path $modern 'pdx_settings.txt') -Raw
Assert-Fixture -Condition ($preparedLegacy.Contains('language="l_polish"')) -Message 'Legacy Polish language'
Assert-Fixture -Condition ($preparedLegacy.Contains('size={ x=1720 y=900 }')) -Message 'Legacy window resolution'
Assert-Fixture -Condition ($preparedLegacy.Contains('fullScreen=no') -and $preparedLegacy.Contains('borderless=no')) -Message 'Legacy window mode'
Assert-Fixture -Condition ($preparedPdx -match '"language"\s*=\s*\{\s*value="l_polish"\s+version=0\s*\}') -Message 'Modern Polish language'
Assert-Fixture -Condition ($preparedPdx -match '"windowed_resolution"\s*=\s*\{\s*value="1720x900"\s+version=0\s*\}') -Message 'Modern window resolution'
Assert-Fixture -Condition ($preparedPdx -match '"display_mode"\s*=\s*\{\s*value="windowed"\s+version=0\s*\}') -Message 'Modern window mode'
$unrelatedKept = $preparedPdx.Contains('"other"={ value="keep" version=8 }') -and $preparedPdx.Contains('"refresh_rate"={ value="144" version=0 }')
Assert-Fixture -Condition $unrelatedKept -Message 'Unrelated modern settings retained'

# Modern three-file session: Restore after the game changed everything.
foreach ($name in $script:FixtureFileNames) {
    Write-FixtureText -Path (Join-Path $modern $name) -Text 'changed by fixture after Begin'
}
Invoke-FixtureHelper -Action Restore -Directory $modern
foreach ($name in $script:FixtureFileNames) {
    $path = Join-Path $modern $name
    Assert-Fixture -Condition ((Get-FixtureHash -Path $path) -eq $expected[$name]) -Message "Modern roundtrip hash for $name"
    Assert-Fixture -Condition (-not (Test-Path -LiteralPath ($path + $script:FixtureBackupSuffix))) -Message "Modern backup removed for $name"
}
Assert-Fixture -Condition (-not (Test-Path -LiteralPath $manifestPath)) -Message 'Modern manifest removed'

# Construct the exact old two-file manifest shape rather than relying on a new Begin.
$oldFiles = @()
foreach ($name in $script:FixtureLegacyFileNames) {
    $path = Join-Path $legacy $name
    $backup = $path + $script:FixtureBackupSuffix
    $hash = Get-FixtureHash -Path $path
    Copy-Item -LiteralPath $path -Destination $backup
    $oldFiles += [pscustomobject]@{ path = $path; backup = $backup; sha256 = $hash }
    Write-FixtureText -Path $path -Text 'changed by legacy fixture'
}
@{ files = $oldFiles; started = '2026-10-01T00:00:00+02:00' } | ConvertTo-Json -Depth 4 |
    Set-Content -LiteralPath (Join-Path $legacy $script:FixtureManifestName) -Encoding UTF8
Invoke-FixtureHelper -Action Restore -Directory $legacy
foreach ($entry in $oldFiles) {
    Assert-Fixture -Condition ((Get-FixtureHash -Path $entry.path) -eq $entry.sha256) -Message 'Old manifest byte-for-byte restore'
    Assert-Fixture -Condition (-not (Test-Path -LiteralPath $entry.backup)) -Message 'Old manifest backup removed'
}
Assert-Fixture -Condition (-not (Test-Path -LiteralPath (Join-Path $legacy 'pdx_settings.txt'))) -Message 'Old manifest does not create modern settings'
# CAPIE switch mod: a descriptor created by Begin is removed by Restore; an existing one is backed up.
foreach ($existing in @($false, $true)) {
    $dir = Join-Path $fixtureRoot ('capie-' + $existing)
    New-Item -ItemType Directory -Path (Join-Path $dir 'mod') | Out-Null
    Write-FixtureText -Path (Join-Path $dir 'dlc_load.json') -Text '{"enabled_mods":[],"disabled_dlcs":[]}'
    Write-FixtureText -Path (Join-Path $dir 'settings.txt') -Text $legacyText
    $capie = Join-Path $dir 'mod\capie.mod'
    if ($existing) { Write-FixtureText -Path $capie -Text 'name="CAPIE"' }
    $before = @{}
    foreach ($item in Get-ChildItem -LiteralPath $dir -Recurse -File) { $before[$item.FullName] = Get-FixtureHash -Path $item.FullName }
    Invoke-FixtureHelper -Action Begin -Directory $dir -WithCapieSwitch
    $dlc = Get-Content -LiteralPath (Join-Path $dir 'dlc_load.json') -Raw | ConvertFrom-Json
    Assert-Fixture -Condition (@($dlc.enabled_mods) -contains 'mod/capie.mod') -Message "CAPIE switch enabled (existing=$existing)"
    Assert-Fixture -Condition (@($dlc.enabled_mods) -contains 'mod/rename_anything_dev.mod') -Message 'Dev mod still enabled'
    $descriptor = Get-Content -LiteralPath $capie -Raw
    Assert-Fixture -Condition ($descriptor -match 'path=".*/mod/capie_dev"') -Message 'Descriptor points at the session copy'
    $inner = Get-Content -LiteralPath (Join-Path $dir 'mod\capie_dev\descriptor.mod') -Raw
    Assert-Fixture -Condition ($inner -match 'name="CAPIE \(dev\)"') -Message 'Session copy descriptor.mod has the session name (the launcher reads it)'
    $devInner = Get-Content -LiteralPath (Join-Path $dir 'mod\rename_anything_dev\descriptor.mod') -Raw
    Assert-Fixture -Condition ($devInner -match 'name="Rename Anything \(dev\)"') -Message 'Dev copy descriptor.mod is not the Workshop name'
    Assert-Fixture -Condition ($descriptor -match 'name="CAPIE \(dev\)"') -Message 'Descriptor name differs from the Workshop item'
    Invoke-FixtureHelper -Action Restore -Directory $dir
    if ($existing) {
        Assert-Fixture -Condition ((Get-FixtureHash -Path $capie) -eq $before[$capie]) -Message 'Existing capie.mod restored'
    } else {
        Assert-Fixture -Condition (-not (Test-Path -LiteralPath $capie)) -Message 'Created capie.mod removed'
    }
    foreach ($path in $before.Keys) {
        Assert-Fixture -Condition ((Get-FixtureHash -Path $path) -eq $before[$path]) -Message "CAPIE session restore $path"
    }
    $left = @(Get-ChildItem -LiteralPath $dir -Recurse -File | Where-Object { -not $before.ContainsKey($_.FullName) })
    Assert-Fixture -Condition ($left.Count -eq 0) -Message "Restore removes every session file ($(($left | ForEach-Object { $_.FullName }) -join ', '))"
}
$report = [pscustomobject]@{
    modern_begin_restore = 'PASS'; modern_manifest_hashes = 'PASS'; modern_values = 'PASS'
    unrelated_settings_preserved = 'PASS'; all_three_sha256_restored = 'PASS'
    old_two_file_manifest_restore = 'PASS'; capie_switch_begin_restore = 'PASS'; fixture_root = $fixtureRoot
}
$report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $fixtureRoot 'result.json') -Encoding UTF8
$report | ConvertTo-Json
