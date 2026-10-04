#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Host test of the BCM4360 hardware-data loader, built from the loader
# source contained in the patch series (no kernel tree needed).
# Requires: cc (gcc or clang), python3.  Uses only synthetic test data.
set -eu
export PYTHONDONTWRITEBYTECODE=1
HERE=$(cd "$(dirname "$0")" && pwd)
PATCHES=$HERE/../../patches/mac80211/brcm
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
python3 "$HERE/new-files-from-patch.py" "$WORK/src" \
	"$PATCHES"/902-*.patch "$PATCHES"/905-*.patch
SAN="-fsanitize=address,undefined"
${CC:-cc} -std=gnu11 -Wall -Wextra -Wno-unused-parameter $SAN -g \
	-DCPTCFG_B43_PHY_AC -I"$HERE/shim" -I"$WORK/src" \
	-o "$WORK/loadtest" "$HERE/loadtest.c" "$WORK/src/bcm4360_data_fw.c"
python3 "$HERE/run-tests.py" "$WORK/loadtest"
