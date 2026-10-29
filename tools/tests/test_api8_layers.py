"""Tests of the two CAPIE API level 8 features: the map colour and the party ideology name.

They run the VM cases of ``inline_checks.colour_cases`` and
``inline_checks.subideology_cases`` (the real effects of ``tools/inline_editor`` and the
generated catalogs in ``mod/``) one group at a time, plus a few checks of the generator's
inputs. ``tools/tests/check_inline_editor.py`` runs the same cases.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from inline_checks import colour_cases, subideology_cases
from modgen.features import colours


@pytest.fixture(scope="module")
def colour_inputs() -> colour_cases.ColourInputs:
    """Load the colour picker's effects once.

    Returns:
        The inputs.
    """
    return colour_cases.ColourInputs()


@pytest.fixture(scope="module")
def ideology_inputs() -> subideology_cases.IdeologyInputs:
    """Load the party ideology editor's effects once.

    Returns:
        The inputs.
    """
    return subideology_cases.IdeologyInputs()


def test_presets_are_distinct_whole_channels() -> None:
    """About two dozen presets, each channel a whole number 0..255, no colour twice."""
    rgbs = [p.rgb for p in colours.PRESETS]
    assert 20 <= len(rgbs) <= 48  # noqa: PLR2004 - "about 24" presets, under the spec's 48
    assert len(set(rgbs)) == len(rgbs)
    assert all(isinstance(c, int) and 0 <= c <= colours.CHANNEL_MAX for rgb in rgbs for c in rgb)
    assert len({p.english for p in colours.PRESETS}) == len(rgbs)


def test_colour_picking(colour_inputs: colour_cases.ColourInputs) -> None:
    """Presets, steppers, the clamp and the preview frame."""
    assert colour_cases.run_picking(colour_inputs) > len(colours.PRESETS)


def test_colour_apply_restore_cooldown_and_api_gate(
    colour_inputs: colour_cases.ColourInputs,
) -> None:
    """Apply's gates (API level 8, capie_colour, switch, rights, cooldown) and Restore."""
    assert colour_cases.run_apply(colour_inputs) > len(colour_cases.REJECTIONS)


@pytest.mark.parametrize(("cap", "colour", "err"), [(1, 1, 10), (7, 1, 15), (8, 0, 16), (9, 1, 0)])
def test_colour_api_level(
    colour_inputs: colour_cases.ColourInputs, cap: int, colour: int, err: int
) -> None:
    """Only CAPIE API level 8 or higher with the colour layer on can apply a colour."""
    vm = colour_inputs.vm()
    colour_cases.open_own(vm)
    colour_cases.preset(vm, 5)
    assert colour_cases.apply(vm, cap=cap, colour=colour) == err
    assert (colour_cases.layer(vm, "FRA") is None) == (err != 0)


def test_colour_restore_needs_no_capie(colour_inputs: colour_cases.ColourInputs) -> None:
    """A colour set earlier can be removed in a game without CAPIE."""
    vm = colour_inputs.vm()
    vm.temp = {"rn_cc_r": Decimal(1), "rn_cc_g": Decimal(2), "rn_cc_b": Decimal(3)}
    vm.scoped("FRA", lambda: vm.run("rn_country_colour_carrier_set"))
    colour_cases.open_own(vm)
    assert colour_cases.reset(vm) == 0
    assert colour_cases.layer(vm, "FRA") is None


def test_colour_subject_and_daily(colour_inputs: colour_cases.ColourInputs) -> None:
    """The subject picker's rights and the daily cosmetic tag check."""
    assert colour_cases.run_subject(colour_inputs) > 0
    assert colour_cases.run_daily(colour_inputs) > 0


def test_colour_mutations_are_caught(colour_inputs: colour_cases.ColourInputs) -> None:
    """Removing any guard of Apply, Restore or the carrier fails a case."""
    assert colour_cases.run_colour_mutations(colour_inputs) > 0


def test_ideology_apply_restore_cooldown_and_api_gate(
    ideology_inputs: subideology_cases.IdeologyInputs,
) -> None:
    """Apply's gates (API level 8, capie_subideo, switch, rights, cooldown, field) and Restore."""
    assert subideology_cases.run_open(ideology_inputs) > 0
    assert subideology_cases.run_apply(ideology_inputs) > len(subideology_cases.REJECTIONS)


@pytest.mark.parametrize(("cap", "subideo", "err"), [(1, 1, 10), (7, 1, 15), (8, 0, 16), (9, 1, 0)])
def test_ideology_api_level(
    ideology_inputs: subideology_cases.IdeologyInputs, cap: int, subideo: int, err: int
) -> None:
    """Only CAPIE API level 8 or higher with the layer on can name the party ideology."""
    vm = ideology_inputs.vm()
    subideology_cases.open_editor(vm)
    assert subideology_cases.apply(vm, cap=cap, subideo=subideo) == err
    assert (subideology_cases.name_of(vm) is None) == (err != 0)


def test_ideology_revision_grows(ideology_inputs: subideology_cases.IdeologyInputs) -> None:
    """Every set and every removal writes a new capie_sn_rev (CONTRACT 20.2)."""
    vm = ideology_inputs.vm()
    revisions = []
    for _ in range(3):
        vm.nations["FRA"].vars.pop("rn_ip_cd_subideo_until", None)
        subideology_cases.open_editor(vm)
        assert subideology_cases.apply(vm) == 0
        revisions.append(vm.nations["FRA"].vars["capie_sn_rev"])
        vm.nations["FRA"].vars.pop("rn_ip_cd_subideo_until")
        subideology_cases.open_editor(vm)
        assert subideology_cases.reset(vm) == 0
        revisions.append(vm.nations["FRA"].vars["capie_sn_rev"])
    assert revisions == [Decimal(n) for n in range(1, 7)]


def test_ideology_lapse_and_mutations(ideology_inputs: subideology_cases.IdeologyInputs) -> None:
    """A new government or leader removes the name; removing a guard fails a case."""
    assert subideology_cases.run_lapse(ideology_inputs) > 0
    assert subideology_cases.run_ideology_mutations(ideology_inputs) > 0
