"""The borrowed ApplyVM and Paradox-script parser, and the native alphabet."""

from __future__ import annotations

import importlib.util
import re
from typing import TYPE_CHECKING

from inline_checks.constants import REPO

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType


def _load(name: str, path: Path) -> ModuleType:
    """Import a Python file by path.

    Args:
        name: Module name to register.
        path: File to import.

    Returns:
        The executed module.

    Raises:
        ImportError: The file cannot be loaded.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        msg = f"cannot load {path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VM_MODULE = _load("inline_apply_vm", REPO / "probes" / "rn_inline_pair_apply_source" / "check.py")
"""Limited ApplyVM and Paradox-script parser shared with the fixture checkers."""

parse = VM_MODULE.parse

ApplyVM = VM_MODULE.ApplyVM

Country = VM_MODULE.Country


def native_alphabet() -> str:
    """Return the characters the native encoder accepts, read from the real C++ source.

    It is read on first use, not at import, so the VM cases that need no CAPIE source (the
    colour and party ideology cases run by pytest) work without the ``plugin`` junction.

    Returns:
        The 84 characters of ``plugin/src/editor_input.hpp``.
    """
    encoder = (REPO / "plugin" / "src" / "editor_input.hpp").read_text(encoding="utf-8")
    return "".join(
        re.findall(
            r'U"([^"]*)"',
            encoder[
                encoder.index("constexpr std::u32string_view alphabet") : encoder.index(
                    "constexpr std::u32string_view delimiters"
                )
            ],
        )
    )


def __getattr__(name: str) -> str:
    """Provide ``NATIVE_ALPHABET`` lazily (PEP 562).

    Args:
        name: Attribute name.

    Returns:
        The native alphabet.

    Raises:
        AttributeError: Any other name.
    """
    if name == "NATIVE_ALPHABET":
        return native_alphabet()
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
