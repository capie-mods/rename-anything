<#
.SYNOPSIS
    Prepares (Begin) or undoes (Restore) a manual HOI4 test session for the dev mod.

.DESCRIPTION
    Begin: backs up dlc_load.json, settings.txt and (when present) pdx_settings.txt next
    to themselves (*.impl_backup), records their SHA-256 in rename_anything_test_session.json,
    then enables only the dev mod descriptor, switches the language and a 1720x900 window.
    Restore: verifies every backup against the manifest BEFORE touching anything, copies
    the backups back, verifies the restored hashes, then removes backups and manifest.
    Old two-file manifests (without pdx_settings.txt) are restored as well.
    HOI4 must be closed for both actions.

.PARAMETER Action
    Begin or Restore.

.PARAMETER UserDirectory
    HOI4 user folder (Documents\Paradox Interactive\Hearts of Iron IV).

.PARAMETER Language
    Game language for the session: english or polish.

.OUTPUTS
    System.String / PSCustomObject. Progress lines and, after Begin, the backed-up files.

.EXAMPLE
    .\tools\test-session.ps1 -Action Begin -Language polish

.EXAMPLE
    .\tools\test-session.ps1 -Action Restore
#>
[CmdletBinding()]
[OutputType([string], [psobject])]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Begin', 'Restore')]
    [string]$Action,
    [ValidateNotNullOrEmpty()]
    [string]$UserDirectory = "$env:USERPROFILE\Documents\Paradox Interactive\Hearts of Iron IV",
    [ValidateSet('english', 'polish')]
    [string]$Language = 'english'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Constants -------------------------------------------------------------
$script:TsGameProcessName = 'hoi4'
$script:TsManifestFileName = 'rename_anything_test_session.json'
$script:TsBackupSuffix = '.impl_backup'
$script:TsDlcLoadFileName = 'dlc_load.json'
$script:TsLegacySettingsFileName = 'settings.txt'
$script:TsModernSettingsFileName = 'pdx_settings.txt'
$script:TsModDirName = 'mod'
$script:TsModDescriptorFileName = 'rename_anything_dev.mod'
$script:TsModName = 'Rename Anything (dev)'
$script:TsModVersion = '0.1.0'
$script:TsSupportedGameVersion = '1.19.*'
$script:TsWindowWidth = 1720
$script:TsWindowHeight = 900
$script:TsWindowMode = 'windowed'
$script:TsManifestJsonDepth = 4
$script:TsUtf8 = New-Object System.Text.UTF8Encoding($false)

# --- Adapters (test seams) -------------------------------------------------
# GetGameProcess() -> array; empty when HOI4 is not running.
$script:TsGetGameProcess = { @(Get-Process -Name $script:TsGameProcessName -ErrorAction SilentlyContinue) }

function Get-TsFileSha256 {
    <#
    .SYNOPSIS
        SHA-256 of a file (upper-case hex).
    .DESCRIPTION
        Single place for hashing so every comparison uses the same format.
    .PARAMETER Path
        File to hash.
    .OUTPUTS
        System.String
    .EXAMPLE
        Get-TsFileSha256 -Path $settingsPath
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Write-TsUtf8 {
    <#
    .SYNOPSIS
        Writes text as UTF-8 without BOM.
    .DESCRIPTION
        HOI4 reads these files as UTF-8; a BOM is never written.
    .PARAMETER Path
        Target file.
    .PARAMETER Text
        Content.
    .OUTPUTS
        None.
    .EXAMPLE
        Write-TsUtf8 -Path $p -Text $t
    #>
    [CmdletBinding()]
    [OutputType([void])]
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Text
    )
    [IO.File]::WriteAllText($Path, $Text, $script:TsUtf8)
}

function Set-PdxSettingValue {
    <#
    .SYNOPSIS
        Replaces value="..." of one quoted setting block in pdx_settings.txt text.
    .DESCRIPTION
        Each modern setting is a flat quoted-key block with value="..." and version.
        Exactly one match is required rather than silently leaving an EN/full-size
        setting active. Pure text function.
    .PARAMETER Text
        pdx_settings.txt content.
    .PARAMETER Setting
        Setting key, e.g. language.
    .PARAMETER Value
        New value.
    .OUTPUTS
        System.String
    .EXAMPLE
        Set-PdxSettingValue -Text $t -Setting 'display_mode' -Value 'windowed'
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Text,
        [Parameter(Mandatory)][string]$Setting,
        [Parameter(Mandatory)][string]$Value
    )
    $pattern = '(?s)(?<prefix>"' + [regex]::Escape($Setting) + '"\s*=\s*\{[^{}]*?\bvalue\s*=\s*")[^"]*(?<suffix>")'
    $pdxMatches = [regex]::Matches($Text, $pattern)
    if ($pdxMatches.Count -ne 1) {
        throw "Expected one pdx_settings.txt block for '$Setting'; found $($pdxMatches.Count)."
    }
    $replacement = $Value
    return [regex]::Replace($Text, $pattern, [System.Text.RegularExpressions.MatchEvaluator] {
            param($match)
            $match.Groups['prefix'].Value + $replacement + $match.Groups['suffix'].Value
        })
}

