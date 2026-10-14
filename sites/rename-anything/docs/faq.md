---
description: Common questions about Rename Anything. Multiplayer, achievements, antivirus warnings, game updates, flags and uninstalling.
---

# FAQ

## Do I need CAPIE?

For your country's name, the pencils in the Politics panel and renaming subjects, yes. For
states, cities and characters, no: those work through the name editor with scripts alone.

## Does renaming my country change its flag?

No. The name you give is kept apart from the game's cosmetic tags, so the flag and colour stay as
the game sets them. Choosing your own flag is planned as a separate feature.

## Does it work in multiplayer?

No. It has never been tested with two players, so it is not supported. Switch CAPIE off before you
play multiplayer: disable the CAPIE mod in your playset.

## Can I still get achievements?

No. Any mod that changes files under `common/` changes the game's checksum, and achievements need
an unmodified checksum. Ironman was not tested.

## My antivirus complains.

That is about CAPIE, which loads itself into the game. Some malware does that too, so heuristic
warnings are possible. Every released binary will be scanned on VirusTotal with the results
linked from the release notes. The source is public, and you can build it yourself.

## What happens after a game update?

CAPIE is pinned to the exact HOI4 1.19.3.0 executable. After a patch, the game starts without
CAPIE and you are told why. States, cities and characters still work. A custom country name shows
as the game's name until a CAPIE update supports the new version.

## Which letters can I use?

Letters, digits, space, `-`, `.`, `'` and the Polish letters, up to 32 characters. Typing Polish
letters straight into the game's text field was checked on one keyboard layout. More alphabets
may come later if the game's fonts support them.

## Why can I not rename again right away?

Each rename starts a 5-day cooldown, counted in game days. The pencil's tooltip says when the next
rename is possible. Restoring a name counts as a rename.

## Can other players rename my country?

Not by default. The host chooses in the lobby who may rename what; see
[Game rules](game-rules.md). An overlord can always rename its own subjects unless the host picks
"Own country only".

## How do I uninstall?

Disable the mod in your playset and remove its files. Close the game to unload CAPIE. Names you
set stay in the saves you made. See [Install](install.md#uninstall).

## Does it work with other mods?

It should work with mods that leave the Politics panel and the state view alone. See
[Known issues](known-issues.md#other-mods).
