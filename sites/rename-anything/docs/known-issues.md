---
description: Known issues in the current Rename Anything development builds and what to do about them.
---

# Known issues

These come from the latest test runs on development builds (HOI4 1.19.3.0, single player). Each
one says what happens and what to do until it is fixed.

## Edit mode stays on after you close Politics <span class="st st-progress">In progress</span> { #edit-mode }

If you close the Politics panel (for example with <kbd>Esc</kbd>) while an editor is open, the
editor disappears with the panel, but Rename Anything still thinks you are editing.

What to do: open the panel again and apply or cancel the edit. Or apply or cancel before you
close the panel.

## The text field takes more than 32 characters

The game's text field lets you keep typing past 32 characters. Rename Anything then rejects the
name with a red line ("Name not accepted: up to 32 characters the game can show.") and changes
nothing. Shorten the name and press <kbd>Enter</kbd> again.

## A long leader name runs under the pencil

In the Politics panel a long leader name can reach the pencil next to the portrait. The pencil
still works.

## Multiplayer is not supported <span class="st st-not">Not supported</span> { #multiplayer }

Rename Anything and CAPIE were never tested with two players. Do not use them in multiplayer.
Switch CAPIE off before you join or host a multiplayer game.

## New features not yet checked in the game <span class="st st-progress">In progress</span> { #unchecked }

"Restore name", the rule "who may rename" and the on/off switches of the
[game rules](game-rules.md) are in the mod but have not been checked in the game yet. Faction names
and flags need CAPIE 1.4, which exists only as a developer build; with an older CAPIE the faction
editor changes nothing and says so.

## Older saves with a custom country name

Saves made with the first development builds stored a custom country name as a cosmetic tag, which
also changed the flag. Such a country keeps showing its name. The first time you rename or restore
it, Rename Anything moves the name to the new storage and drops that cosmetic tag. The cosmetic tag
the country had before was never stored, so it cannot come back.

## Other mods

Rename Anything should work with mods that leave the Politics panel and the state view alone.
Mods that replace `countrypoliticsview.gui` or the same scripted GUIs can conflict. Mods that
change the map, state or province IDs, or add victory points, need the city tables regenerated.
