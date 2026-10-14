<#
.SYNOPSIS
    Splits the monorepo into the capie, capie-script-sdk, capie-design and rename-anything
    repositories with history kept, in a working folder outside the repository.

.DESCRIPTION
    Repeatable and read-only towards the source repository. For every repository named in
    split-map.psd1 (or in -Repository) the script:

      1. clones the source with "git clone --no-local --single-branch" into
         <WorkRoot>\<name> (a fresh, unshared object store; the source is not touched);
      2. runs git filter-repo with that repository's path list and renames
         (uv run --no-project --with git-filter-repo git-filter-repo);
      3. scans the whole new history with scan_history.py: forbidden paths (build output,
         binaries, caches, key files; the Forbidden list of the map, plus ArchiveOnly:
         docs/evidence and documents moved into it, ADR-0034), Windows PE content
         under any name, private keys, token formats, large blobs;
      4. removes what the scan found: an --invert-paths pass for forbidden paths and PE or
         key files, --strip-blobs-bigger-than, and --replace-text for token values;
      5. scans again, requires zero forbidden paths, executables and secrets, checks the
         Expect files of the map, runs git gc and records commits, size and the file list.

    Before that, one more fresh clone (<WorkRoot>\_source) is checked for history paths that
    no repository selects (they would be lost). The results go to <WorkRoot>\report.txt and
    <WorkRoot>\report.json, the file list of each repository to <WorkRoot>\<name>.files.txt,
    the logs and filter files to <WorkRoot>\_work\.

    Nothing is pushed unless -Push is given together with -PushOwner. Push only adds a remote
    and pushes all branches and tags of a repository that passed every check; the target
    repositories must already exist (empty, private).

.PARAMETER WorkRoot
    Working folder for the clones and reports. Must be outside the source repository.
    Created when missing. Existing repository folders in it are refused unless -Force.

.PARAMETER SourceRepository
    The monorepo to split. Default: the repository that contains this script.

.PARAMETER Branch
    Branch to clone and split. Default: main.

.PARAMETER Repository
    Names of the repositories to produce (keys of split-map.psd1). Default: all of them.

.PARAMETER MapPath
    Path map. Default: split-map.psd1 next to this script.

.PARAMETER StripBlobsBiggerThan
    Size limit for git filter-repo --strip-blobs-bigger-than (for example 10M). Blobs above it
    are removed from the history of the new repositories.

.PARAMETER LargeBlobBytes
    Blobs above this size are listed in the report as large (not removed).

.PARAMETER Python
    Python 3.13 interpreter that runs scan_history.py (run with -I). Default: python.

.PARAMETER ReplaceTextPath
    Optional git filter-repo --replace-text file applied to the whole history of every new
    repository after the cleanup (for example scrub-user-paths.txt, which replaces the
    maintainer's Windows profile path). Off by default; changed files are listed in the report.

.PARAMETER Force
    Delete existing <WorkRoot>\<name> folders (and _source, _work) before cloning.

.PARAMETER Push
    Push the produced repositories. Off by default; requires -PushOwner.

.PARAMETER PushOwner
    GitHub owner (user or organisation) of the target repositories, for example capie-mods.

.PARAMETER PushUrlTemplate
    Remote URL template; {0} is the owner, {1} the repository name.

.OUTPUTS
    System.Management.Automation.PSCustomObject (one result per repository)

.EXAMPLE
    .\tools\repo-split\split.ps1 -WorkRoot $env:TEMP\repo-split-dry -Force

.EXAMPLE
    .\tools\repo-split\split.ps1 -WorkRoot D:\split -Repository capie-script-sdk

.EXAMPLE
    # Only after the maintainer has confirmed the transfer and created the empty repositories:
    .\tools\repo-split\split.ps1 -WorkRoot D:\split -Force -Push -PushOwner capie-mods
#>
[CmdletBinding()]
[OutputType([pscustomobject])]
param(
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$WorkRoot,
    [string]$SourceRepository = '',
    [ValidateNotNullOrEmpty()][string]$Branch = 'main',
    [string[]]$Repository = @(),
    [string]$MapPath = '',
    [ValidatePattern('^\d+[KMG]?$')][string]$StripBlobsBiggerThan = '10M',
    [ValidateRange(1, [long]::MaxValue)][long]$LargeBlobBytes = 1048576,
    [ValidateNotNullOrEmpty()][string]$Python = 'python',
    [string]$ReplaceTextPath = '',
    [switch]$Force,
    [switch]$Push,
    [string]$PushOwner = '',
    [ValidateNotNullOrEmpty()][string]$PushUrlTemplate = 'https://github.com/{0}/{1}.git'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:ScanScript = Join-Path $PSScriptRoot 'scan_history.py'
$script:Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$script:EvidenceLinkPattern = '(^|[^A-Za-z0-9_-])evidence/'
$script:UserPathPattern = '[A-Za-z]:[\\/]{1,2}Users[\\/]{1,2}[A-Za-z0-9._ -]+'
$script:FilterRepo = @('run', '--no-project', '--quiet', '--with', 'git-filter-repo', 'git-filter-repo')

function Write-SplitInfo {
    <#
    .SYNOPSIS
        Prints one progress line.
    .DESCRIPTION
        Writes to the information stream with InformationAction Continue, so the line is shown
        without Write-Host and can still be redirected (6>).
    .PARAMETER Message
        Text to print.
    .OUTPUTS
        None
    .EXAMPLE
        Write-SplitInfo -Message 'clone capie'
    #>
    [CmdletBinding()]
    [OutputType([void])]
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Message)
    Write-Information -MessageData $Message -InformationAction Continue
}

function Invoke-SplitNative {
    <#
    .SYNOPSIS
        Runs a native program and returns its exit code and output lines.
    .DESCRIPTION
        Merges standard error into the output (Git and filter-repo report progress there),
        appends everything to -LogPath when given, and throws on a non-zero exit code unless
        -AllowFailure. ErrorActionPreference is lowered only around the call, so stderr lines
        of Windows PowerShell 5.1 do not become terminating errors.
    .PARAMETER FilePath
        Program to run (resolved from PATH).
    .PARAMETER ArgumentList
        Arguments, passed one by one.
    .PARAMETER WorkingDirectory
        Folder to run in; empty keeps the current one.
    .PARAMETER LogPath
        Optional log file that receives the command line and its output.
    .PARAMETER AllowFailure
        Return a non-zero exit code instead of throwing.
    .OUTPUTS
        System.Management.Automation.PSCustomObject with ExitCode and Output (string[]).
    .EXAMPLE
        Invoke-SplitNative -FilePath git -ArgumentList @('-C', $dir, 'rev-list', '--count', 'HEAD')
    #>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$FilePath,
        [Parameter(Mandatory)][string[]]$ArgumentList,
        [string]$WorkingDirectory = '',
        [string]$LogPath = '',
        [switch]$AllowFailure
    )
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    if ($WorkingDirectory) { Push-Location -LiteralPath $WorkingDirectory }
    try {
        $output = @(& $FilePath @ArgumentList 2>&1 | ForEach-Object { [string]$_ })
        $code = $LASTEXITCODE
    } finally {
        if ($WorkingDirectory) { Pop-Location }
        $ErrorActionPreference = $previous
    }
    if ($LogPath) {
        $text = ('> {0} {1}' -f $FilePath, ($ArgumentList -join ' ')) + [Environment]::NewLine
        $text += ($output -join [Environment]::NewLine) + [Environment]::NewLine
        [IO.File]::AppendAllText($LogPath, $text, $script:Utf8NoBom)
    }
    if ($code -ne 0 -and -not $AllowFailure) {
        $tail = ($output | Select-Object -Last 15) -join [Environment]::NewLine
        throw ('{0} {1} failed with exit code {2}:{3}{4}' -f $FilePath, ($ArgumentList -join ' '), $code, [Environment]::NewLine, $tail)
    }
    return [pscustomobject]@{ ExitCode = $code; Output = $output }
}

