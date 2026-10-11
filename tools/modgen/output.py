"""Where generated files go: the ``OutputSink`` protocol and its two adapters.

The slices only build text; :mod:`modgen.build` hands every file to an
``OutputSink``. Two adapters exist, which is why this is a protocol rather than
a plain function:

* :class:`DiskSink` writes below a folder (``mod/`` in production).
* :class:`MemorySink` keeps the encoded bytes in a dictionary. The unit tests use
  it to compare whole generator runs without touching ``mod/``, and a dry run
  can use it to diff the output before writing.

Both adapters encode the same way, through :func:`encode_text`: UTF-8, LF line
endings, and a byte order mark for localisation files.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from rncommon.loc_files import UTF8_BOM

if TYPE_CHECKING:
    from pathlib import Path


def encode_text(text: str, *, bom: bool = False) -> bytes:
    """Encode a generated text file.

    Args:
        text: File contents. Any CRLF is turned into LF first.
        bom: Prefix the bytes with a UTF-8 byte order mark.

    Returns:
        The file contents as written to disk.
    """
    data = text.replace("\r\n", "\n").encode("utf-8")
    return UTF8_BOM + data if bom else data


class OutputSink(Protocol):
    """Destination of the generated files; paths are relative to the mod root."""

    def write_text(self, relative: str, text: str, *, bom: bool = False) -> None:
        """Store one text file encoded with :func:`encode_text`.

        Args:
            relative: POSIX path relative to the mod root.
            text: File contents.
            bom: Prefix the file with a UTF-8 byte order mark.
        """
        ...

    def write_bytes(self, relative: str, data: bytes) -> None:
        """Store one binary file unchanged.

        Args:
            relative: POSIX path relative to the mod root.
            data: File contents.
        """
        ...


class DiskSink:
    """:class:`OutputSink` adapter that writes below a folder, creating parents."""

    def __init__(self, root: Path) -> None:
        """Create the adapter.

        Args:
            root: Folder that receives the files (``mod/``).
        """
        self.root = root

    def write_text(self, relative: str, text: str, *, bom: bool = False) -> None:
        """Write one text file as UTF-8 with LF line endings.

        Args:
            relative: POSIX path relative to :attr:`root`.
            text: File contents.
            bom: Prefix the file with a UTF-8 byte order mark.
        """
        self.write_bytes(relative, encode_text(text, bom=bom))

    def write_bytes(self, relative: str, data: bytes) -> None:
        """Write one file, creating missing parent folders.

        Args:
            relative: POSIX path relative to :attr:`root`.
            data: File contents.
        """
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


class MemorySink:
    """:class:`OutputSink` adapter that keeps every file in :attr:`files`."""

    def __init__(self) -> None:
        """Create an empty sink."""
        self.files: dict[str, bytes] = {}

    def write_text(self, relative: str, text: str, *, bom: bool = False) -> None:
        """Store one encoded text file.

        Args:
            relative: POSIX path relative to the mod root.
            text: File contents.
            bom: Prefix the file with a UTF-8 byte order mark.
        """
        self.write_bytes(relative, encode_text(text, bom=bom))

    def write_bytes(self, relative: str, data: bytes) -> None:
        """Store one file; a later write to the same path replaces it.

        Args:
            relative: POSIX path relative to the mod root.
            data: File contents.
        """
        self.files[relative] = data
