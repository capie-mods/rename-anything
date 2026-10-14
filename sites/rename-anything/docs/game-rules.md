---
description: The Rename Anything game rules the host sets in the lobby. Who may rename what, the rename news event, the flag choice, and an on/off switch for every feature.
---

# Game rules

The host sets these in the lobby, under the game rules, like any other rule. Every Rename Anything
rule starts with "Rename Anything:", so they stay together in the list. More rules come with new
features; this page groups them by what they decide.

The rules keep achievements allowed as far as the rules are concerned; the mod itself still
changes the game's checksum (see the [FAQ](faq.md#can-i-still-get-achievements)).

## Who may rename <span class="st st-progress">In progress</span> { #rights }

"Rename Anything: who may rename". In the mod; not yet checked in the game.

| Option | Meaning |
|---|---|
| Own country and subjects (default) | Players rename their own country and their subjects. A faction's leader renames the faction. |
| Host renames every country | As above, and the host may rename every country and every faction. |
| Own country only | Players rename only their own country, not their subjects. A faction's leader still renames the faction. |

The game has no way to tell a script who the host is. In single player you are the host. In
multiplayer the host option does nothing until CAPIE can report who the host is.

If the rule does not allow a rename, the editor says "The game rule does not let you rename this.
Nothing was changed."

## News of a new country name <span class="st st-today">Works today</span> { #news }

"Rename Anything: news of a new country name". Checked in the game on a CAPIE developer build.

| Option | Meaning |
|---|---|
| Off (default) | Country names change quietly. |
| On | Everyone gets a news event when a player renames a country or restores its original name. |

When the previous name is known, the event's title is "*old name* Changes Its Name to *new
name*". Otherwise it is "New country name: *new name*". The text is one of four short reports that
mention the capital, the leader or the adjective. You dismiss it with "Noted."

<figure class="diagram" markdown="span">
  ![Left: the country editor with the name Great Britian. Right: a World News event titled New country name: Great Britian.](assets/screenshots/news-event.jpg)
  <figcaption>A country renamed to Great Britian, and the news event every country receives.</figcaption>
</figure>

## Flag choice { #flags }

"Rename Anything: flag choice" decides which flags a player may give a country.

| Option | Meaning |
|---|---|
| Every flag in the game (default) | Any flag from the game. A subject can also take its overlord's current flag. |
| The country's own flags | Only the flags of the country itself: its ideologies and its other forms of state. |
| Own flags and the overlord's | As above, and a subject can also take its overlord's current flag. |

## Turning features off <span class="st st-progress">In progress</span> { #switches }

Each feature has its own on/off rule, for example "Rename Anything: Country name and adjective",
"Rename Anything: Leader name", "Rename Anything: Party names" or "Rename Anything: Faction
names". All are on by default. When the host turns one off, its buttons stay visible but greyed
out, and the tooltip says the host turned it off for this game. In the mod; not yet checked in the
game.

## Leader portrait <span class="st st-progress">In progress</span> { #portrait }

Choosing a different portrait for a country leader is being prepared. It will bring rules of its own: which
portraits are on offer, and whether the overlord, the subject or both may change a subject
leader's portrait. Its on/off switch already exists in the list; its text says that the portrait
choice comes in a later version.