function Invoke-SplitGit {
    <#
    .SYNOPSIS
        Runs one Git command in a repository and returns its output lines.
    .DESCRIPTION
        Thin wrapper over Invoke-SplitNative with "git -C <Directory>"; core.quotepath is off
        so non-ASCII file names come back unquoted. Throws on failure.
    .PARAMETER Directory
        Repository folder.
    .PARAMETER ArgumentList
        Git arguments after "git -C <Directory>".
    .PARAMETER LogPath
        Optional log file.
    .OUTPUTS
        System.String[]
    .EXAMPLE
        Invoke-SplitGit -Directory $dir -ArgumentList @('rev-list', '--count', 'HEAD')
    #>
    [CmdletBinding()]
    [OutputType([string[]], [object[]])]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Directory,
        [Parameter(Mandatory)][string[]]$ArgumentList,
        [string]$LogPath = ''
    )
    $all = @('-C', $Directory, '-c', 'core.quotepath=off') + $ArgumentList
    return (Invoke-SplitNative -FilePath 'git' -ArgumentList $all -LogPath $LogPath).Output
}

function Invoke-SplitFilterRepo {
    <#
    .SYNOPSIS
        Runs git filter-repo inside one repository.
    .DESCRIPTION
        Uses "uv run --no-project --with git-filter-repo git-filter-repo", so no package is
        installed into the monorepo environment. filter-repo works on the current directory;
        the call runs inside -Directory.
    .PARAMETER Directory
        Repository to rewrite.
    .PARAMETER ArgumentList
        filter-repo arguments.
    .PARAMETER LogPath
        Log file that receives the output.
    .OUTPUTS
        None
    .EXAMPLE
        Invoke-SplitFilterRepo -Directory $dir -ArgumentList @('--paths-from-file', $f) -LogPath $log
    #>
    [CmdletBinding()]
    [OutputType([void])]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Directory,
        [Parameter(Mandatory)][string[]]$ArgumentList,
        [Parameter(Mandatory)][string]$LogPath
    )
    $null = Invoke-SplitNative -FilePath 'uv' -ArgumentList ($script:FilterRepo + $ArgumentList) -WorkingDirectory $Directory -LogPath $LogPath
}

function Write-SplitTextFile {
    <#
    .SYNOPSIS
        Writes lines as UTF-8 without BOM and with LF line ends.
    .DESCRIPTION
        git filter-repo reads its path and replacement files as bytes; a BOM would become
        part of the first pattern, and Windows PowerShell 5.1 Set-Content writes one.
    .PARAMETER Path
        Target file.
    .PARAMETER Line
        Lines to write.
    .OUTPUTS
        None
    .EXAMPLE
        Write-SplitTextFile -Path paths.txt -Line @('plugin/', 'README.md')
    #>
    [CmdletBinding()]
    [OutputType([void])]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Path,
        [Parameter(Mandatory)][AllowEmptyCollection()][string[]]$Line
    )
    $text = ''
    foreach ($item in $Line) { $text += $item + "`n" }
    [IO.File]::WriteAllText($Path, $text, $script:Utf8NoBom)
}

