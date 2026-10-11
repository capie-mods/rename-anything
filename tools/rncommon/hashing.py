"""SHA-256 digests of files, in the spellings the evidence manifests use."""

from __future__ import annotations

import hashlib
from pathlib import Path

CRLF = b"\r\n"
"""Windows line ending, folded to :data:`LF` by ``fold_crlf``."""

LF = b"\n"
"""Unix line ending."""


def sha256_file(path: str | Path, *, upper: bool = False, fold_crlf: bool = False) -> str:
    """Return the SHA-256 hex digest of a file.

    Args:
        path: File to hash.
        upper: Return upper-case hex digits (the form the debug bridge manifests use).
        fold_crlf: Replace every CRLF with LF before hashing, so a text file hashes
            the same in a Windows and a Unix checkout.

    Returns:
        The digest as 64 hex characters.
    """
    data = Path(path).read_bytes()
    if fold_crlf:
        data = data.replace(CRLF, LF)
    digest = hashlib.sha256(data).hexdigest()
    return digest.upper() if upper else digest
