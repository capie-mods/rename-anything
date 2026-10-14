#!/usr/bin/env python3
"""Scan the whole history of one Git repository for content that must not be published.

Used by ``tools/repo-split/split.ps1`` after ``git filter-repo`` has cut a repository out of
the monorepo, and usable on its own on any clone. It reads every blob reachable from any ref
(``git rev-list --objects --all``) through one ``git cat-file --batch`` process and reports:

* forbidden paths: every path that ever existed and matches a pattern of the forbidden-paths
  file (the same ``glob:``/``regex:``/literal syntax ``git filter-repo --paths-from-file``
  reads, with the same matching rules);
* executable content: blobs that start with a PE header (``MZ`` ... ``PE``), whatever their name;
  their paths, and the paths of files with a private key, are listed under ``remove_paths``
  so the caller can drop those files from history;
* large blobs: blobs bigger than ``--large-bytes``;
* secrets: high-confidence token formats (private keys, GitHub, Anthropic, OpenAI, AWS,
  Slack, Google, Steam Web API) and lower-confidence review hits (generic ``password = "..."``
  assignments, SteamID64 numbers, Windows user profile paths, e-mail addresses).

Matched secret text is never printed in full; the report shows a masked excerpt. With
``--replace-out`` the exact high-confidence matches (other than private keys) are written as a
``git filter-repo --replace-text`` file (``literal==>***REMOVED***`` per line).

With ``--assigned`` (one or more paths files of the new repositories) the report also lists
``unassigned_paths``: history paths that no file selects, which a split would drop.

Usage:
    python -I tools/repo-split/scan_history.py --repo PATH --report OUT.json
        [--forbidden FILE] [--large-bytes N] [--replace-out FILE] [--assigned FILE ...]

Exit code: 0 when the scan ran (findings are in the report), 2 on a usage or Git error.
"""

from __future__ import annotations

import argparse
import fnmatch
import itertools
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

HIGH_RULES: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    (
        "private-key",
        re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY"),
    ),
    ("github-token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("github-pat", re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{50,}\b")),
    ("anthropic-key", re.compile(rb"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai-key", re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9]{32,}\b")),
    ("aws-access-key", re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(rb"\bxox[abprs]-[0-9A-Za-z-]{10,}")),
    ("google-api-key", re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("steam-web-api-key", re.compile(rb"(?i)steam\w{0,20}key\W{0,5}[0-9A-F]{32}\b")),
)
"""Token formats that are treated as real secrets: reported and written to ``--replace-out``."""

REVIEW_RULES: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    (
        "generic-assignment",
        re.compile(
            rb"(?i)\b(?:password|passwd|secret|token|api[_-]?key|client[_-]?secret)\b"
            rb"\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
        ),
    ),
    ("steamid64", re.compile(rb"\b7656119\d{10}\b")),
    (
        "user-profile-path",
        re.compile(rb"(?i)\b[A-Z]:[\\/]{1,2}Users[\\/]{1,2}[A-Za-z0-9._ -]{1,40}"),
    ),
    (
        "email",
        re.compile(rb"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"),
    ),
)
"""Patterns that need a human look; reported with counts, never removed automatically."""

WHOLE_FILE_RULES = frozenset({"private-key"})
"""Rules whose hit drops the whole file from history (a text replacement would leave the key)."""

BINARY_SNIFF_BYTES = 8000
"""Bytes inspected for a NUL character to tell binary blobs from text (Git uses the same size)."""

PE_HEADER_LIMIT = 1024
"""Highest offset at which the ``PE`` signature of a Windows executable is accepted."""

RAW_FIELDS = 5
"""Fields of a ``git log --raw`` record before the path: modes, object IDs and status."""

GITLINK_MODE = "160000"
"""Mode of a submodule entry; its object ID names a commit, not a blob."""

MAX_HITS_PER_RULE = 50
"""Detailed hits kept per review rule in the report; the count is always complete."""