function Get-SplitFullPath {
    <#
    .SYNOPSIS
        Returns an absolute path with a trailing separator, for prefix comparisons.
    .DESCRIPTION
        Resolves relative paths against the current location; the path does not need to exist.
    .PARAMETER Path
        Path to normalise.
    .OUTPUTS
        System.String
    .EXAMPLE
        Get-SplitFullPath -Path .\out
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Path)
    $full = [IO.Path]::GetFullPath($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path))
    if (-not $full.EndsWith([IO.Path]::DirectorySeparatorChar)) { $full += [IO.Path]::DirectorySeparatorChar }
    return $full
}

function Invoke-SplitScan {
    <#
    .SYNOPSIS
        Runs scan_history.py on one repository and returns the parsed report.
    .DESCRIPTION
        Writes the JSON report (and, with -ReplaceOut, the --replace-text file of token values)
        and returns the report as an object. The report never contains secret values.
    .PARAMETER Directory
        Repository to scan.
    .PARAMETER ReportPath
        JSON report file to write.
    .PARAMETER ForbiddenPath
        Paths file with the forbidden patterns.
    .PARAMETER ReplaceOut
        Optional --replace-text output file.
    .PARAMETER Assigned
        Optional paths files; enables the unassigned-path check.
    .PARAMETER LogPath
        Log file.
    .PARAMETER Options
        Run options (Python, LargeBlobBytes).
    .OUTPUTS
        System.Management.Automation.PSCustomObject
    .EXAMPLE
        Invoke-SplitScan -Directory $dir -ReportPath scan.json -ForbiddenPath forbidden.txt -LogPath log.txt -Options $options
    #>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Directory,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$ReportPath,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$ForbiddenPath,
        [string]$ReplaceOut = '',
        [string[]]$Assigned = @(),
        [Parameter(Mandatory)][string]$LogPath,
        [Parameter(Mandatory)][pscustomobject]$Options
    )
    $arguments = @('-I', $script:ScanScript, '--repo', $Directory, '--report', $ReportPath,
        '--forbidden', $ForbiddenPath, '--large-bytes', [string]$Options.LargeBlobBytes)
    if ($ReplaceOut) { $arguments += @('--replace-out', $ReplaceOut) }
    if ($Assigned.Count -gt 0) { $arguments += @('--assigned') + $Assigned }
    $null = Invoke-SplitNative -FilePath $Options.Python -ArgumentList $arguments -LogPath $LogPath
    return (Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Get-SplitPathLine {
    <#
    .SYNOPSIS
        Builds the --paths-from-file lines of one repository.
    .DESCRIPTION
        Filters first, renames after them: filter-repo applies the entries in file order and
        a filter must see the original path.
    .PARAMETER Definition
        Hashtable of one repository from split-map.psd1 (Paths, Renames).
    .PARAMETER IncludeRenames
        Also emit the rename lines.
    .OUTPUTS
        System.String[]
    .EXAMPLE
        Get-SplitPathLine -Definition $map.Repositories.capie -IncludeRenames
    #>
    [CmdletBinding()]
    [OutputType([string[]], [object[]])]
    param(
        [Parameter(Mandatory)][hashtable]$Definition,
        [switch]$IncludeRenames
    )
    $lines = @($Definition.Paths)
    if ($IncludeRenames) { $lines += @($Definition.Renames) }
    return , [string[]]$lines
}

function Get-SplitStatistic {
    <#
    .SYNOPSIS
        Collects commits, pack size and the file list of a split repository.
    .DESCRIPTION
        Reads "git rev-list", "git count-objects -v" and "git ls-tree -r -l HEAD", writes the
        file list (size and path) to -FileListPath and returns the numbers plus a per-top-level
        folder summary.
    .PARAMETER Directory
        Repository folder.
    .PARAMETER FileListPath
        Output file for the list of files at the tip.
    .OUTPUTS
        System.Management.Automation.PSCustomObject
    .EXAMPLE
        Get-SplitStatistic -Directory $dir -FileListPath capie.files.txt
    #>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Directory,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$FileListPath
    )
    $commits = [int]@(Invoke-SplitGit -Directory $Directory -ArgumentList @('rev-list', '--count', '--all'))[0]
    $branches = @(Invoke-SplitGit -Directory $Directory -ArgumentList @('for-each-ref', '--format=%(refname:short)', 'refs/heads', 'refs/tags'))
    $counts = @{}
    foreach ($line in (Invoke-SplitGit -Directory $Directory -ArgumentList @('count-objects', '-v'))) {
        $parts = $line -split ':\s*', 2
        if ($parts.Count -eq 2) { $counts[$parts[0]] = [long]$parts[1] }
    }
    $files = New-Object System.Collections.Generic.List[string]
    $groups = @{}
    $headBytes = [long]0
    foreach ($line in (Invoke-SplitGit -Directory $Directory -ArgumentList @('ls-tree', '-r', '-l', '--full-tree', 'HEAD'))) {
        $meta, $path = $line -split "`t", 2
        $size = [long](($meta -split '\s+')[3])
        $headBytes += $size
        $files.Add(('{0,10} {1}' -f $size, $path))
        $top = if ($path.Contains('/')) { ($path -split '/')[0] + '/' } else { $path }
        if (-not $groups.ContainsKey($top)) { $groups[$top] = @(0, [long]0) }
        $groups[$top] = @(($groups[$top][0] + 1), ($groups[$top][1] + $size))
    }
    [IO.File]::WriteAllLines($FileListPath, $files.ToArray(), $script:Utf8NoBom)
    $summary = foreach ($key in ($groups.Keys | Sort-Object)) {
        [pscustomobject]@{ Path = $key; Files = $groups[$key][0]; Bytes = $groups[$key][1] }
    }
    return [pscustomobject]@{
        Commits   = $commits
        Refs      = $branches
        PackBytes = ($counts['size-pack'] + $counts['size']) * 1024
        HeadFiles = $files.Count
        HeadBytes = $headBytes
        TopLevel  = @($summary)
    }
}

