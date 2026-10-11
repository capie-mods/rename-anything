"""Rename cooldown of the legacy editor (states and cities).

One constant, :data:`COOLDOWN_DAYS`, sets the cooldown for every rename type:
country name and adjective, leader, parties (one shared cooldown), states and
cities (one per player country and category). It starts only after a
successful rename. The in-place editor gets the same value through the
``@RN_COOLDOWN_DAYS@`` token (see :mod:`modgen.features.inline_editor`), and the
legacy editor checks the in-place cooldowns too, so neither can be used to get
around the other.

Each category keeps its expiry day in a country variable
(``rn_cd_<category>_until``). Triggers and tooltips compute the remaining days
with temporary-variable arithmetic inside the trigger, as vanilla
``common/ai_strategy/ENG.txt`` does, so no temporary value is shared between
``defined_text`` blocks.
"""

from __future__ import annotations

from typing import NamedTuple

from modgen.common import POLISH
from modgen.script import defined_text

COOLDOWN_DAYS = 5
"""Rename cooldown in game days, the single source for every rename type.

It is written into the state/city cooldown effect ``rn_cd_days`` and substituted for
the ``@RN_COOLDOWN_DAYS@`` token in the in-place editor source (``rn_ip_cooldown_days``).
"""

COOLDOWN_LABEL_LIMIT = 30
"""Largest remaining-day count that gets its own tooltip text; longer ones say "more than"."""

MORE_THAN_LIMIT = 1000000
"""Upper bound of the "more than" tooltip branch; larger than any real game date."""

MORE = "MORE"
"""Key suffix of the "more than :data:`COOLDOWN_LABEL_LIMIT` days" tooltip text."""


class CooldownCategory(NamedTuple):
    """One cooldown of the legacy editor."""

    key: str
    """Localisation key part (``RN_CD_<key>_*``)."""

    prefix: str
    """Script name prefix: ``<prefix>_until``, ``<prefix>_active``, ``<prefix>_start``."""

    english: str
    """English tooltip text before the number of days."""

    polish: str
    """Polish tooltip text before the number of days."""


CATEGORIES = (
    CooldownCategory(
        key="STATE",
        prefix="rn_cd_state",
        english="Next state rename possible in",
        polish="Kolejna zmiana nazwy stanu możliwa za",
    ),
    CooldownCategory(
        key="VP",
        prefix="rn_cd_vp",
        english="Next city rename possible in",
        polish="Kolejna zmiana nazwy miasta możliwa za",
    ),
)
"""The state and city cooldowns, in output order."""


def _days_left(category: CooldownCategory, limit: int) -> str:
    """Return the trigger that holds while 0 < days left < ``limit``.

    Args:
        category: Cooldown category.
        limit: Exclusive upper bound of the remaining days.

    Returns:
        Trigger body with the temporary-variable arithmetic.
    """
    return (
        f"set_temp_variable = {{ rn_cd_left = {category.prefix}_until }} "
        "subtract_from_temp_variable = { rn_cd_left = global.num_days } "
        f"check_variable = {{ rn_cd_left > 0 }} check_variable = {{ rn_cd_left < {limit} }}"
    )


def tooltip_loc() -> str:
    """Return the cooldown tooltip scripted localisation.

    Returns:
        A comment line and one ``RN_CD_<key>_LEFT`` block per category that picks an
        exact day count (1 to :data:`COOLDOWN_LABEL_LIMIT`), "more than" or the
        ready text.
    """
    out = ["\n# Rename cooldown tooltips (country variables rn_cd_state_until / rn_cd_vp_until).\n"]
    for category in CATEGORIES:
        branches = [
            (_days_left(category, n + 1), f"RN_CD_{category.key}_WAIT_{n}")
            for n in range(1, COOLDOWN_LABEL_LIMIT + 1)
        ]
        more = f"RN_CD_{category.key}_WAIT_{MORE}"
        branches.append((_days_left(category, MORE_THAN_LIMIT), more))
        out.append(
            defined_text(f"RN_CD_{category.key}_LEFT", branches, f"RN_CD_{category.key}_READY")
        )
    return "".join(out)


def effects() -> str:
    """Return the effects that start the state and city cooldowns.

    Returns:
        ``rn_cd_days`` (the length as a temporary variable) and one
        ``<prefix>_start`` per category, with their comment line.
    """
    starts = "".join(
        f"""{category.prefix}_start = {{
	rn_cd_days = yes
	set_variable = {{ {category.prefix}_until = global.num_days }}
	add_to_variable = {{ {category.prefix}_until = temp_var:rn_cd_days }}
}}
"""
        for category in CATEGORIES
    )
    return f"""# Rename cooldown (states, cities): COUNTRY scope, one per category, started only after a setter ran.
rn_cd_days = {{
	set_temp_variable = {{ rn_cd_days = {COOLDOWN_DAYS} }}
}}
{starts}"""  # noqa: E501 - generated script lines are emitted verbatim


def triggers() -> str:
    """Return the ``<prefix>_active`` triggers of both categories.

    Returns:
        The triggers with their comment lines.
    """
    actives = "".join(
        f"""{category.prefix}_active = {{
	set_temp_variable = {{ rn_cd_left = {category.prefix}_until }}
	subtract_from_temp_variable = {{ rn_cd_left = global.num_days }}
	check_variable = {{ rn_cd_left > 0 }}
}}
"""
        for category in CATEGORIES
    )
    return (
        "# Rename cooldown, COUNTRY scope, one per category (states, cities).\n"
        "# Temp-variable arithmetic inside triggers follows vanilla "
        "common/ai_strategy/ENG.txt:1729-1731.\n" + actives
    )


def _wait_text(category: CooldownCategory, lang: str, n: int | str) -> str:
    """Return one "next rename possible in" tooltip text.

    Args:
        category: Cooldown category.
        lang: Game language; Polish has its own text, every other language English.
        n: Days left, or :data:`MORE` for the "more than" text.

    Returns:
        The red-coloured tooltip text.
    """
    if lang == POLISH:
        if n == MORE:
            left = f"ponad {COOLDOWN_LABEL_LIMIT} dni"
        else:
            left = "1 dzień" if n == 1 else f"{n} dni"
        return f"§R{category.polish} {left}.§!"
    if n == MORE:
        left = f"more than {COOLDOWN_LABEL_LIMIT} days"
    else:
        left = "1 day" if n == 1 else f"{n} days"
    return f"§R{category.english} {left}.§!"


def wait_entries(lang: str) -> list[str]:
    """Return the ``RN_CD_<key>_WAIT_<n>`` localisation lines of one language.

    Args:
        lang: Game language.

    Returns:
        One line per category and remaining-day text.
    """
    return [
        f' RN_CD_{category.key}_WAIT_{n}: "{_wait_text(category, lang, n)}"\n'
        for category in CATEGORIES
        for n in [*range(1, COOLDOWN_LABEL_LIMIT + 1), MORE]
    ]
