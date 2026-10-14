# Path map for tools/repo-split/split.ps1: which monorepo paths go into which new repository.
#
# Syntax of every entry is the syntax of "git filter-repo --paths-from-file":
#   plain text     a file, or a directory when it ends with "/" (also matches without it)
#   glob:PATTERN   fnmatch over the full path ("*" also matches "/")
#   regex:PATTERN  Python regular expression, searched in the full path (anchor it with ^ and $)
# Renames are "OLD==>NEW"; split.ps1 writes them after all filters, so filters see the old names.
#
# A path may be listed for more than one repository. Its history is then kept in each of them
# (used for the root tool configuration and for documents that cover both products).
# Documents moved by the docs/ reorganisation of 2026-10-14 are listed under their old and
# their new names, so the history before and after the move stays in the same repository.
#
# ADR-0034: no new repository gets docs/evidence. The evidence archive, and the old-path
# history of documents that now live only in docs/evidence (notes, handoffs, plans, logs),
# stay in the archived monorepo. ArchiveOnly lists them; split.ps1 removes them from every
# new repository (like Forbidden) and counts them as assigned in the coverage check.
#
# Expect lists files that must exist at the tip of the new branch; split.ps1 fails otherwise.
# Forbidden lists paths that are removed from the history of every new repository
# (build output, binaries, caches, key files), on top of the content scan in scan_history.py.
@{
    # Processing and report order (a data file cannot hold an ordered dictionary).
    Order        = @('capie', 'capie-script-sdk', 'capie-design', 'rename-anything')

    Repositories = @{

        'capie'            = @{
            Description = 'CAPIE (Cyprian''s API Extender): native DLLs, proxy loader, launcher, bootstrap installer, CAPIE site and documentation.'
            Topics      = @('hearts-of-iron-iv', 'hoi4', 'hoi4-mod', 'modding', 'cpp', 'windows', 'dll', 'capie')
            Paths       = @(
                # Native code: CAPIE (plugin/capie, incl. src/proxy), the legacy country DLL
                # (plugin/src), the reviewed launcher candidate (plugin/launcher), the native
                # bridges and their tests (plugin/probes), build module and MinHook licence.
                'plugin/'
                # Installer of CAPIE (proxy version.dll or launcher) and the live proxy test.
                'tools/bootstrap/'
                'tools/test-proxy-loader.ps1'
                # Audits plugin/probes/inline_editor_debug_bridge.cpp and its build output.
                'tools/audit-debug-bridge.py'
                # PowerShell and Python lint used by the build scripts (copied to every repo that needs it).
                'tools/lint-powershell.ps1'
                'tools/lint/'
                'tools/check_constant_docstrings.py'
                'PSScriptAnalyzerSettings.psd1'
                # Ghidra decompilation script used for the RE notes of hoi4.exe.
                'probes/ghidra/'
                # Documentation site of CAPIE.
                'sites/capie/'
                # Root tool configuration (rewritten for the new repository after the split).
                '.gitignore'
                '.gitattributes'
                '.python-version'
                'pyproject.toml'
                'uv.lock'
                # Current documentation (docs/ after the reorganisation of 2026-10-14, commit 80136ae).
                # The index, the ADR register, the contributor guides and the RE notes cover both
                # products; both repositories keep them and each trims its copy (plan.txt, P3).
                'docs/README.md'
                'docs/adr/'
                'docs/contributing/'
                'docs/research/'
                'docs/API-DECISIONS.md'
                'docs/DISTRIBUTION-DECISIONS.md'
                # The same documents under their names before the reorganisation.
                'docs/proxy-loader.md'
                'docs/country-re-findings.md'
                'docs/naming-signatures.json'
                'docs/state-view-internals.md'
                'docs/typed-state-variable-findings.md'
            )
            Renames     = @()
            Expect      = @('plugin/capie/CONTRACT.md', 'plugin/capie/build.ps1', 'plugin/capie/src/proxy/proxy_main.cpp',
                'tools/bootstrap/install.ps1', 'sites/capie/zensical.toml')
        }

        'capie-script-sdk' = @{
            Description = 'CAPIE Script SDK: generated HOI4 script helpers for mods that use CAPIE (separate Workshop item).'
            Topics      = @('hearts-of-iron-iv', 'hoi4', 'hoi4-mod', 'modding', 'paradox-script', 'capie')
            Paths       = @(
                'sdk/capie-script-sdk/'
                'tools/check_constant_docstrings.py'
                '.gitignore'
                '.python-version'
                'pyproject.toml'
                'uv.lock'
            )
            # The SDK folder becomes the repository root (its README.md, mod/, tools/, tests/).
            Renames     = @('sdk/capie-script-sdk/==>')
            Expect      = @('README.md', 'tools/gen_sdk.py', 'tools/capie_charset.py', 'tests/test_sdk.py',
                'mod/common/scripted_effects/capie_sdk_v1_effects.txt')
        }

        'capie-design'     = @{
            Description = 'Shared design system of CAPIE and Rename Anything: tokens, rules, marks, diagrams, site theme and Paradox script lexer.'
            Topics      = @('design-system', 'design-tokens', 'zensical', 'pygments', 'capie')
            Paths       = @(
                'docs/design/'
                'docs/assets/'
                'sites/shared/'
                'sites/README.md'
                '.impeccable.md'
                'tools/check_constant_docstrings.py'
                '.gitignore'
                '.python-version'
                'pyproject.toml'
                'uv.lock'
            )
            Renames     = @()
            Expect      = @('docs/design/DESIGN-SYSTEM.md', 'docs/design/tokens.json', 'sites/shared/sync_shared.py',
                'sites/shared/theme/stylesheets/tokens.css')
        }

        'rename-anything'  = @{
            Description = 'Rename Anything: HOI4 mod to rename countries, leaders, parties, states and cities in game, built on CAPIE.'
            Topics      = @('hearts-of-iron-iv', 'hoi4', 'hoi4-mod', 'modding', 'paradox-script', 'rename-anything')
            Paths       = @(
                'mod/'
                'descriptor.mod'
                # Generator, checks and tests of the mod. tools/bootstrap/, tools/test-proxy-loader.ps1
                # and tools/audit-debug-bridge.py belong to CAPIE.
                'tools/gen.py'
                'tools/check.py'
                'tools/compare-logs.py'
                'tools/test-session.ps1'
                'tools/modgen/'
                'tools/rncommon/'
                'tools/inline_editor/'
                'tools/tests/'
                'tools/repo-split/'
                'tools/lint-powershell.ps1'
                'tools/lint/'
                'tools/check_constant_docstrings.py'
                # Script probes and QA fixtures (probes/ghidra is kept in both repositories).
                'probes/'
                'sites/rename-anything/'
                'README.md'
                'docs/assets/'
                'PSScriptAnalyzerSettings.psd1'
                '.gitignore'
                '.gitattributes'
                '.python-version'
                'pyproject.toml'
                'uv.lock'
                # Current documentation (see capie above), and the same documents under their
                # names before the reorganisation of 2026-10-14.
                'docs/README.md'
                'docs/adr/'
                'docs/contributing/'
                'docs/research/'
                'docs/API-DECISIONS.md'
                'docs/country-re-findings.md'
                'docs/naming-signatures.json'
                'docs/state-view-internals.md'
                'docs/typed-state-variable-findings.md'
            )
            Renames     = @()
            Expect      = @('mod/descriptor.mod', 'tools/gen.py', 'tools/modgen/__init__.py', 'sites/rename-anything/zensical.toml', 'README.md')
        }
    }

    # Removed from the history of every new repository by an --invert-paths pass.
    Forbidden    = @(
        'glob:*.dll'
        'glob:*.exe'
        'glob:*.pdb'
        'glob:*.obj'
        'glob:*.lib'
        'glob:*.ilk'
        'glob:*.exp'
        'glob:*.idb'
        'glob:*.npz'
        'glob:*.npy'
        'glob:*.pkl'
        'glob:*.zip'
        'glob:*.7z'
        'glob:*.pfx'
        'glob:*.p12'
        'glob:*.pem'
        'glob:*.key'
        'glob:*.snk'
        'glob:*.dmp'
        'glob:*.mdmp'
        'glob:*.pyc'
        'regex:(^|/)\.env$'
        'regex:(^|/)(build|_cache|__pycache__|\.venv|\.ruff_cache|\.gstack|node_modules)/'
        'regex:^sites/[^/]+/(site|\.cache)/'
    )

    # ADR-0034: kept only in the archived monorepo; removed from every new repository.
    ArchiveOnly  = @(
        # The evidence archive (screenshots, logs, reports, decompiler output, review notes).
        'docs/evidence/'
        # Old-path history of documents that the reorganisation of 2026-10-14 moved into
        # docs/evidence (notes, handoffs, plans, decision logs, research notes, design audit).
        'regex:^docs/HANDOFF-[^/]+\.md$'
        'docs/CLAUDE-CODE-PROMPT.md'
        'docs/PROGRESS.md'
        'docs/architecture.md'
        'docs/design.md'
        'docs/in-place-editing-plan.md'
        'docs/test-report.md'
        'docs/mp-test-plan.md'
        'docs/launcher-plan.md'
        'docs/globe-reference-assessment.md'
        'regex:^docs/stage0-[^/]+\.md$'
        'docs/naming-internals.md'
        'docs/workshop-native-research.md'
        'docs/design/audit-anti-slop.md'
    )

    # Every path of the source history must be selected by at least one repository (or be
    # forbidden); split.ps1 reports the rest as unassigned, because the split would drop them.
    # Patterns listed here may stay unassigned on purpose (same syntax as above).
    IgnoreUnassigned = @()
}
