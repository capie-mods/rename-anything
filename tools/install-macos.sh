#!/bin/zsh
# Installs the development build of Rename Anything for Hearts of Iron IV on macOS.
#
#   tools/install-macos.sh            # register mod/ from this checkout
#   tools/install-macos.sh --copy     # copy mod/ into the HOI4 user folder instead
#   tools/install-macos.sh --uninstall
#
# It writes one descriptor, <HOI4 user folder>/mod/rename_anything_dev.mod, and with --copy
# one folder next to it. Nothing in the game folder is changed. CAPIE does not run on macOS,
# so the mod runs in its script-only mode (states, cities, characters).
set -euo pipefail

readonly DESCRIPTOR_NAME='Rename Anything (dev)'
readonly DESCRIPTOR_FILE='rename_anything_dev.mod'
readonly COPY_DIR='rename_anything_dev'
readonly TESTED_VERSION='1.19.3.0'

user_dir="${HOI4_USER_DIR:-$HOME/Documents/Paradox Interactive/Hearts of Iron IV}"
game_dir="${HOI4_GAME_DIR:-$HOME/Library/Application Support/Steam/steamapps/common/Hearts of Iron IV}"
repo_mod="${0:A:h:h}/mod"
mod_dir="$user_dir/mod"
descriptor="$mod_dir/$DESCRIPTOR_FILE"

die() { print -u2 -- "error: $*"; exit 1; }

# Refuse to touch a descriptor this script did not write.
check_ownership() {
  [[ -e $descriptor ]] || return 0
  grep -qxF "name=\"$DESCRIPTOR_NAME\"" "$descriptor" ||
    die "$descriptor exists and was not written by this script; leaving it alone"
}

warn_game_version() {
  local settings="$game_dir/launcher-settings.json" version
  if [[ ! -f $settings ]]; then
    print "note: HOI4 not found in $game_dir (set HOI4_GAME_DIR if it is elsewhere)"
    return
  fi
  version=$(sed -n 's/.*"rawVersion": *"\([^"]*\)".*/\1/p' "$settings")
  [[ $version == "$TESTED_VERSION" ]] ||
    print "warning: game version is ${version:-unknown}; Rename Anything was tested on $TESTED_VERSION only"
}

install() {
  local copy=$1 target
  [[ $(uname -s) == Darwin ]] || die "this installer is for macOS"
  [[ -f $repo_mod/descriptor.mod && -d $repo_mod/common ]] || die "no mod/ folder next to tools/ ($repo_mod)"
  check_ownership
  warn_game_version
  mkdir -p "$mod_dir"
  if (( copy )); then
    target="$mod_dir/$COPY_DIR"
    rm -rf "$target.tmp"
    cp -R "$repo_mod" "$target.tmp"
    rm -rf "$target"
    mv "$target.tmp" "$target"
  else
    target=$repo_mod
  fi
  local version
  version=$(sed -n 's/^version="\([^"]*\)"/\1/p' "$repo_mod/descriptor.mod")
  cat >"$descriptor.tmp" <<EOF
name="$DESCRIPTOR_NAME"
path="$target"
version="${version:-0.1.0}"
supported_version="1.19.*"
picture="thumbnail.png"
tags={
	"Utilities"
	"Gameplay"
}
EOF
  mv "$descriptor.tmp" "$descriptor"
  print "Installed: $descriptor"
  print "Mod files:  $target"
  print "Next: open the Paradox Launcher, add \"$DESCRIPTOR_NAME\" to a playset and press Play."
}

uninstall() {
  check_ownership
  rm -f "$descriptor"
  rm -rf "$mod_dir/$COPY_DIR"
  print "Removed $descriptor (and $mod_dir/$COPY_DIR if it existed)."
  print "Names you set stay in the saves you made."
}

case "${1:-}" in
  '') install 0 ;;
  --copy) install 1 ;;
  --uninstall) uninstall ;;
  -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) die "unknown option $1 (use --copy, --uninstall or --help)" ;;
esac