function Set-TsLegacySetting {
    <#
    .SYNOPSIS
        Applies language, window size and windowed mode to legacy settings.txt text.
    .DESCRIPTION
        Pure text function; keys that are absent are left as they are.
    .PARAMETER Text
        settings.txt content.
    .PARAMETER GameLanguage
        english or polish.
    .OUTPUTS
        System.String
    .EXAMPLE
        Set-TsLegacySetting -Text $t -GameLanguage polish
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Text,
        [Parameter(Mandatory)][string]$GameLanguage
    )
    $t = $Text -replace 'language="l_[^"]+"', "language=`"l_$GameLanguage`""
    $t = $t -replace 'size=\{ x=\d+ y=\d+ \}', "size={ x=$($script:TsWindowWidth) y=$($script:TsWindowHeight) }"
    $t = $t -replace 'fullScreen=yes', 'fullScreen=no'
    return ($t -replace 'borderless=yes', 'borderless=no')
}

function Set-TsModernSetting {
    <#
    .SYNOPSIS
        Applies language, window size and windowed mode to pdx_settings.txt text.
    .DESCRIPTION
        Every setting must exist exactly once (see Set-PdxSettingValue).
    .PARAMETER Text
        pdx_settings.txt content.
    .PARAMETER GameLanguage
        english or polish.
    .OUTPUTS
        System.String
    .EXAMPLE
        Set-TsModernSetting -Text $t -GameLanguage polish
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Text,
        [Parameter(Mandatory)][string]$GameLanguage
    )
    $t = Set-PdxSettingValue -Text $Text -Setting 'language' -Value "l_$GameLanguage"
    $t = Set-PdxSettingValue -Text $t -Setting 'windowed_resolution' -Value "$($script:TsWindowWidth)x$($script:TsWindowHeight)"
    return (Set-PdxSettingValue -Text $t -Setting 'display_mode' -Value $script:TsWindowMode)
}

function Assert-TsGameClosed {
    <#
    .SYNOPSIS
        Throws while HOI4 is running.
    .DESCRIPTION
        Uses the process adapter; never stops the game.
    .OUTPUTS
        None.
    .EXAMPLE
        Assert-TsGameClosed
    #>
    [CmdletBinding()]
    [OutputType([void])]
    param()
    if (@(& $script:TsGetGameProcess).Count -gt 0) {
        throw 'Close HOI4 before starting or restoring a test session.'
    }
}

function Restore-TsSession {
    <#
    .SYNOPSIS
        Restores the files recorded in the session manifest.
    .DESCRIPTION
        Manifest-driven recovery accepts old two-file and new three-file sessions. Every
        recovery copy is checked before any of them is changed or deleted.
    .PARAMETER ManifestPath
        rename_anything_test_session.json.
    .OUTPUTS
        System.String (one line per restored file)
    .EXAMPLE
        Restore-TsSession -ManifestPath $manifestPath
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][string]$ManifestPath)
    if (-not (Test-Path -LiteralPath $ManifestPath)) { throw 'No test-session manifest; nothing restored.' }
    $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
    foreach ($entry in $manifest.files) {
        if (-not (Test-Path -LiteralPath $entry.backup)) { throw "Missing backup: $($entry.backup)" }
        if ((Get-TsFileSha256 -Path $entry.backup) -ne $entry.sha256) { throw "Backup hash mismatch: $($entry.backup)" }
    }
    foreach ($entry in $manifest.files) {
        Copy-Item -LiteralPath $entry.backup -Destination $entry.path -Force
        if ((Get-TsFileSha256 -Path $entry.path) -ne $entry.sha256) { throw "Restored hash mismatch; backups retained: $($entry.path)" }
        Write-Output "Restored $($entry.path) SHA256=$($entry.sha256)"
    }
    foreach ($entry in $manifest.files) { Remove-Item -LiteralPath $entry.backup }
    Remove-Item -LiteralPath $ManifestPath
}

function Backup-TsSessionFile {
    <#
    .SYNOPSIS
        Creates verified *.impl_backup copies and returns the manifest entries.
    .DESCRIPTION
        Refuses to overwrite an existing backup and requires every file to exist. The
        modern pdx_settings.txt is included only when it exists (recent HOI4 builds
        overwrite settings.txt from it at startup); it is never created.
    .PARAMETER Directory
        HOI4 user folder.
    .OUTPUTS
        System.Management.Automation.PSCustomObject[] (path, backup, sha256)
    .EXAMPLE
        $files = Backup-TsSessionFile -Directory $UserDirectory
    #>
    [CmdletBinding()]
    [OutputType([psobject[]], [object[]])]
    param([Parameter(Mandatory)][string]$Directory)
    $fileNames = @($script:TsDlcLoadFileName, $script:TsLegacySettingsFileName)
    if (Test-Path -LiteralPath (Join-Path $Directory $script:TsModernSettingsFileName)) { $fileNames += $script:TsModernSettingsFileName }
    $files = @()
    foreach ($name in $fileNames) {
        $path = Join-Path $Directory $name
        $backup = $path + $script:TsBackupSuffix
        if (Test-Path -LiteralPath $backup) { throw "Existing backup; refusing to overwrite: $backup" }
        if (-not (Test-Path -LiteralPath $path)) { throw "Required user file is missing: $path" }
        $files += [pscustomobject]@{ path = $path; backup = $backup; sha256 = (Get-TsFileSha256 -Path $path) }
    }
    foreach ($entry in $files) {
        Copy-Item -LiteralPath $entry.path -Destination $entry.backup
        if ((Get-TsFileSha256 -Path $entry.backup) -ne $entry.sha256) {
            throw "Backup hash mismatch; original files untouched: $($entry.path)"
        }
    }
    return $files
}

function Start-TsSession {
    <#
    .SYNOPSIS
        Backs up the user files and switches them to the dev test configuration.
    .DESCRIPTION
        Writes the recovery manifest first. If changing the files fails, the manifest and
        the verified backups stay in place and the error asks for -Action Restore.
    .PARAMETER Directory
        HOI4 user folder.
    .PARAMETER GameLanguage
        english or polish.
    .PARAMETER RepoDirectory
        Repository root (the dev mod is <repo>\mod).
    .OUTPUTS
        System.String / PSCustomObject (status line and backed-up files)
    .EXAMPLE
        Start-TsSession -Directory $UserDirectory -GameLanguage polish -RepoDirectory $repo
    #>
    [CmdletBinding()]
    [OutputType([string], [psobject])]
    param(
        [Parameter(Mandatory)][string]$Directory,
        [Parameter(Mandatory)][string]$GameLanguage,
        [Parameter(Mandatory)][string]$RepoDirectory
    )
    $manifestPath = Join-Path $Directory $script:TsManifestFileName
    if (Test-Path -LiteralPath $manifestPath) { throw 'Existing test-session manifest. Restore it first.' }
    $files = @(Backup-TsSessionFile -Directory $Directory)
    @{ files = $files; started = [DateTimeOffset]::Now.ToString('o') } | ConvertTo-Json -Depth $script:TsManifestJsonDepth |
        Set-Content -LiteralPath $manifestPath -Encoding UTF8
    try {
        $pdxSettingsPath = Join-Path $Directory $script:TsModernSettingsFileName
        $pdxSettings = $null
        if (Test-Path -LiteralPath $pdxSettingsPath) {
            $pdxSettings = Set-TsModernSetting -Text ([IO.File]::ReadAllText($pdxSettingsPath)) -GameLanguage $GameLanguage
        }
        $modDirectory = Join-Path $Directory $script:TsModDirName
        if (-not (Test-Path -LiteralPath $modDirectory)) { New-Item -ItemType Directory -Path $modDirectory | Out-Null }
        $modPath = (Join-Path $RepoDirectory 'mod').Replace('\', '/')
        $descriptor = @(
            "version=`"$($script:TsModVersion)`"`n",
            "name=`"$($script:TsModName)`"`n",
            "supported_version=`"$($script:TsSupportedGameVersion)`"`n",
            "path=`"$modPath`"`n"
        ) -join ''
        Write-TsUtf8 -Path (Join-Path $modDirectory $script:TsModDescriptorFileName) -Text $descriptor
        $dlcLoad = '{"enabled_mods":["' + $script:TsModDirName + '/' + $script:TsModDescriptorFileName + '"],"disabled_dlcs":[]}'
        Write-TsUtf8 -Path (Join-Path $Directory $script:TsDlcLoadFileName) -Text $dlcLoad
        $settingsPath = Join-Path $Directory $script:TsLegacySettingsFileName
        Write-TsUtf8 -Path $settingsPath -Text (Set-TsLegacySetting -Text ([IO.File]::ReadAllText($settingsPath)) -GameLanguage $GameLanguage)
        if ($null -ne $pdxSettings) { Write-TsUtf8 -Path $pdxSettingsPath -Text $pdxSettings }
        $size = "$($script:TsWindowWidth)x$($script:TsWindowHeight)"
        Write-Output "Test session prepared ($GameLanguage, $size). After closing HOI4 run: tools/test-session.ps1 -Action Restore"
        $files | Select-Object path, sha256
    } catch {
        # Recovery manifest and verified originals remain available even after a failed setup.
        Write-Error "Test setup failed; run -Action Restore. $($_.Exception.Message)"
    }
}

# Dot-sourcing (". .\test-session.ps1 -Action Restore") only defines the functions, for tests.
if ($MyInvocation.InvocationName -eq '.') { return }
Assert-TsGameClosed
if ($Action -eq 'Restore') {
    Restore-TsSession -ManifestPath (Join-Path $UserDirectory $script:TsManifestFileName)
    exit 0
}
Start-TsSession -Directory $UserDirectory -GameLanguage $Language -RepoDirectory (Split-Path -Parent $PSScriptRoot)
