# Rename Anything changelog

Change notes of the Rename Anything Steam Workshop item (`mod/`). `tools/release/release.py`
turns the section of the version in `mod/descriptor.mod` into the Workshop change note
(BBCode). Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.1] - unreleased

- Fixed: about 180 characters showed the unknown mini portrait in the Characters tab, and 10
  leader and general portraits were missing from the portrait list. Their pictures come from the
  four former DLC that HOI4 now gives every player (Together for Victory, Death or Dishonor,
  Waking the Tiger, Man the Guns).

## [0.2.0] - 2026-10-28

- HOI4 1.19.4.0: the features that need CAPIE work again with CAPIE 1.5.1, which supports the
  new game build.
- New game rule "Rename Anything: rename cooldown": no cooldown, 1, 5 (default), 15 or 30 days
  between two renames of the same kind. It applies to every rename type.
- The Characters tab shows a small portrait next to every character (base-game characters;
  characters from other mods show the game's unknown portrait).
- The flag and portrait lists and the city lists follow HOI4 1.19.4.0 (19 more flags, one more
  portrait, two more cities). Flags and portraits already chosen in a saved game stay as they are.
- Fixed: 69 portraits from South American countries showed as blank cells; portraits that need a
  DLC are listed only with that DLC.
- Fixed: renaming a subject's country needed an up-to-date CAPIE but did not check for it;
  "Restore name" on a country without a custom name no longer sends a news event.

## [0.1.0] - unreleased

- First Workshop release: rename countries, leaders, parties, factions, states and cities in
  game, with cooldowns and game rules for who may rename what.
- With CAPIE: free-text names typed in place, custom country flags from the game's catalogue.
- Without CAPIE: the on-screen keyboard editor.
- Not declared multiplayer-compatible yet.