function Get-SplitTipMatch {
    <#
    .SYNOPSIS
        Lists lines at the tip of a repository that match a regular expression.
    .DESCRIPTION
        Runs "git grep -n -I -E" on HEAD (text files only) and returns "path:line: text" entries.
        Exit code 1 of git grep means "no match" and returns an empty list.
    .PARAMETER Directory
        Repository folder.
    .PARAMETER Pattern
        Extended regular expression (git grep -E).
    .OUTPUTS
        System.String[]
    .EXAMPLE
        Get-SplitTipMatch -Directory $dir -Pattern 'evidence/'
    #>
    [CmdletBinding()]
    [OutputType([string[]], [object[]])]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Directory,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Pattern
    )
    $arguments = @('-C', $Directory, '-c', 'core.quotepath=off', 'grep', '-n', '-I', '-E', '-e', $Pattern, 'HEAD')
    $result = Invoke-SplitNative -FilePath 'git' -ArgumentList $arguments -AllowFailure
    if ($result.ExitCode -gt 1) { throw ('git grep failed in {0}' -f $Directory) }
    return @($result.Output | Where-Object { $_ } | ForEach-Object { $_ -replace '^HEAD:', '' })
}

function Get-SplitTree {
    <#
    .SYNOPSIS
        Returns the files at the tip of a repository as a path to blob ID table.
    .DESCRIPTION
        Reads "git ls-tree -r HEAD". Used to prove that every file at the tip of a split
        repository has exactly the content of the same file in the source.
    .PARAMETER Directory
        Repository folder.
    .OUTPUTS
        System.Collections.Hashtable
    .EXAMPLE
        Get-SplitTree -Directory $dir
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param([Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Directory)
    $tree = @{}
    foreach ($line in (Invoke-SplitGit -Directory $Directory -ArgumentList @('ls-tree', '-r', '--full-tree', 'HEAD'))) {
        $meta, $path = $line -split "`t", 2
        $tree[$path] = ($meta -split '\s+')[2]
    }
    return $tree
}

function Compare-SplitTip {
    <#
    .SYNOPSIS
        Lists tip files of a split repository whose content differs from the source tip.
    .DESCRIPTION
        Maps every split path back to its source path through the literal renames of the map
        (NEW prefix back to OLD prefix) and compares blob IDs. A file that is missing in the
        source tip or has other content is returned. Text replaced by --replace-text shows up
        here on purpose.
    .PARAMETER SplitTree
        Tip table of the split repository (Get-SplitTree).
    .PARAMETER SourceTree
        Tip table of the source clone (Get-SplitTree).
    .PARAMETER Rename
        Rename lines of the map ("OLD==>NEW").
    .OUTPUTS
        System.String[]
    .EXAMPLE
        Compare-SplitTip -SplitTree $a -SourceTree $b -Rename @('sdk/capie-script-sdk/==>')
    #>
    [CmdletBinding()]
    [OutputType([string[]], [object[]])]
    param(
        [Parameter(Mandatory)][hashtable]$SplitTree,
        [Parameter(Mandatory)][hashtable]$SourceTree,
        [Parameter(Mandatory)][AllowEmptyCollection()][string[]]$Rename
    )
    $differences = New-Object System.Collections.Generic.List[string]
    foreach ($path in $SplitTree.Keys) {
        $origin = $path
        foreach ($entry in $Rename) {
            $old, $new = $entry -split '==>', 2
            if (-not $path.StartsWith($new, [StringComparison]::Ordinal)) { continue }
            $sourcePath = $old + $path.Substring($new.Length)
            if ($SourceTree.ContainsKey($sourcePath)) { $origin = $sourcePath; break }
        }
        if (-not $SourceTree.ContainsKey($origin)) { $differences.Add('not in source tip: ' + $path) }
        elseif ($SourceTree[$origin] -ne $SplitTree[$path]) { $differences.Add('content differs: ' + $path) }
    }
    return $differences.ToArray()
}

function New-SplitRepository {
    <#
    .SYNOPSIS
        Produces one split repository: clone, filter, clean, verify.
    .DESCRIPTION
        Runs steps 1 to 5 of the script description for one entry of the map and returns a
        result object. Problems that make the repository unfit for pushing are collected in
        Problems and set Status to FAIL; the function throws only on tool failures.
    .PARAMETER Name
        Repository name (key in the map).
    .PARAMETER Definition
        The map entry (Paths, Renames, Expect, Description, Topics).
    .PARAMETER Source
        Source repository path.
    .PARAMETER Root
        Working folder (already validated).
    .PARAMETER ForbiddenFile
        Paths file with the forbidden patterns.
    .PARAMETER SourceCommits
        Number of commits on the source branch, for the report.
    .PARAMETER Options
        Run options (Branch, StripBlobsBiggerThan, LargeBlobBytes, Python).
    .PARAMETER SourceTree
        Tip table of the source clone (Get-SplitTree), for the content comparison.
    .OUTPUTS
        System.Management.Automation.PSCustomObject
    .EXAMPLE
        New-SplitRepository -Name capie -Definition $d -Source $src -Root $root -ForbiddenFile f.txt -SourceCommits 151 -Options $o -SourceTree $t
    #>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Name,
        [Parameter(Mandatory)][hashtable]$Definition,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Source,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Root,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$ForbiddenFile,
        [Parameter(Mandatory)][int]$SourceCommits,
        [Parameter(Mandatory)][pscustomobject]$Options,
        [Parameter(Mandatory)][hashtable]$SourceTree
    )
    $directory = Join-Path $Root $Name
    $work = Join-Path (Join-Path $Root '_work') $Name
    $null = New-Item -ItemType Directory -Path $work -Force
    $log = Join-Path $work 'log.txt'
    $problems = New-Object System.Collections.Generic.List[string]

    Write-SplitInfo -Message ('[{0}] clone {1} ({2})' -f $Name, $Source, $Options.Branch)
    $null = Invoke-SplitNative -FilePath 'git' -LogPath $log -ArgumentList @('clone', '--no-local', '--single-branch',
        '--branch', $Options.Branch, '--', $Source, $directory)

    $pathsFile = Join-Path $work 'paths.txt'
    Write-SplitTextFile -Path $pathsFile -Line (Get-SplitPathLine -Definition $Definition -IncludeRenames)
    Write-SplitInfo -Message ('[{0}] filter-repo: {1} path entries, {2} renames' -f $Name, @($Definition.Paths).Count, @($Definition.Renames).Count)
    Invoke-SplitFilterRepo -Directory $directory -LogPath $log -ArgumentList @('--paths-from-file', $pathsFile)

    Write-SplitInfo -Message ('[{0}] scan history (before cleanup)' -f $Name)
    $replaceFile = Join-Path $work 'replace-text.txt'
    $before = Invoke-SplitScan -Directory $directory -ReportPath (Join-Path $work 'scan-before.json') -ForbiddenPath $ForbiddenFile `
        -ReplaceOut $replaceFile -LogPath $log -Options $Options

    $removeFile = Join-Path $work 'remove-paths.txt'
    $removeLines = @(Get-Content -LiteralPath $ForbiddenFile -Encoding UTF8) + @($before.remove_paths | ForEach-Object { 'literal:' + $_ })
    Write-SplitTextFile -Path $removeFile -Line $removeLines
    Write-SplitInfo -Message ('[{0}] remove forbidden paths ({1} found), PE/key files ({2}), blobs > {3}' -f $Name,
        @($before.forbidden_paths).Count, @($before.remove_paths).Count, $Options.StripBlobsBiggerThan)
    Invoke-SplitFilterRepo -Directory $directory -LogPath $log -ArgumentList @('--force', '--invert-paths', '--paths-from-file', $removeFile,
        '--strip-blobs-bigger-than', $Options.StripBlobsBiggerThan)

    $replaced = @(Get-Content -LiteralPath $replaceFile -Encoding UTF8 | Where-Object { $_ }).Count
    if ($replaced -gt 0) {
        Write-SplitInfo -Message ('[{0}] replace {1} secret value(s) in history' -f $Name, $replaced)
        Invoke-SplitFilterRepo -Directory $directory -LogPath $log -ArgumentList @('--force', '--replace-text', $replaceFile)
    }
    $scrubbed = [bool]$Options.ReplaceTextPath
    if ($scrubbed) {
        Write-SplitInfo -Message ('[{0}] replace text in history with {1}' -f $Name, $Options.ReplaceTextPath)
        Invoke-SplitFilterRepo -Directory $directory -LogPath $log -ArgumentList @('--force', '--replace-text', $Options.ReplaceTextPath)
    }

    $null = Invoke-SplitGit -Directory $directory -LogPath $log -ArgumentList @('reflog', 'expire', '--expire=now', '--all')
    $null = Invoke-SplitGit -Directory $directory -LogPath $log -ArgumentList @('gc', '--prune=now', '--quiet')

    Write-SplitInfo -Message ('[{0}] scan history (after cleanup)' -f $Name)
    $after = Invoke-SplitScan -Directory $directory -ReportPath (Join-Path $work 'scan-after.json') -ForbiddenPath $ForbiddenFile -LogPath $log `
        -Options $Options
    if (@($after.forbidden_paths).Count -gt 0) { $problems.Add(('{0} forbidden path(s) remain' -f @($after.forbidden_paths).Count)) }
    if (@($after.executables).Count -gt 0) { $problems.Add(('{0} executable blob(s) remain' -f @($after.executables).Count)) }
    if (@($after.secrets_high).Count -gt 0) { $problems.Add(('{0} secret match(es) remain' -f @($after.secrets_high).Count)) }

    $stats = Get-SplitStatistic -Directory $directory -FileListPath (Join-Path $Root ($Name + '.files.txt'))
    if ($stats.Commits -eq 0 -or $stats.HeadFiles -eq 0) { $problems.Add('repository is empty') }
    foreach ($expected in @($Definition.Expect)) {
        if (-not (Test-Path -LiteralPath (Join-Path $directory $expected) -PathType Leaf)) { $problems.Add('expected file missing: ' + $expected) }
    }
    $evidenceLinks = @(Get-SplitTipMatch -Directory $directory -Pattern $script:EvidenceLinkPattern)
    [IO.File]::WriteAllLines((Join-Path $Root ($Name + '.evidence-links.txt')), [string[]]$evidenceLinks, $script:Utf8NoBom)
    $userPaths = @(Get-SplitTipMatch -Directory $directory -Pattern $script:UserPathPattern)
    [IO.File]::WriteAllLines((Join-Path $Root ($Name + '.user-paths.txt')), [string[]]$userPaths, $script:Utf8NoBom)
    $historyUserPaths = @()
    $historyHits = $after.review_paths.'user-profile-path'
    if ($null -ne $historyHits) {
        $historyUserPaths = @($historyHits.PSObject.Properties | ForEach-Object { '{0,6} {1}' -f $_.Value, $_.Name })
    }
    $differences = @(Compare-SplitTip -SplitTree (Get-SplitTree -Directory $directory) -SourceTree $SourceTree -Rename @($Definition.Renames))
    if ($replaced -eq 0 -and -not $scrubbed -and $differences.Count -gt 0) {
        $problems.Add(('{0} tip file(s) differ from the source tip' -f $differences.Count))
    }
    $remote = @(Invoke-SplitGit -Directory $directory -ArgumentList @('remote'))
    if ($remote.Count -gt 0) { $problems.Add('unexpected remote(s): ' + ($remote -join ', ')) }

    return [pscustomobject]@{
        Name              = $Name
        Status            = $(if ($problems.Count -eq 0) { 'OK' } else { 'FAIL' })
        Directory         = $directory
        Description       = $Definition.Description
        Topics            = @($Definition.Topics)
        SourceCommits     = $SourceCommits
        Commits           = $stats.Commits
        Refs              = $stats.Refs
        PackBytes         = $stats.PackBytes
        HeadFiles         = $stats.HeadFiles
        HeadBytes         = $stats.HeadBytes
        TopLevel          = $stats.TopLevel
        RemovedForbidden  = @($before.forbidden_paths)
        RemovedFiles      = @($before.remove_paths)
        SecretsBefore     = @($before.secrets_high | ForEach-Object { '{0} {1} {2}' -f $_.rule, $_.path, $_.excerpt })
        ReplacedValues    = $replaced
        Scrubbed          = $scrubbed
        BlobsAfter        = $after.blobs
        LargeBlobs        = @($after.large_blobs | ForEach-Object { '{0,10} {1}' -f $_.bytes, $_.path })
        ReviewCounts      = $after.review_counts
        TipDifferences    = $differences
        EvidenceLinks     = $evidenceLinks
        TipUserPaths      = $userPaths
        HistoryUserPaths  = $historyUserPaths
        Problems          = $problems.ToArray()
    }
}

