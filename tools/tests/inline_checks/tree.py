"""Helpers for the ``(key, operator, value)`` parse trees of the borrowed parser."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from inline_checks.constants import MOD
from inline_checks.fixtures import parse
from modgen.features.cooldown import COOLDOWN_DAYS
from rncommon.hashing import sha256_file

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def sha(path: Path) -> str:
    """Return the upper-case SHA-256 of a text file with CRLF folded to LF.

    Args:
        path: File to hash.

    Returns:
        Hex digest.
    """
    return sha256_file(path, upper=True, fold_crlf=True)


def get(nodes: list[Any], key: str) -> Any:  # noqa: ANN401 - untyped parse-tree value
    """Return the value of the only node with this key.

    Args:
        nodes: Parse-tree nodes ``(key, operator, value)``.
        key: Key to look up.

    Returns:
        The node value (a string or a nested node list).
    """
    found = [v for k, _, v in nodes if k == key]
    assert len(found) == 1, ("expected singleton", key, len(found))
    return found[0]


def walk(nodes: list[Any]) -> Iterator[Any]:
    """Yield every node of a parse tree, depth first.

    Args:
        nodes: Parse-tree nodes.

    Yields:
        Each ``(key, operator, value)`` node.
    """
    for node in nodes:
        yield node
        if isinstance(node[2], list):
            yield from walk(node[2])


def tokens(nodes: list[Any]) -> set[str]:
    """Return every string value in a parse tree.

    Args:
        nodes: Parse-tree nodes.

    Returns:
        The set of string values.
    """
    return {v for _, _, v in walk(nodes) if isinstance(v, str)}


def named(nodes: list[Any]) -> dict[str, Any]:
    """Map every GUI element name to its node list.

    Args:
        nodes: Parsed GUI tree.

    Returns:
        Element name to element body.
    """
    return {
        get(v, "name"): v
        for _, _, v in walk(nodes)
        if isinstance(v, list) and any(k == "name" for k, _, _ in v)
    }


def then(nodes: list[Any]) -> list[Any]:
    """Return the nodes of a block without its ``limit``.

    Args:
        nodes: Body of an ``if`` block.

    Returns:
        Every node except ``limit``.
    """
    return [n for n in nodes if n[0] != "limit"]


def success_if(nodes: list[Any]) -> list[Any]:
    """Return the body of the first ``if`` that requires a zero error code.

    Args:
        nodes: Effect body.

    Returns:
        The ``if`` body without its ``limit``.
    """
    out = next(value for key, _, value in nodes if key == "if")
    assert get(get(out, "limit"), "check_variable") in (
        [("temp_var:rn_pair_err", "=", "0")],
        [("temp_var:rn_ip_leader_error", "=", "0")],
    ), "unguarded success branch"
    return then(out)


def declarations(folder: Path, pattern: str = "*.txt") -> dict[str, Any]:
    """Parse every top-level declaration of the matching script files.

    The ``@RN_COOLDOWN_DAYS@`` token of the source is replaced exactly as
    ``tools/gen.py`` does it.

    Args:
        folder: Folder to read.
        pattern: Glob pattern of the files.

    Returns:
        Declaration name to body.
    """
    result: dict[str, Any] = {}
    for path in sorted(folder.glob(pattern)):
        text = path.read_text(encoding="utf-8-sig").replace(
            "@RN_COOLDOWN_DAYS@", str(COOLDOWN_DAYS)
        )
        for name, _, body in parse(text):
            assert name not in result, ("duplicate declaration", name, path)
            result[name] = body
    return result


def models_of(folder: Path, pattern: str = "*.txt") -> dict[str, Any]:
    """Parse every scripted GUI model of the matching files.

    Args:
        folder: ``common/scripted_guis`` folder.
        pattern: Glob pattern of the files.

    Returns:
        Model name to model body.
    """
    return {
        name: body
        for path in sorted(folder.glob(pattern))
        for _, _, outer in parse(path.read_text(encoding="utf-8-sig"))
        for name, _, body in outer
    }


def legacy(folder: str) -> dict[str, Any]:
    """Parse the declarations of the legacy generated ``rename_anything_*`` files.

    Args:
        folder: Folder relative to ``mod/``.

    Returns:
        Declaration name to body.
    """
    return declarations(MOD / folder, "rename_anything_*.txt")


def xy(node: list[Any], key: str = "position") -> tuple[int, int]:
    """Return the two numbers of a ``position`` or ``size`` block.

    Args:
        node: GUI element body.
        key: ``position`` or ``size``.

    Returns:
        ``(x, y)`` or ``(width, height)``.
    """
    values = {k: v for k, _, v in get(node, key)}
    return int(values.get("x", values.get("width"))), int(values.get("y", values.get("height")))


def set_value(node: list[Any], key: str, value: Any) -> None:  # noqa: ANN401 - parse-tree value
    """Replace the value of one key in an element body, in place.

    Args:
        node: Element body.
        key: Key to replace.
        value: New value.
    """
    node[:] = [(k, op, value if k == key else v) for k, op, v in node]
