---
description: The two Rename Anything game rules the host sets in the lobby. Who may rename what, and a news event when a country is renamed.
---

# Game rules

<span class="st st-progress">In progress</span> Both rules are in the mod and pass their offline
checks. They have not been checked in the game yet.

The host sets them in the lobby, under the game rules, like any other rule. Both keep
achievements allowed as far as the rules are concerned; the mod itself still changes the game's
checksum (see the [FAQ](faq.md#can-i-still-get-achievements)).

## Who may rename

"Rename Anything: who may rename"

| Option | Meaning |
|---|---|
| Own country and subjects (default) | Players rename their own country and their subjects. A faction's leader renames the faction. |
| Host renames every country | As above, and the host may rename every country and every faction. |
| Own country only | Players rename only their own country, not their subjects. A faction's leader still renames the faction. |

The game has no way to tell a script who the host is. In single player you are the host. In
multiplayer the host option does nothing until CAPIE can report who the host is.

If the rule does not allow a rename, the editor says "The game rule does not let you rename this.
Nothing was changed."

## News of a new country name

"Rename Anything: news of a new country name"

| Option | Meaning |
|---|---|
| Off (default) | Country names change quietly. |
| On | Everyone gets a news event when a player renames a country or restores its original name. |

The event's title reads "*old name* Changes Its Name to *new name*". When the old name is not
known, the title is "*new name* Takes a New Name". The text is one of four short reports that
mention the capital, the leader or the adjective. You dismiss it with "Noted."

<figure class="diagram" markdown="span">
  ![Left: the country editor with the name Great Britian. Right: a World News event titled New country name: Great Britian.](assets/screenshots/news-event.jpg)
  <figcaption>A country renamed to Great Britian, and the news event every country receives.</figcaption>
</figure>

At first the old name is known only when the country already had a name given by a player. A
newer CAPIE will also report the game's name at the moment of the rename.