function Publish-SplitRepository {
    <#
    .SYNOPSIS
        Adds the target remote to a split repository and pushes all branches and tags.
    .DESCRIPTION
        Called only with -Push. Refuses an existing remote, so a repeated run cannot push to
        a remote it did not set up itself.
    .PARAMETER Result
        Result object of New-SplitRepository with Status OK.
    .PARAMETER Url
        Remote URL.
    .OUTPUTS
        None
    .EXAMPLE
        Publish-SplitRepository -Result $r -Url https://github.com/capie-mods/capie.git
    #>
    [CmdletBinding()]
    [OutputType([void])]
    param(
        [Parameter(Mandatory)][pscustomobject]$Result,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Url
    )
    $log = Join-Path (Join-Path (Split-Path -Parent $Result.Directory) '_work') ($Result.Name + '\log.txt')
    if (@(Invoke-SplitGit -Directory $Result.Directory -ArgumentList @('remote')).Count -gt 0) { throw ('{0} already has a remote' -f $Result.Name) }
    Write-SplitInfo -Message ('[{0}] push to {1}' -f $Result.Name, $Url)
    $null = Invoke-SplitGit -Directory $Result.Directory -LogPath $log -ArgumentList @('remote', 'add', 'origin', $Url)
    $null = Invoke-SplitGit -Directory $Result.Directory -LogPath $log -ArgumentList @('push', '--all', 'origin')
    $null = Invoke-SplitGit -Directory $Result.Directory -LogPath $log -ArgumentList @('push', '--tags', 'origin')
}

