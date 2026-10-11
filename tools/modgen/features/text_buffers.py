"""Name buffers: code arrays rendered back to text through scripted localisation.

A typed name lives in a country array of character codes plus a length
variable. ``RN_<prefix>_<slot>`` is a ``defined_text`` per slot that prints the
character of that slot, or nothing past the stored length. Concatenating all
:data:`~modgen.common.MAXLEN` slots (:func:`modgen.common.slots_expr`) gives the
whole name, which ``meta_effect`` then turns into a literal string.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from modgen.charset import DISPLAY_ORDER, char_key
from modgen.common import EMPTY_LOC_KEY, MAXLEN
from modgen.script import check_variable, defined_text

if TYPE_CHECKING:
    from collections.abc import Iterable


class NameBuffer(NamedTuple):
    """One name buffer: scripted loc prefix, code array and length variable."""

    prefix: str
    """Scripted localisation prefix (``RN_<prefix>_<slot>``)."""

    array: str
    """Country array holding the character codes."""

    length: str
    """Country variable holding the number of used slots."""


INPUT_BUFFER = NameBuffer("B", "rn_buf", "rn_len")
"""The input window's buffer (what the player is typing)."""

COUNTRY_NAME_BUFFER = NameBuffer("N", "rn_cname", "rn_cname_len")
"""Country name typed on the Country tab."""

COUNTRY_ADJ_BUFFER = NameBuffer("J", "rn_cadj", "rn_cadj_len")
"""Country adjective typed on the Country tab."""

BUFFERS = [INPUT_BUFFER, COUNTRY_NAME_BUFFER, COUNTRY_ADJ_BUFFER]
"""The three name buffers, in the order their tables are written."""


def slot_tables(buffers: Iterable[NameBuffer]) -> str:
    """Return the ``RN_<prefix>_<slot>`` tables of every buffer.

    Each slot prints nothing when the slot lies past the stored length, the
    matching ``RN_CH_<code>`` key otherwise, and nothing for an unknown code.

    Args:
        buffers: Buffers in output order.

    Returns:
        ``MAXLEN`` ``defined_text`` blocks per buffer.
    """
    return "".join(
        defined_text(
            f"RN_{buffer.prefix}_{slot}",
            [
                (f"NOT = {{ {check_variable(f'{buffer.length} > {slot}')} }}", EMPTY_LOC_KEY),
                *(
                    (check_variable(f"{buffer.array}^{slot} = {code}"), char_key(code))
                    for code in DISPLAY_ORDER
                ),
            ],
            EMPTY_LOC_KEY,
        )
        for buffer in buffers
        for slot in range(MAXLEN)
    )
