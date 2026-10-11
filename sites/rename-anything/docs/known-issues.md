---
description: Known issues in the current Rename Anything development builds and what to do about them.
---

# Known issues

These come from the latest test runs on development builds (HOI4 1.19.3.0, single player). Each
one says what happens and what to do until it is fixed.

## The leader's name updates only after you reopen Politics <span class="st st-progress">In progress</span> { #leader-refresh }

After you rename your leader, the Politics panel keeps showing the old name. The new name is
already applied: it shows as soon as you close the Politics panel and open it again. Party names
update right away.

A fix exists and was loaded in the last test, but a safety check in it did not recognise the
panel, so it stayed switched off on purpose. It is being reworked.

What to do: close and reopen the Politics panel.

## Edit mode stays on after you close Politics <span class="st st-progress">In progress</span> { #edit-mode }

If you close the Politics panel (for example with <kbd>Esc</kbd>) while an editor is open, the
editor disappears with the panel, but Rename Anything still thinks you are editing. When you open
the panel again, Apply and Enter in that editor can do nothing, without a message.

What to do: click Cancel (the small cross) in the editor, then open it again with the pencil. Or
apply or cancel your edit before you close the panel.

## Multiplayer is not supported <span class="st st-not">Not supported</span> { #multiplayer }

Rename Anything and CAPIE were never tested with two players. Do not use them in multiplayer.
Remove the CAPIE launch option before you join or host a multiplayer game.

## The text field takes more than 32 characters

The game's text field lets you keep typing past 32 characters. Rename Anything then rejects the
name with a red line ("Name not accepted: up to 32 characters the game can show.") and changes
nothing. Shorten the name and press <kbd>Enter</kbd> again.

## Renaming a subject's names

As an overlord you cannot rename your subjects' names yet. The place for it exists but is hidden
while it is <span class="st st-progress">In progress</span>.

## Other mods

Rename Anything should work with mods that leave the Politics panel and the state view alone.
Mods that replace `countrypoliticsview.gui` or the same scripted GUIs can conflict. Mods that
change the map, state or province IDs, or add victory points, need the city tables regenerated.