DEFAULT_LARGE_BYTES = 1024 * 1024
"""Default threshold of ``--large-bytes``: blobs above 1 MiB are listed."""

REPLACEMENT = b"***REMOVED***"
"""Text that ``git filter-repo --replace-text`` writes in place of a high-confidence secret."""


@dataclass
class Hit:
    """One pattern match inside one blob."""

    rule: str
    """Name of the rule that matched."""
    blob: str
    """Object ID of the blob."""
    path: str
    """A path under which the blob was reachable."""
    excerpt: str
    """Masked excerpt of the match; never the full secret."""


def git(repo: Path, *args: str) -> bytes:
    """Run one Git command in ``repo`` and return its standard output.

    Args:
        repo: Repository working tree or bare directory.
        *args: Git arguments after ``git -C repo``.

    Returns:
        The raw standard output.

    Raises:
        SystemExit: When Git exits with a non-zero code.
    """
    result = subprocess.run(  # noqa: S603 - fixed executable, arguments built by this script
        ["git", "-C", str(repo), *args],  # noqa: S607 - Git is resolved from PATH on purpose
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        text = f"git {' '.join(args)} failed: {message}"
        raise SystemExit(text)
    return result.stdout


def load_patterns(path: Path | None) -> list[tuple[str, str]]:
    """Read a ``git filter-repo --paths-from-file`` style file.

    Args:
        path: The file, or None for no patterns.

    Returns:
        ``(kind, expression)`` pairs; kind is ``literal``, ``glob`` or ``regex``. Rename
        lines (``OLD==>NEW``) select nothing in ``git filter-repo`` and are skipped.
    """
    if path is None:
        return []
    patterns: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "==>" in line:
            continue
        for kind in ("glob", "regex", "literal"):
            if line.startswith(kind + ":"):
                patterns.append((kind, line[len(kind) + 1 :]))
                break
        else:
            patterns.append(("literal", line))
    return patterns


def path_matches(kind: str, expression: str, path: str) -> bool:
    """Match one path the way ``git filter-repo`` does.

    Args:
        kind: ``literal``, ``glob`` or ``regex``.
        expression: The pattern text.
        path: Repository-relative path with forward slashes.

    Returns:
        True when the pattern selects the path.
    """
    if kind == "regex":
        return re.search(expression, path) is not None
    if kind == "glob":
        if fnmatch.fnmatch(path, expression):
            return True
        if not expression.endswith("*"):
            suffix = "*" if expression.endswith("/") else "/*"
            return fnmatch.fnmatch(path, expression + suffix)
        return False
    prefix = expression.rstrip("/")
    return path == prefix or path.startswith(prefix + "/")


def mask(data: bytes) -> str:
    """Return a masked, printable excerpt of a match.

    Args:
        data: The matched bytes.

    Returns:
        The first six characters followed by ``...`` and the length.
    """
    text = data.decode("utf-8", "replace").replace("\n", " ")
    return f"{text[:6]}...({len(text)} chars)"


def is_pe(blob: bytes) -> bool:
    r"""Tell whether a blob is a Windows PE executable (DLL, EXE, SYS).

    Args:
        blob: Blob content.

    Returns:
        True when the DOS header points at a ``PE\0\0`` signature.
    """
    if len(blob) < 64 or blob[:2] != b"MZ":  # noqa: PLR2004 - size of the DOS header
        return False
    offset = int.from_bytes(blob[60:64], "little")
    return 0 < offset <= PE_HEADER_LIMIT and blob[offset : offset + 4] == b"PE\0\0"


def reachable_blobs(repo: Path) -> dict[str, list[str]]:
    """List every blob reachable from any ref with every path it was committed under.

    The same content can sit under several names (a ``.dll`` and a renamed copy share one
    blob), so all paths are kept; removing only the first would leave the others in history.

    Args:
        repo: Repository to read.

    Returns:
        Mapping of blob object ID to its sorted paths.
    """
    output = git(repo, "log", "--all", "--no-renames", "--raw", "--no-abbrev", "--format=", "-z")
    tokens = output.decode("utf-8", "replace").split("\0")
    paths: dict[str, set[str]] = {}
    for meta, path in itertools.pairwise(tokens):
        fields = meta.lstrip("\n").split()
        if len(fields) < RAW_FIELDS or not fields[0].startswith(":") or fields[1] == GITLINK_MODE:
            continue
        sha = fields[3]
        if sha.strip("0"):
            paths.setdefault(sha, set()).add(path)
    return {sha: sorted(names) for sha, names in paths.items()}


def all_paths(repo: Path) -> list[str]:
    """List every path that was added or changed in any commit of any ref.

    Args:
        repo: Repository to read.

    Returns:
        Sorted unique paths.
    """
    output = git(repo, "log", "--all", "--name-only", "--format=", "-z", "--no-renames")
    return sorted({p for p in output.decode("utf-8", "replace").split("\0") if p.strip()})


def read_blobs(repo: Path, shas: list[str]) -> dict[str, bytes]:
    """Read many blobs through one ``git cat-file --batch`` process.

    Args:
        repo: Repository to read.
        shas: Object IDs to read.

    Returns:
        Mapping of object ID to content.
    """
    result = subprocess.run(  # noqa: S603 - fixed executable, arguments built by this script
        ["git", "-C", str(repo), "cat-file", "--batch"],  # noqa: S607 - Git from PATH
        input=("\n".join(shas) + "\n").encode("ascii"),
        capture_output=True,
        check=True,
    )
    data = result.stdout
    contents: dict[str, bytes] = {}
    position = 0
    while position < len(data):
        end = data.index(b"\n", position)
        header = data[position:end].decode("ascii").split()
        size = int(header[2])
        contents[header[0]] = data[end + 1 : end + 1 + size]
        position = end + 1 + size + 1
    return contents


@dataclass
class Findings:
    """Findings collected while the blobs are read."""

    large: list[dict[str, object]] = field(default_factory=list)
    """Blobs above the size threshold."""
    executables: list[dict[str, object]] = field(default_factory=list)
    """Blobs with a Windows PE header."""
    high: list[Hit] = field(default_factory=list)
    """High-confidence secret hits."""
    review: list[Hit] = field(default_factory=list)
    """Review hits, at most ``MAX_HITS_PER_RULE`` per rule."""
    review_counts: dict[str, int] = field(default_factory=dict)
    """Number of review hits per rule."""
    review_paths: dict[str, dict[str, int]] = field(default_factory=dict)
    """Number of review hits per rule and path (every path, not sampled)."""
    secrets: set[bytes] = field(default_factory=set)
    """Exact high-confidence matches that a text replacement can remove."""
    remove_paths: set[str] = field(default_factory=set)
    """Paths whose files must leave history as a whole."""

    def add_blob(self, sha: str, names: list[str], blob: bytes, large_bytes: int) -> None:
        """Inspect one blob and record what it contains.

        Args:
            sha: Object ID of the blob.
            names: Every path the blob was committed under (at least one).
            blob: Blob content.
            large_bytes: Size above which the blob is listed as large.
        """
        path = names[0]
        if len(blob) > large_bytes:
            self.large.append({"blob": sha, "path": path, "bytes": len(blob)})
        if is_pe(blob):
            self.executables.append({"blob": sha, "path": ", ".join(names), "bytes": len(blob)})
            self.remove_paths.update(names)
            return
        if b"\0" in blob[:BINARY_SNIFF_BYTES]:
            return
        for name, pattern in HIGH_RULES:
            for match in pattern.finditer(blob):
                self.high.append(Hit(name, sha, path, mask(match.group(0))))
                if name in WHOLE_FILE_RULES:
                    self.remove_paths.update(names)
                else:
                    self.secrets.add(match.group(0))
        for name, pattern in REVIEW_RULES:
            for match in pattern.finditer(blob):
                self.review_counts[name] = self.review_counts.get(name, 0) + 1
                per_path = self.review_paths.setdefault(name, {})
                per_path[path] = per_path.get(path, 0) + 1
                if self.review_counts[name] <= MAX_HITS_PER_RULE:
                    self.review.append(Hit(name, sha, path, mask(match.group(0))))


@dataclass
class ScanResult:
    """Outcome of :func:`scan`."""

    report: dict[str, object]
    """JSON-serialisable report (without secret values)."""
    secrets: list[bytes]
    """Exact high-confidence matches, for the ``--replace-text`` file only."""
    summary: str
    """One-line summary printed on standard output."""


def scan(repo: Path, forbidden: list[tuple[str, str]], large_bytes: int) -> ScanResult:
    """Scan one repository's whole history.

    Args:
        repo: Repository to read.
        forbidden: Forbidden path patterns from :func:`load_patterns`.
        large_bytes: Size above which a blob is listed as large.

    Returns:
        The report, the secret values and a summary line.
    """
    blob_paths = reachable_blobs(repo)
    contents = read_blobs(repo, sorted(blob_paths))
    paths = all_paths(repo)
    forbidden_hits = sorted(p for p in paths if any(path_matches(k, e, p) for k, e in forbidden))
    found = Findings()
    for sha, blob in contents.items():
        found.add_blob(sha, blob_paths[sha], blob, large_bytes)
    found.large.sort(key=lambda item: -int(str(item["bytes"])))
    report: dict[str, object] = {
        "repo": str(repo),
        "blobs": len(contents),
        "blob_bytes": sum(len(b) for b in contents.values()),
        "paths_in_history": len(paths),
        "forbidden_paths": forbidden_hits,
        "executables": found.executables,
        "large_blobs": found.large,
        "secrets_high": [asdict(h) for h in found.high],
        "review_counts": {name: found.review_counts.get(name, 0) for name, _ in REVIEW_RULES},
        "review_paths": {
            name: dict(sorted(found.review_paths.get(name, {}).items())) for name, _ in REVIEW_RULES
        },
        "review_samples": [asdict(h) for h in found.review],
        "remove_paths": sorted(found.remove_paths),
    }
    summary = (
        f"blobs={len(contents)} forbidden={len(forbidden_hits)} "
        f"executables={len(found.executables)} large={len(found.large)} "
        f"secrets_high={len(found.high)} remove_paths={len(found.remove_paths)}"
    )
    return ScanResult(report, sorted(found.secrets), summary)


def main(argv: list[str]) -> int:
    """Parse arguments, scan, and write the report.

    Args:
        argv: Command-line arguments without the program name.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--forbidden", type=Path, default=None)
    parser.add_argument("--large-bytes", type=int, default=DEFAULT_LARGE_BYTES)
    parser.add_argument("--replace-out", type=Path, default=None)
    parser.add_argument("--assigned", type=Path, nargs="+", default=None)
    args = parser.parse_args(argv)
    if not (args.repo / ".git").exists() and not (args.repo / "HEAD").exists():
        print(f"not a Git repository: {args.repo}", file=sys.stderr)
        return 2
    result = scan(args.repo, load_patterns(args.forbidden), args.large_bytes)
    if args.assigned is not None:
        assigned = [pattern for file in args.assigned for pattern in load_patterns(file)]
        result.report["unassigned_paths"] = [
            path
            for path in all_paths(args.repo)
            if not any(path_matches(kind, expression, path) for kind, expression in assigned)
        ]
    if args.replace_out is not None:
        lines = [value + b"==>" + REPLACEMENT + b"\n" for value in result.secrets]
        args.replace_out.write_bytes(b"".join(lines))
    args.report.write_text(json.dumps(result.report, indent=2), encoding="utf-8")
    print(result.summary)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