function Format-SplitReport {
    <#
    .SYNOPSIS
        Renders the text report of a split run.
    .DESCRIPTION
        One section per repository (status, commits, sizes, top-level folders, removals,
        review counts, large blobs, problems) plus the unassigned paths of the source history.
    .PARAMETER Result
        Result objects of New-SplitRepository.
    .PARAMETER Source
        Source repository, commit and commit count.
    .PARAMETER Unassigned
        History paths that no repository selects.
    .PARAMETER LargeBytes
        Threshold that was used for the large-blob list.
    .OUTPUTS
        System.String
    .EXAMPLE
        Format-SplitReport -Result $results -Source $sourceInfo -Unassigned @() -LargeBytes 1048576
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Result,
        [Parameter(Mandatory)][pscustomobject]$Source,
        [Parameter(Mandatory)][AllowEmptyCollection()][string[]]$Unassigned,
        [Parameter(Mandatory)][long]$LargeBytes
    )
    $sb = New-Object System.Text.StringBuilder
    $null = $sb.AppendLine('Repository split report')
    $null = $sb.AppendLine(('Source: {0} branch {1} at {2}; {3} commits; pack {4:N1} MiB' -f $Source.Path, $Source.Branch, $Source.Commit,
            $Source.Commits, ($Source.PackBytes / 1MB)))
    $null = $sb.AppendLine(('Unassigned history paths (lost by the split): {0}' -f $Unassigned.Count))
    foreach ($path in $Unassigned) { $null = $sb.AppendLine('  ' + $path) }
    foreach ($r in $Result) {
        $null = $sb.AppendLine()
        $null = $sb.AppendLine(('== {0}: {1}' -f $r.Name, $r.Status))
        $null = $sb.AppendLine(('   commits {0} (of {1}); refs {2}; pack {3:N1} MiB; tip {4} files, {5:N1} MiB' -f $r.Commits, $r.SourceCommits,
                ($r.Refs -join ','), ($r.PackBytes / 1MB), $r.HeadFiles, ($r.HeadBytes / 1MB)))
        foreach ($t in $r.TopLevel) { $null = $sb.AppendLine(('     {0,-40} {1,5} files {2,12:N0} bytes' -f $t.Path, $t.Files, $t.Bytes)) }
        $null = $sb.AppendLine(('   removed from history: {0} forbidden path(s), {1} PE/key file(s), {2} secret value(s)' -f @($r.RemovedForbidden).Count,
                @($r.RemovedFiles).Count, $r.ReplacedValues))
        foreach ($p in (@($r.RemovedForbidden) + @($r.RemovedFiles) | Sort-Object -Unique)) { $null = $sb.AppendLine('     - ' + $p) }
        foreach ($p in @($r.SecretsBefore)) { $null = $sb.AppendLine('     secret: ' + $p) }
        $review = ($r.ReviewCounts.PSObject.Properties | ForEach-Object { '{0}={1}' -f $_.Name, $_.Value }) -join ', '
        $null = $sb.AppendLine('   review hits (not removed): ' + $review)
        $null = $sb.AppendLine(('   blobs > {0} bytes: {1}' -f $LargeBytes, @($r.LargeBlobs).Count))
        foreach ($p in @($r.LargeBlobs)) { $null = $sb.AppendLine('     ' + $p) }
        if ($r.Scrubbed) { $null = $sb.AppendLine('   history text replaced with -ReplaceTextPath (tip differences below are expected)') }
        $null = $sb.AppendLine(('   tip files identical to the source tip: {0} of {1}' -f ($r.HeadFiles - @($r.TipDifferences).Count), $r.HeadFiles))
        $linkFiles = @($r.EvidenceLinks | ForEach-Object { ($_ -split ':', 2)[0] } | Sort-Object -Unique)
        $null = $sb.AppendLine(('   links to evidence at the tip (fix in P3): {0} line(s) in {1} file(s) ({2}.evidence-links.txt)' -f @($r.EvidenceLinks).Count,
                $linkFiles.Count, $r.Name))
        $null = $sb.AppendLine(('   user profile paths at the tip: {0} line(s) ({1}.user-paths.txt)' -f @($r.TipUserPaths).Count, $r.Name))
        foreach ($p in @($r.TipUserPaths)) { $null = $sb.AppendLine('     ' + $p) }
        $null = $sb.AppendLine(('   user profile paths in history: {0} file(s)' -f @($r.HistoryUserPaths).Count))
        foreach ($p in @($r.HistoryUserPaths)) { $null = $sb.AppendLine('     ' + $p) }
        foreach ($p in @($r.TipDifferences)) { $null = $sb.AppendLine('     ' + $p) }
        foreach ($p in @($r.Problems)) { $null = $sb.AppendLine('   PROBLEM: ' + $p) }
    }
    return $sb.ToString()
}

