---
description: Installing Rename Anything. The planned release with the Workshop, the CAPIE installer and the CAPIE switch in your playset, and today's development setup.
---

# Install

## With the first release <span class="st st-progress">In progress</span> { #first-release }

Nothing is published yet. This is how it will work:

1. Subscribe to **Rename Anything** and to the small **CAPIE** mod on the Steam Workshop, and add
   both to a playset in the Paradox Launcher, like any other mod.
2. Install CAPIE once. Two ways, same result:
    - one line in PowerShell (`irm ... | iex`). It runs the installer in the terminal, with a short
      animation, and asks before it changes anything;
    - the installer from the project's GitHub Releases page.
3. Press Play in Steam, pick your playset, and play. CAPIE loads only while the CAPIE mod is
   enabled in the playset you start.

<figure class="diagram" markdown="span">
  ![Launch chain: Steam Play or a shortcut starts the CAPIE launcher, then the Paradox Launcher, then the game with CAPIE. On an unknown game version the game starts without CAPIE.](assets/shared/diagrams/launch-chain.svg)
  <figcaption>The CAPIE launcher goes through the Paradox Launcher, so your playsets work as usual.</figcaption>
</figure>

### Switching CAPIE on and off

The CAPIE mod in your playset is the switch. It contains no game content.

- Enabled: the CAPIE launcher loads CAPIE into the game.
- Disabled, or not in the playset: the game starts without CAPIE, as if it were not installed.

Disable it before you play multiplayer. To remove CAPIE completely, run the installer again and
choose uninstall; it puts back what it changed.

The command and the release will be published together. Until then the installer refuses to run
on purpose. The CAPIE documentation describes the installer, its options, updates and uninstall in
detail.

Without CAPIE the mod still works for states, cities and characters. The pencils for your
country, leader and parties, and renaming subjects, need CAPIE and stay hidden without it.

## Today: development builds

For testers comfortable with a developer setup.

1. Keep the whole `mod/` folder of the repository, for example
   `C:/Users/you/Documents/GitHub/hoi4-rename-anything/mod`.
2. In your HOI4 user folder (`Documents/Paradox Interactive/Hearts of Iron IV/mod/`) create
   `rename_anything_dev.mod`. The `path` must point at the `mod` folder that contains `common/`,
   `interface/` and `descriptor.mod`:

    ```text title="rename_anything_dev.mod"
    name="Rename Anything (dev)"
    path="C:/Users/you/Documents/GitHub/hoi4-rename-anything/mod"
    version="0.1.0"
    supported_version="1.19.*"
    ```

3. Add the mod to a playset in the Paradox Launcher. You do not need to change `dlc_load.json` or
   any game file.
4. For the features that need CAPIE, build CAPIE and load it into the running game as described
   in the repository's `plugin/capie/README.md`. Repeat this every time the game starts.

`supported_version="1.19.*"` only quiets the launcher's warning. Only 1.19.3.0 was tested.

## Uninstall

Disable the mod in your playset and delete `rename_anything_dev.mod` (and the copied folder, if
you made one). Close the game to unload CAPIE. Nothing in the game folder needs repairing.

Names you set stay in the saves you made. To drop a custom country name from a save, restore the
name in the game before you uninstall. Continuing an old save without the mod was not tested; try
it on a copy.
