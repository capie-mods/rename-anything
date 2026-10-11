---
description: Common questions about Rename Anything. Multiplayer, achievements, antivirus warnings, game updates and uninstalling.
---

# FAQ

## Do I need CAPIE?

For your country's name and the pencils in the Politics panel, yes. For states, cities and
characters, no: those work through the name editor with scripts alone.

## Does it work in multiplayer?

No. It has never been tested with two players, so it is not supported. Remove the CAPIE launch
option from Steam before you play multiplayer.

## Can I still get achievements?

No. Any mod that changes files under `common/` changes the game's checksum, and achievements need
an unmodified checksum. Ironman was not tested.

## My antivirus complains.

That is about CAPIE, which loads itself into the game. Some malware does that too, so heuristic
warnings are possible. Every released binary will be scanned on VirusTotal with the results
linked from the release notes. The source is public, and you can build it yourself.

## What happens after a game update?

CAPIE is pinned to the exact HOI4 1.19.3.0 executable. After a patch, the game starts without
CAPIE and the launcher tells you why. States, cities and characters still work. A custom country
name shows as the original until a CAPIE update supports the new version.

## Which letters can I use?

Letters, digits, space, `-`, `.`, `'` and the Polish letters, up to 32 characters. Typing Polish
letters straight into the game's text field was checked on one keyboard layout. More alphabets
may come later if the game's fonts support them.

## Why can I not rename again right away?

Each rename starts a 5-day cooldown, counted in game days. The pencil's tooltip says when the next
rename is possible.

## How do I uninstall?

Disable the mod in your playset and remove its files. Close the game to unload CAPIE. Names you
set stay in the saves you made. See [Install](install.md#uninstall).

## Does it work with other mods?

It should work with mods that leave the Politics panel and the state view alone. See
[Known issues](known-issues.md#other-mods).
