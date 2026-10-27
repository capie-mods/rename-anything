# Backlog after the 1.19.4.0 port

Player requests from the Workshop comments and what the 1.19.4.0 patch notes mean for the mod.
The port itself (CAPIE pins, see `capie/docs/research/port-1.19.4.0.md`) comes first: on 1.19.4.0
CAPIE refuses to load until it is done.

## Player requests

| # | Request (Workshop) | Plan | Where |
|---|---|---|---|
| 1 | "Is there no way to get rid of the 5 day wait between changes?" (bluechair607, 2026-10-25) | Game rule "Rename cooldown" with options (off, 1, 5 default, 15, 30 days); the cooldown effects read the rule | `common/game_rules`, `scripted_effects/rn_inline_cooldown.txt`, localisation |
| 2 | Custom portraits and flags (birbo, 2026-10-20); maintainer: offer every leader of the running game, modded ones included, not only vanilla | Build the portrait list at runtime from the characters the game has loaded (CAPIE side: the portrait layer already resolves any sprite; the picker must enumerate instead of using a generated vanilla list) | CAPIE portrait layer, `scripted_effects`/GUI of the leader picker, `tools/modgen` |
| 3 | "Increase the character count for the country rename tool" (B I G S T I N K Y, 2026-10-18) | Raise the edit box `max_characters` and the matching CAPIE limit; check the localisation buffer and save size | `interface/*.gui`, CAPIE `max_utf8`/schema limits, CONTRACT |
| 4 | "Add more flags to the menu" (Algo, 2026-10-18); maintainer: same as leaders | Flag picker from every flag the game has loaded (mods included), not a generated list | flag picker effects/GUI, CAPIE flag layer (`build_flag_candidates`) |

## Status and findings (2026-10-27)

1. **Cooldown rule: done.** Lobby rule `rn_rename_cooldown` (no cooldown, 1, 5 default, 15, 30
   days) in `tools/inline_editor/common/game_rules/rn_rules.txt`; `rn_ip_cooldown_days` is the
   single source and `rn_cd_days` (states, cities) reads it. English and Polish texts in
   `rn_cooldown_rule_l_*.yml`; the "ready" tooltips no longer name a day count. Tests: two pytest
   cases, eight script-VM cases (every option, country and party), `check_inline_editor.py` green.
   Needs an in-game check of the lobby screen.
2. **Every leader, modded ones included.** Today `tools/gen.py` builds the portrait catalog from
   the vanilla files at build time, so other mods' leaders never appear. A runtime list needs
   CAPIE: enumerate the sprite database (CAPIE already resolves `sprite_database_global` and
   `sprite_find`) or the loaded characters, and hand the list to script in pages. That is a new
   capability (API level 8) with its own contract section; design first, then CAPIE, then the
   picker GUI.
3. **Longer country names.** The 32-character limit sits in four places that must move
   together: `CONTRACT.md` (error 2 "more than 32 characters"), `country_protocol.hpp`
   (`max_field_codepoints = 32`), the console (`console_text.hpp`) and the mod's script name
   buffers and generated tables. A new limit (e.g. 48 or 64) is an API level change; the text
   field itself copies up to 128. Check the focus-tree header and map labels with long names
   (patch note on overlapping filters).
4. **More flags.** Same shape as 2: the flag catalog is generated from vanilla `gfx/flags`; a
   runtime catalog (every flag the game loaded, mods included) needs a CAPIE enumeration of the
   flag files the game knows (`build_flag_candidates` is already pinned). Shares the paging
   protocol with 2.

5. **Mini portraits in the Characters list: done (2026-10-27)**, offline-tested;
   `char_portraits.py`. Needs an in-game look: the row image uses
   `GFX_rnp_[?rn_row_character.rn_pp_i|0]`; if the game does not resolve the variable through
   the typed row variable, switch to a numeric array built with the page.
6. **Other languages (Workshop comment: German, Russian, Czech, French).** Glyph coverage of the
   1.19.4.0 fonts: Latin-1 (de/fr/es/pt…) in every font; Latin Extended-A (cs/sk/hu/ro/tr…) in
   the main `hoi_*` fonts; Cyrillic only in the separate `*_cryllic` fonts the game uses when its
   language is Russian. CAPIE's grammar alphabet (API level 2, CONTRACT section 7) already has
   264 codes: Latin-1 and Latin Extended-A. Only Rename Anything's older in-place editors
   (country, leader, party) still use the 84-code table. Plan: move them to the grammar
   encoding and extend the name tables to codes 85..264 (append only; saves stay valid);
   measure the cost of the larger per-slot tables first. Cyrillic would show only for players
   whose game runs in Russian; **decided 2026-10-27: acceptable** (the maintainer accepts
   Cyrillic names that show only in the Russian version of the game).
7. **Country colour picker (wishlist).** The game has a native faction colour picker
   (`CFactionColorPickerWindow`, palette presets plus slider), so a preset palette in a scripted
   GUI (grid of colours, click, then Apply or Enter) is straightforward. Changing the map colour
   needs a CAPIE colour layer like the flag layer: find the function the map takes a country's
   colour from (RE), hook it for countries with a layer, store the colour in country variables.

8. **Rename the ruling party's sub-ideology (maintainer request 2026-10-27).** The politics
   panel's `ideology` text box is filled natively from the sub-ideology's global localisation key
   (`conservatism`, `despotism`, ...). Script cannot do it: overriding the key renames it for every
   country, and switching the leader to a custom sub-ideology breaks vanilla triggers
   (`has_country_leader_ideology`). Plan: a CAPIE layer like the portrait layer, keyed to the
   ruling party's leader: find (RE) the function that turns a character's sub-ideology into its
   display text, answer the custom text for a leader with a layer, store the text in character
   or country variables. Game mechanics stay untouched. API level 8, contract section first.
9. **Mini portraits, first in-game result (2026-10-27).** Visibility works (large / small /
   unknown icons are chosen right), but the `image` property does not resolve
   `[?rn_row_character.rn_pp_i]` through the typed row variable: every row shows the default
   sprite. Fix: a second grid over the list, iterating a numeric array built with the page
   (`value = rn_pv`, `image = "GFX_rnchp_[?rn_pv|0]"`), the pattern the flag picker uses.

## 1.19.4.0 patch notes that matter

- "Reduced string allocations in GUI system": seen in the binary. GUI child lookups now take a
  `{const char*, int32}` name and use per-type hash maps (CAPIE port notes).
- "State scope variables are no longer classified as raw numbers in math expressions": check
  the city/state lookup that relied on the old behaviour (`docs/research/typed-state-variable-findings.md`).
- "Added a toggle ... that colors subjects the same color as their overlords": check that a
  renamed subject's map label and colour still look right with the toggle on.
- "Right-Clicking the topbar country flag opens your own diplomacy view": check that the flag
  layer still draws in the top bar and the click is not blocked by our GUI.
- "Fixes country names being overlapped by filters in focus tree": check that long custom names
  fit the focus tree header (relevant to request 3).
- "Added the optional argument immediate_status_update = yes to set_major": not used by the mod.