# --- Validation -----------------------------------------------------------------------------
if (-not $SourceRepository) { $SourceRepository = Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }
if (-not $MapPath) { $MapPath = Join-Path $PSScriptRoot 'split-map.psd1' }
if ($Push -and -not $PushOwner) { throw '-Push needs -PushOwner (for example capie-mods).' }
$sourceFull = Get-SplitFullPath -Path $SourceRepository
$rootFull = Get-SplitFullPath -Path $WorkRoot
if ($rootFull.StartsWith($sourceFull, [StringComparison]::OrdinalIgnoreCase) -or
    $sourceFull.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase)) {
    throw "WorkRoot '$rootFull' and the source '$sourceFull' must not contain each other."
}
if (-not (Test-Path -LiteralPath (Join-Path $sourceFull '.git'))) { throw "Not a Git repository: $sourceFull" }
foreach ($tool in @('git', 'uv', $Python)) {
    if (-not (Get-Command -Name $tool -ErrorAction SilentlyContinue)) { throw "Required program not found: $tool" }
}
$map = Import-PowerShellDataFile -LiteralPath $MapPath
$names = if ($Repository.Count -gt 0) { $Repository } else { @($map.Order) }
foreach ($name in $names) { if (-not $map.Repositories.ContainsKey($name)) { throw "Unknown repository '$name' (not in $MapPath)." } }

