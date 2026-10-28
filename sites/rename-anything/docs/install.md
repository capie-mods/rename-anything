---
description: How to install Rename Anything and CAPIE on Windows step by step, how to check that CAPIE is running, and what to do when the game says CAPIE is missing.
---

# Install

Rename Anything needs three things. Most problems come from one of them missing:

| Part | What it is | Where it comes from |
|---|---|---|
| **Rename Anything** | the mod itself | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3819937546) |
| **CAPIE** (mod) | a small switch mod with no game content; it tells CAPIE to load | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3819929471) |
| **CAPIE** (program) | the native part that lets the mod read the text field, change country names and flags | installed once with a PowerShell setup tool |

Subscribing to the two mods is not enough. Without the program the mod shows
**"CAPIE missing"** and only the CAPIE-free features work (states, cities, characters).

## Before you start

- Windows 10 or 11. CAPIE is Windows-only. On macOS and Linux the mod runs without CAPIE
  (see [Without CAPIE](#without-capie)).
- Hearts of Iron IV 1.19.4.0 from Steam. The version is shown in the bottom left corner of
  the main menu. CAPIE 1.5.1 supports only this build (CAPIE 1.5.0 supported only 1.19.3.0); on any other build the game starts
  without CAPIE. Copies from other stores have a different `hoi4.exe` and are not supported.
- No local copy of Rename Anything or CAPIE in `Documents\Paradox Interactive\Hearts of Iron IV\mod`
  with the same name as the Workshop item. With two mods of the same name the game uses the local
  one and skips the Workshop one.
- About 5 minutes.

## Step 1: subscribe to both mods

1. Subscribe to **[Rename Anything](https://steamcommunity.com/sharedfiles/filedetails/?id=3819937546)** on the Steam Workshop.
2. Subscribe to **[CAPIE](https://steamcommunity.com/sharedfiles/filedetails/?id=3819929471)**.
3. Wait until Steam has downloaded both (Steam, View, Downloads).

## Step 2: install the CAPIE program

The setup tool changes the Hearts of Iron IV launch options in Steam. Steam keeps them in a file
it rewrites while it runs, so **Steam must be closed** during this step. The tool can close Steam
for you and start it again afterwards.

### Way A: one PowerShell line (recommended)

1. Press ++win++, type `PowerShell`, and open **Windows PowerShell**. You do not need
   "Run as administrator".
2. Paste this line and press ++enter++:

    ```powershell
    irm https://github.com/capie-mods/capie/releases/latest/download/install.ps1 | iex
    ```

3. A menu opens. Choose **1 Install or update** with ++enter++.
4. Answer the questions:

    | Question | Answer |
    |---|---|
    | Install or update CAPIE in `...\RenameAnything`? | ++enter++ (yes) |
    | Loading method: 1 = CAPIE launcher, 2 = proxy | ++enter++ (1, launcher) |
    | Add the CAPIE launcher to the HOI4 Steam launch options? | ++enter++ (yes) |
    | Steam is running. Close Steam now? | ++enter++ (yes) |
    | Several Steam accounts found | the number of the account you play on, or `A` for all |
    | Start Steam again? | ++enter++ (yes) |

5. Wait for the **Summary**. It should say that CAPIE is installed and that Steam starts it
   ("started by Steam"). If a step failed, the summary names the log file; see
   [If it does not work](#troubleshooting).

The tool installs into `%LOCALAPPDATA%\RenameAnything`. It does not change the game folder.

!!! note "What `irm | iex` does"

    It downloads the setup script from the latest CAPIE release on GitHub and runs it at once,
    with your user rights. Everything the script downloads afterwards is checked against a signed
    manifest and SHA-256 hashes, but the script itself is not checked before it runs. If you want
    to read it first, use way B.

### Way B: download the files yourself

1. Open the [latest CAPIE release](https://github.com/capie-mods/capie/releases/latest) and
   download into one folder (for example `Downloads\CAPIE`): `CAPIE-1.5.0-win64.zip`,
   `install.ps1`, `release-manifest.json` and `release-manifest.json.sig`. Do not unpack the ZIP.
2. Open that folder in File Explorer, click the address bar, type `powershell` and press
   ++enter++. PowerShell opens in that folder.
3. Run:

    ```powershell
    powershell -ExecutionPolicy Bypass -File .\install.ps1 -Install -SteamLaunchOption -PackagePath .\CAPIE-1.5.0-win64.zip
    ```

4. The questions are plain text here. When asked "Add the selected loading method to the HOI4
   Steam launch options? [y/N]", type `y` and press ++enter++ (++enter++ alone means no). Answer
   the Steam questions as in way A.

## Step 3: enable both mods in your playset

1. Start the game from Steam (**Play**). The Paradox Launcher opens.
2. Open **Playsets** and enable both **Rename Anything** and **CAPIE** in the playset you play with.
   The order does not matter.
3. Close the Paradox Launcher.

The CAPIE mod is the on/off switch: CAPIE loads only when the CAPIE mod is enabled in the playset
you start the game with.

## Step 4: start the game the right way

1. Start the game with **Play in Steam**. This runs the CAPIE launcher, which opens the Paradox
   Launcher as usual.
2. In the Paradox Launcher pick the playset with both mods and press **Play**.
3. Wait in the main menu for about **20 seconds** after it appears. CAPIE loads after the main
   menu is ready, never earlier.

!!! warning "These starts do not load CAPIE"

    - Pressing Play in a Paradox Launcher that was **already open** before you pressed Play in
      Steam. Close the Paradox Launcher completely first.
    - The game's own desktop shortcut, a shortcut to `dowser.exe` or `hoi4.exe`, or starting the
      game from the Paradox Launcher's library.

## Step 5: check that CAPIE is running

1. In the main menu, the CAPIE mark appears when the CAPIE mod is enabled. Its tooltip only says
   the switch is on; it does not prove CAPIE loaded.
2. Start or load a game. Open **Decisions**, find the Rename Anything category and take
   **Rename characters**. The name editor opens; switch to its **Country** tab.
3. A line near the bottom of that tab shows **CAPIE 1.5 loaded** when CAPIE runs. **CAPIE
   missing: Rename Anything needs it** means it did not load; go to
   [If it does not work](#troubleshooting). With CAPIE running you also see pencils next to the
   country and leader names in the Politics panel.

## If it does not work { #troubleshooting }

### First: read the launcher log

Everything the CAPIE launcher decides is written to
`%LOCALAPPDATA%\RenameAnything\launcher.log`. Press ++win+r++, paste
`%LOCALAPPDATA%\RenameAnything`, press ++enter++ and open `launcher.log`. Read the lines from the
last start:

| Line in the log | Meaning | What to do |
|---|---|---|
| No new lines at all, or no `launcher.log` | the game was not started through the CAPIE launcher | check the Steam launch option (below) and start with Play in Steam |
| `playset disabled: CAPIE mod not enabled in the playset` | the CAPIE mod was off in the playset you started | enable the CAPIE mod (step 3) |
| `playset unknown: ...` | `dlc_load.json` could not be read | start once from the Paradox Launcher with your playset, then try again |
| `game ... sha256=...` as a warning, and a "not supported" notice | your game build is not 1.19.4.0 from Steam | see [Wrong game version](#wrong-version) |
| `bundle check failed` | CAPIE files are damaged or changed (often by an antivirus) | run the setup again and choose Install or update |
| `no game appeared in the started tree in time` | the game was started by another, already open Paradox Launcher | close the Paradox Launcher, then Play in Steam |
| `CAPIE loaded into pid=...` | CAPIE is running | if the mod still says missing, wait 20 s in the main menu and reopen the editor |

### "CAPIE missing" although both mods are enabled

Go through these in order and test after each one:

1. Check the Steam launch option: Steam, Library, right-click Hearts of Iron IV,
   Properties, General, **Launch Options**. It must contain
   `"...\RenameAnything\current\RenameAnythingLauncher.exe" %command%`. If it is empty, the setup
   could not change it because Steam was running: close Steam completely (Steam menu, **Exit**,
   not the window's X), run the setup again, choose **1 Install or update**, and answer yes to
   the Steam questions.
2. If you have several Steam accounts: the launch option is set per account. Run the setup again and
   pick the account you play on (or `A`).
3. Close every Paradox Launcher window, also the one in the tray next to the clock, then press Play
   in Steam.
4. Wait 20 seconds in the main menu before you load a game.
5. Look for a local copy of either mod in `Documents\Paradox Interactive\Hearts of Iron IV\mod`
   and remove it or rename it in its `descriptor.mod`.
6. Check your antivirus. Some antivirus programs block or quarantine CAPIE, because it loads itself
   into the game. Look in your antivirus history for `RenameAnythingLauncher.exe`,
   `capie_core.dll`, `capie_editor.dll` or `capie_injector.exe`, restore them, add
   `%LOCALAPPDATA%\RenameAnything` as an exception, and run the setup again.
7. If none of this helps, use the [alternative method](#proxy).

### The setup does not offer to change the launch options

- The Steam step needs a Steam installation the tool can find. If Steam is installed in an
  unusual place, run way B with `-SteamRoot "D:\Path\To\Steam"`.
- If you answered no, or Steam did not close within 60 seconds, the step was skipped. Close
  Steam yourself (Steam menu, Exit) and run the setup again.
- You can also set it by hand: in Launch Options type the line above, with the full path of
  `RenameAnythingLauncher.exe` in `%LOCALAPPDATA%\RenameAnything\current`, followed by
  ` %command%`.

### PowerShell errors

- "Running scripts is disabled on this system" means you ran `.\install.ps1` directly. Use the
  `powershell -ExecutionPolicy Bypass -File .\install.ps1 ...` line from way B, or way A.
- If Windows blocks the downloaded file, run
  `Unblock-File .\install.ps1` in the same folder, then try again.
- "irm is not recognized" means you are in the old Command Prompt (`cmd`), not PowerShell. Open
  Windows PowerShell as in step 2.
- If the signature or hash check fails, the download was incomplete or changed. Delete the files,
  download them again, and do not mix files from different releases.

### Wrong game version { #wrong-version }

CAPIE 1.5.1 works only with Hearts of Iron IV 1.19.4.0 from Steam (CAPIE 1.5.0 only with 1.19.3.0). On any other build, including a
beta branch, the game starts without CAPIE and the CAPIE-free features still work. In Steam,
Properties, **Betas**, choose "None". A yellow "not supported" warning in the Paradox Launcher's
mod list compares the mod's `supported_version` with your game and does not by itself stop
anything; the version in the main menu is what counts.

### Alternative method: proxy loader { #proxy }

If the launcher method does not work for you, CAPIE can be loaded by a `version.dll` next to
`hoi4.exe` instead. This method adds one file to the game folder, does not need the Steam launch
option and does not use the CAPIE mod as a switch: while it is installed, CAPIE loads in every
game you start.

1. Run the setup once more and choose **Uninstall**, so the two methods do not overlap.
2. Download the release files as in way B and run, in that folder:

    ```powershell
    powershell -ExecutionPolicy Bypass -File .\install.ps1 -Install -PackagePath .\CAPIE-1.5.0-win64.zip -LoadMethod Proxy -ProxyActivation Config
    ```

3. Start the game any way you like. Its log is `%LOCALAPPDATA%\RenameAnything\proxy.log`.

If the setup cannot write to the game folder, run PowerShell as administrator for this step. The
setup never replaces a `version.dll` it did not install; if another mod or tool already has one
there, this method cannot be used.

To switch it off, delete `%LOCALAPPDATA%\RenameAnything\proxy.enabled`, or uninstall.

### Still stuck

Open an issue on [GitHub](https://github.com/capie-mods/rename-anything/issues) or comment on the
Workshop page with:

- your game version from the main menu,
- what the Steam launch options contain,
- `launcher.log` (and `bootstrap.log` from the same folder if the setup failed).

The logs contain paths and process ids, never names you typed.

## Multiplayer

CAPIE has not been tested in multiplayer. Before you play multiplayer, disable the CAPIE mod in
your playset, or run the setup and choose **Disable** (removes CAPIE from the Steam launch
options; files stay).

## Updates

CAPIE never updates itself. Run the one-line command again and choose **1 Install or update**. The
previous version stays on disk; running the downloaded script with `-Rollback` (as in way B)
switches back to it.

## Uninstall

1. Run the one-line command and choose **Uninstall**. It removes CAPIE and puts your Steam launch
   options back as they were. Nothing in the game folder needs repairing (with the proxy method
   it removes its own `version.dll` only).
2. Unsubscribe from Rename Anything and CAPIE on the Workshop.

Names you set stay in the saves you made. To drop a custom country name, use **Restore name** in
the game before you remove the mod. Continuing an old save without the mod was not tested; try it
on a copy.

## Without CAPIE { #without-capie }

On macOS, on Linux, on an unsupported game version, or when you just do not want the native part,
Rename Anything still works for states, cities (victory points) and generals, admirals and
advisers (decision "Rename characters", typed on an on-screen keyboard). The pencils for your
country, leader and parties, renaming subjects and factions, and flags need CAPIE and stay hidden.
