---
description: Installing Rename Anything. The planned Workshop release with the CAPIE launcher, and today's development setup.
---

# Install

## With the first release <span class="st st-planned">Planned</span> { #first-release }

Nothing is published yet. The plan:

1. Subscribe to Rename Anything on the Steam Workshop and add it to a playset in the Paradox
   Launcher, like any other mod.
2. Run one PowerShell line that installs the CAPIE launcher. It asks whether to add the launcher
   to Steam's launch options, create a desktop shortcut, or both.
3. Press Play in Steam (or use the shortcut), pick your playset, and play. CAPIE loads only into
   the game started this way.

<figure class="diagram" markdown="span">
  ![Launch chain: Steam Play or a shortcut starts the CAPIE launcher, then the Paradox Launcher, then the game with CAPIE. On an unknown game version the game starts without CAPIE.](assets/shared/diagrams/launch-chain.svg)
  <figcaption>Planned launch chain. Built and reviewed, not yet tested end to end.</figcaption>
</figure>

The command will be published with the first release. Until then the installer refuses to run on
purpose. The CAPIE documentation describes the installer, its options, updates and uninstall in
detail.

Without CAPIE the mod still works for states, cities and characters. The pencils for your
country, leader and parties need CAPIE and stay hidden without it.

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
4. For your country's name and the in-panel text fields, build CAPIE and load it into the running
   game as described in the repository's `plugin/README.md`. Repeat this every time the game
   starts. Current builds still use the legacy file names `rename_anything_*.dll` and
   `rename_anything_injector.exe`; they will be renamed to CAPIE in a separate step.

`supported_version="1.19.*"` only quiets the launcher's warning. Only 1.19.3.0 was tested.

## Uninstall

Disable the mod in your playset and delete `rename_anything_dev.mod` (and the copied folder, if
you made one). Close the game to unload CAPIE. Nothing in the game folder needs repairing.

Names you set stay in the saves you made. To drop a custom country name from a save, use
"Original name" in the game before you uninstall. Continuing an old save without the mod was not
tested; try it on a copy.