$options = [pscustomobject]@{
    Branch               = $Branch
    StripBlobsBiggerThan = $StripBlobsBiggerThan
    LargeBlobBytes       = $LargeBlobBytes
    Python               = $Python
    ReplaceTextPath      = $(if ($ReplaceTextPath) { (Resolve-Path -LiteralPath $ReplaceTextPath).Path } else { '' })
}
$root = $rootFull.TrimEnd([IO.Path]::DirectorySeparatorChar)
$null = New-Item -ItemType Directory -Path $root -Force
foreach ($name in (@($names) + @('_source', '_work'))) {
    $target = Join-Path $root $name
    if (Test-Path -LiteralPath $target) {
        if (-not $Force) { throw "$target exists. Use -Force to replace it." }
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}
$null = New-Item -ItemType Directory -Path (Join-Path $root '_work') -Force
$source = $sourceFull.TrimEnd([IO.Path]::DirectorySeparatorChar)
$previousEncoding = [Console]::OutputEncoding
[Console]::OutputEncoding = $script:Utf8NoBom
try {
    # --- Source snapshot and coverage of the map ---------------------------------------------
    $work = Join-Path $root '_work'
    $log = Join-Path $work 'source-log.txt'
    $forbiddenFile = Join-Path $work 'forbidden.txt'
    # ADR-0034: archive-only paths (docs/evidence and documents moved into it) are removed like
    # forbidden paths and count as assigned in the coverage check.
    Write-SplitTextFile -Path $forbiddenFile -Line (@($map.Forbidden) + @($map.ArchiveOnly))
    $sourceClone = Join-Path $root '_source'
    Write-SplitInfo -Message ('[_source] clone {0} ({1}) for the coverage check' -f $source, $Branch)
    $null = Invoke-SplitNative -FilePath 'git' -LogPath $log -ArgumentList @('clone', '--no-local', '--single-branch', '--branch', $Branch, '--',
        $source, $sourceClone)
    $assignedFiles = @($forbiddenFile)
    foreach ($name in @($map.Order)) {
        $file = Join-Path $work ('assigned-' + $name + '.txt')
        Write-SplitTextFile -Path $file -Line (Get-SplitPathLine -Definition $map.Repositories[$name])
        $assignedFiles += $file
    }
    if (@($map.IgnoreUnassigned).Count -gt 0) {
        $ignoreFile = Join-Path $work 'ignore-unassigned.txt'
        Write-SplitTextFile -Path $ignoreFile -Line @($map.IgnoreUnassigned)
        $assignedFiles += $ignoreFile
    }
    $sourceScan = Invoke-SplitScan -Directory $sourceClone -ReportPath (Join-Path $work 'scan-source.json') -ForbiddenPath $forbiddenFile `
        -Assigned $assignedFiles -LogPath $log -Options $options
    $sourceStats = Get-SplitStatistic -Directory $sourceClone -FileListPath (Join-Path $work 'source.files.txt')
    $sourceTree = Get-SplitTree -Directory $sourceClone
    $sourceInfo = [pscustomobject]@{
        Path      = $source
        Branch    = $Branch
        Commit    = @(Invoke-SplitGit -Directory $sourceClone -ArgumentList @('rev-parse', 'HEAD'))[0]
        Commits   = $sourceStats.Commits
        PackBytes = $sourceStats.PackBytes
    }
    $unassigned = @($sourceScan.unassigned_paths)
    Write-SplitInfo -Message ('[_source] {0} commits, {1} unassigned history path(s)' -f $sourceInfo.Commits, $unassigned.Count)

    # --- Split ---------------------------------------------------------------------------------
    $results = foreach ($name in $names) {
        New-SplitRepository -Name $name -Definition $map.Repositories[$name] -Source $source -Root $root -ForbiddenFile $forbiddenFile `
            -SourceCommits $sourceInfo.Commits -Options $options -SourceTree $sourceTree
    }
    $results = @($results)

    $report = Format-SplitReport -Result $results -Source $sourceInfo -Unassigned $unassigned -LargeBytes $LargeBlobBytes
    [IO.File]::WriteAllText((Join-Path $root 'report.txt'), $report, $script:Utf8NoBom)
    $json = [pscustomobject]@{ Source = $sourceInfo; Unassigned = $unassigned; Repositories = $results } | ConvertTo-Json -Depth 6
    [IO.File]::WriteAllText((Join-Path $root 'report.json'), $json, $script:Utf8NoBom)
    Write-SplitInfo -Message $report

    # --- Optional push -------------------------------------------------------------------------
    if ($Push) {
        $failed = @($results | Where-Object { $_.Status -ne 'OK' })
        if ($failed.Count -gt 0 -or $unassigned.Count -gt 0) {
            throw ('Push refused: {0} repository(ies) failed checks, {1} unassigned path(s).' -f $failed.Count, $unassigned.Count)
        }
        foreach ($r in $results) { Publish-SplitRepository -Result $r -Url ($PushUrlTemplate -f $PushOwner, $r.Name) }
    } else {
        Write-SplitInfo -Message ('Nothing pushed (no -Push). Repositories are in {0}' -f $root)
    }
    $results
} finally {
    [Console]::OutputEncoding = $previousEncoding
}
