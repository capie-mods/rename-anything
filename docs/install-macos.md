# Installing Rename Anything on macOS

The macOS installer installs the script-only version of Rename Anything. Its file operations
were tested in a temporary folder; gameplay on macOS has not been checked. CAPIE,
the native library behind the in-place text fields, has no working macOS release yet,
so the mod is designed to hide features that need it
([ADR-0006](adr/0006-script-only-fallback.md)).

## Expected script-only behavior (not yet checked in the game on macOS)

| Feature | On macOS |
|---|---|
| States and cities (victory points) | Script-only path available; macOS gameplay unverified |
| Generals, admirals, advisers (decision "Rename characters") | Script-only on-screen keyboard; macOS gameplay unverified |
| Your country's name and adjective, flag | No, needs CAPIE |
| Leader and party names in the Politics panel | No, needs CAPIE |
| Subjects and factions | No, needs CAPIE |

The reference gameplay tests target HOI4 1.19.3.0 on Windows. No gameplay test has been
performed on macOS. Both versions read the same script; equivalent behavior is an expectation,
not a macOS test result.

## CAPIE port status

The native macOS port is in development. A controlled HOI4 launch loaded a read-only
diagnostic library and passed 240 checks of the static address profile; this did not activate
CAPIE or test Rename Anything gameplay. The target is the Steam x86_64 executable
for HOI4 1.19.3.0, SHA-256
`09419b087f8b4656c00df337bf838ff34c9b1d816b76cef5383ae6a4ac15b1fb`.
There is no validated macOS CAPIE dylib, loader or native installer to install with this script.
Do not copy Windows DLLs into the app bundle or treat an offline test as an in-game result.
Native installation instructions will be added only after the loader and game adapters work.

## Requirements

- Hearts of Iron IV 1.19.3.0 from Steam.
- The game started at least once, so `~/Documents/Paradox Interactive/Hearts of Iron IV/` exists.
  The installer creates the `mod` folder inside it if needed.
- A checkout of this repository (`git clone https://github.com/capie-mods/rename-anything.git`).

## Install

From the repository folder:

```bash
tools/install-macos.sh
```

This writes `rename_anything_dev.mod` into your HOI4 `mod` folder. The descriptor points at the
`mod/` folder of your checkout, so a `git pull` updates the mod. If you want the mod to stay put
when you move or delete the checkout, copy it instead:

```bash
tools/install-macos.sh --copy
```

Then open the Paradox Launcher, add "Rename Anything (dev)" to a playset and press Play. No game
file and no `dlc_load.json` entry is changed by the installer.

If your game or user folder is somewhere else, set `HOI4_GAME_DIR` or `HOI4_USER_DIR` before
running the script.

## Uninstall

```bash
tools/install-macos.sh --uninstall
```

This removes the descriptor and the copied folder, if any. Names you set stay in your saves.
Continuing an old save without the mod was not tested; try it on a copy.

## Troubleshooting

- **The launcher does not list the mod.** Check that
  `~/Documents/Paradox Interactive/Hearts of Iron IV/mod/rename_anything_dev.mod` exists and that
  its `path` points to a folder containing `descriptor.mod` and `common/`.
- **The installer refuses to overwrite the descriptor.** A file with that name exists and was not
  written by the script. Rename or remove it yourself.
- **"game version is …" warning.** The reference gameplay tests were on Windows 1.19.3.0.
  Other versions and macOS gameplay are unverified.

## Shared Windows and macOS release

The completed port must ship in the same versioned GitHub Release as Windows.
That release must retain the existing Windows configuration and package and add
the macOS configuration and package. Follow the installation instructions for your
operating system; both sets of instructions must point to the same release.
This is a release requirement, not a claim that native macOS artifacts are available today.

The CAPIE repository now builds native macOS parent/child launcher executables without
requiring Python at runtime. A real Paradox Launcher test delivered the unchanged active
playset to a harmless recorder; this did not activate CAPIE. Its separately packaged
launcher component explicitly reports `runtime_ready:false` and provides no script API.
It is not a native installer or a replacement for the complete macOS release asset.
The script-only installer above remains unchanged. The complete CAPIE release must still
ship Windows and macOS together, with separate platform instructions and trusted manifests.
