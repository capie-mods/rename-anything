---
description: How to rename things with Rename Anything. Pencils, Enter, the party tabs, the 5-day cooldown, states, cities and characters.
---

# How to use

You rename your country, leader and parties in the Politics panel. States, cities and characters
have their own editor. Each section below says whether it needs CAPIE.

## Your leader

1. Open the Politics panel.
2. Click the small pencil next to the leader's portrait. Its tooltip says "Rename leader".
3. The game's own text field opens in the same place, filled in with the current name.
4. Type the new name and press <kbd>Enter</kbd>, or click the Apply icon.

Today the leader's name updates after you close the Politics panel and open it again. See
[Known issues](known-issues.md).

Needs CAPIE, because a script cannot read what you type into the game's text field.

## Your parties, in all four party groups

1. In the Politics panel, click the pencil for parties ("Rename parties").
2. The editor has one tab per party group, like the game's own tabs. The tab's tooltip shows that
   party's current name. Pick the group you want; it does not have to be the party in power.
3. Fill in both fields, "Short name" and "Full name", and press <kbd>Enter</kbd>.

The new party name shows in the panel right away. Needs CAPIE.

## Your country's name and adjective

1. Click the pencil on the Politics panel's title line ("Rename country").
2. Fill in "Name" and "Adjective". Both are required.
3. Press <kbd>Enter</kbd>.

The map, diplomacy, tooltips and events use the new name. Decision titles keep the text they
were written with. To go back, use "Original name" in the name editor; it drops the custom name.
An older cosmetic tag your country had before is not restored.

Needs CAPIE in every game session. Without CAPIE your country shows its original name, and the
custom name comes back when you start the game with CAPIE again.

## States and cities

You can rename your own states and the cities (victory points) in them. No CAPIE is needed.

- Select one of your states on the map. Next to the game's state panel a small "Rename" panel
  appears with "Rename state", "Cities" and "Reset".
- "Cities" lists the victory points of that state; pick one and rename it.
- The same lists are in the name editor, on the "States" and "Cities" tabs.

## Generals, admirals and advisers

Open the decisions, find the "Rename Anything" category, and take the decision "Rename
characters". It opens the name editor on the "Characters" tab, where you pick a character from
the list and type a new name. States and cities are in the same editor. No CAPIE is needed.

The name editor has its own typing: letters, <kbd>Shift</kbd> + letter for capitals, digits,
`-` and `.`; <kbd>Backspace</kbd> deletes and <kbd>Enter</kbd> applies. Polish letters and `'`
are on buttons. Game hotkeys stay active while you type there.

## Limits and checks

- At most 32 characters per name. Longer input is rejected with a red line under the field, and
  nothing is changed. Nothing is cut short.
- Letters, digits, space, `-`, `.`, `'` and the Polish letters ą ć ę ł ń ó ś ź ż (and capitals).
  Characters the game cannot show are rejected.
- An empty field is rejected.
- Renames have a 5-day cooldown. While it runs, the pencil is greyed out and its tooltip adds a
  red line such as "Next rename possible in 3 days (last change: 4 January 1936)." For states and
  cities the editor says "You can rename one state every 5 days" (or city).
- You can rename only your own country's things.

## Where the names live

Every name is stored in your save, like any other change in the campaign. It survives saving,
loading and restarting the game.
