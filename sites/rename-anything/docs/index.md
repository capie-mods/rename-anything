---
description: Rename Anything lets you rename your country, its leader, its parties, its states and its cities in Hearts of Iron IV, right where the name is shown.
---

# Rename Anything

<p class="endorse">Built on CAPIE</p>

<p class="lead">Click the pencil next to a name, type a new one, press Enter. Rename Anything lets
you rename your country, its leader, its parties, its states and its cities in Hearts of Iron IV,
in the panel where the name is shown.</p>

!!! warning "Pre-release"

    Rename Anything is not on the Steam Workshop yet. The features marked
    <span class="st st-today">Works today</span> were checked in the game on development builds,
    single player, HOI4 1.19.3.0. Multiplayer is not supported.

HOI4 lets you name a division whatever you like, but your own country, its leader and its ruling
party are stuck with whatever the game or a focus tree gives them. Rename Anything gives you a
real text field instead: any name you can type, Polish letters included, saved in your campaign.

<figure class="diagram" markdown="span">
  ![Renaming a leader: click the pencil, type Jan Żółć into the game's own text field, press Enter. The name is stored in the save.](assets/diagrams/edit-in-place.svg)
  <figcaption>Edit where you see the name. The new name is written into your save like any other change.</figcaption>
</figure>

## What you can rename

| Object | Where | Status |
|---|---|---|
| Your country's name and adjective | Pencil on the Politics panel title | <span class="st st-today">Works today</span> needs CAPIE |
| Your country's leader | Pencil next to the portrait in the Politics panel | <span class="st st-today">Works today</span> |
| Party names, short and full, all four party groups | Pencil in the Politics panel, one tab per group | <span class="st st-today">Works today</span> |
| States | State view on the map, or the name editor | <span class="st st-today">Works today</span> |
| Cities (victory points) | "Cities" in the state view, or the name editor | <span class="st st-today">Works today</span> |
| Generals, admirals, advisers | The name editor, from the decision "Rename characters" | <span class="st st-today">Works today</span> |
| Your subject's names, as overlord | | <span class="st st-progress">In progress</span> hidden for now |

Names survive saving, loading and a full restart of the game. Map labels, diplomacy, tooltips
and events pick up a new country name; decision titles keep their own text.

## What needs CAPIE

Rename Anything is ordinary HOI4 script and interface files. Two things need more than script can
do, and those come from CAPIE (Cyprian's API Extender), a small native library:

- your country's name and adjective, because the game has no script effect that takes free text
  for a country;
- the in-panel text fields, because a script cannot read what you type into the game's own text
  field.

States, cities and characters work without CAPIE, through the name editor. Without CAPIE the
pencils that need it are hidden and your country shows its original name.

[How to use it](how-to-use.md){ .md-button .md-button--primary } [Install](install.md){ .md-button }
