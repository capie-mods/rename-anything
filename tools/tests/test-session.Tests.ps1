<#
.SYNOPSIS
    Offline Pester 3.4 unit tests for the pure functions and the process adapter of tools/test-session.ps1.

.DESCRIPTION
    Dot-sources the script (which then only defines functions) and works on strings or
    in $env:RA_TEST_SESSION_TEST_ROOT (default %TEMP%\ra-test-session-tests). The real
    HOI4 user folder is never touched. The Begin/Restore round trip on real files is
    covered by tools/tests/test-session-fixture.ps1.
        Invoke-Pester -Script .\tools\tests\test-session.Tests.ps1
#>

$scriptUnderTest = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) 'test-session.ps1'
. $scriptUnderTest -Action Restore
Set-StrictMode -Version Latest
$workRoot = if ($env:RA_TEST_SESSION_TEST_ROOT) { $env:RA_TEST_SESSION_TEST_ROOT } else { Join-Path ([IO.Path]::GetTempPath()) 'ra-test-session-tests' }

Describe 'test-session.ps1 pure functions' {
    It 'Set-PdxSettingValue replaces exactly one block value and keeps the rest' {
        $text = "`"System`"={`n `"language`"={ value=`"l_english`" version=0 }`n `"other`"={ value=`"keep`" version=8 }`n}`n"
        $r = Set-PdxSettingValue -Text $text -Setting 'language' -Value 'l_polish'
        $r | Should Be $text.Replace('l_english', 'l_polish')
    }
    It 'Set-PdxSettingValue refuses a missing or duplicated setting' {
        $threw = $false
        try { [void](Set-PdxSettingValue -Text '"x"={ value="1" }' -Setting 'language' -Value 'l_polish') } catch {
            $threw = $_.Exception.Message -match 'found 0'
        }
        $threw | Should Be $true
        $dup = '"language"={ value="a" } "language"={ value="b" }'
        $threw = $false
        try { [void](Set-PdxSettingValue -Text $dup -Setting 'language' -Value 'l_polish') } catch { $threw = $_.Exception.Message -match 'found 2' }
        $threw | Should Be $true
    }
    It 'Set-TsLegacySetting switches language, size and window mode' {
        $text = "language=`"l_english`"`ngraphics={`n size={ x=3440 y=1440 }`n fullScreen=yes`n borderless=yes`n}`n"
        $r = Set-TsLegacySetting -Text $text -GameLanguage 'polish'
        $r | Should Be "language=`"l_polish`"`ngraphics={`n size={ x=1720 y=900 }`n fullScreen=no`n borderless=no`n}`n"
    }
    It 'Set-TsModernSetting sets language, windowed_resolution and display_mode' {
        $text = @(
            "`"language`"={ value=`"l_english`" version=0 }`n",
            "`"windowed_resolution`"={ value=`"3440x1440`" version=0 }`n",
            "`"display_mode`"={ value=`"fullscreen`" version=0 }`n"
        ) -join ''
        $r = Set-TsModernSetting -Text $text -GameLanguage 'english'
        $r | Should Match 'value="1720x900"'
        $r | Should Match '"display_mode"=\{ value="windowed"'
        $r | Should Match 'value="l_english"'
    }
}

Describe 'test-session.ps1 adapters and recovery' {
    It 'process adapter: a running game blocks every action' {
        $saved = $script:TsGetGameProcess
        try {
            $script:TsGetGameProcess = { @('fake-hoi4') }
            $threw = $false
            try { Assert-TsGameClosed } catch { $threw = $_.Exception.Message -match 'Close HOI4' }
            $threw | Should Be $true
            $script:TsGetGameProcess = { @() }
            Assert-TsGameClosed
        } finally { $script:TsGetGameProcess = $saved }
    }
    It 'Restore-TsSession checks every backup before changing anything' {
        $dir = Join-Path $workRoot 'restore-check'
        if (Test-Path $dir) { Remove-Item -LiteralPath $dir -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        $a = Join-Path $dir 'a.txt'
        $b = Join-Path $dir 'b.txt'
        Set-Content -LiteralPath $a -Value 'changed-a'
        Set-Content -LiteralPath $b -Value 'changed-b'
        Set-Content -LiteralPath "$a.impl_backup" -Value 'orig-a'
        Set-Content -LiteralPath "$b.impl_backup" -Value 'tampered'
        $files = @(
            [pscustomobject]@{ path = $a; backup = "$a.impl_backup"; sha256 = (Get-TsFileSha256 -Path "$a.impl_backup") },
            [pscustomobject]@{ path = $b; backup = "$b.impl_backup"; sha256 = ('0' * 64) }
        )
        $manifest = Join-Path $dir 'rename_anything_test_session.json'
        @{ files = $files } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifest
        $threw = $false
        try { [void](Restore-TsSession -ManifestPath $manifest) } catch { $threw = $_.Exception.Message -match 'Backup hash mismatch' }
        $threw | Should Be $true
        (Get-Content -LiteralPath $a) | Should Be 'changed-a'
        Test-Path -LiteralPath $manifest | Should Be $true
    }
}
