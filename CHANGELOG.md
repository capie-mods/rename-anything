# Rename Anything changelog

Change notes of the Rename Anything Steam Workshop item (`mod/`). `tools/release/release.py`
turns the section of the version in `mod/descriptor.mod` into the Workshop change note
(BBCode). Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.3.0] - 2026-10-29

- New, needs CAPIE 1.6: country colours on the map. Open the "Colour" tab of the country name
  editor or the flag picker; for another country, "Change map colour" in its Diplomacy view or
  "Map colour" in a subject's flag picker. Then Apply. The name and the flag do not change.
- 90 colours to pick from, grouped by hue, with a row of the great powers' own map colours.
- Red, green and blue can be changed by 1, 10 or 50, and the code under the preview shows the
  exact colour as #RRGGBB.
- Type a colour code: six hex digits such as 1E5AA0, or red, green and blue such as 30 90 160.
  Use the keypad in the picker or your keyboard. A wrong code shows what is wrong and is not
  applied.
- For a subject: "My colour" gives it your country's current colour; "Reset" brings back its
  own colour. "Reset" works for your own country too, and a change of the country's form of
  state also brings its own colour back.
- New game rule "Rename Anything: Country map colour": own country and subjects (default),
  own country only, any country (the host), or off. Colours follow the rename cooldown.

## [0.2.1] - 2026-10-28

- Fixed: opening the Characters tab wrote up to 100,000 lines to the game's error.log. It now
  writes none.
- Fixed: about 1,800 characters showed the unknown portrait in the Characters tab, mostly
  characters from DLC. A DLC portrait shows when you own that DLC; without it you see the
  unknown portrait, as elsewhere in the game.
- The portrait list has 10 more leader and general portraits (from Together for Victory, Death
  or Dishonor, Waking the Tiger and Man the Guns, which every player now has). The Anniversary
  Pack portraits are no longer offered: the game cannot check that DLC, which caused an error.
- Portraits you already chose stay as they are; the portrait list may start from the first
  entry again.

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
