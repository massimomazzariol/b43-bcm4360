#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Install the patch series into an OpenWrt source tree.
#
# usage: tools/apply-to-openwrt.sh <openwrt-tree>
#
# Copies patches/mac80211/brcm/*.patch into
# package/kernel/mac80211/patches/brcm/ (the OpenWrt build applies them to
# backports when it prepares the mac80211 package) and applies the
# packaging patch patches/openwrt/*.patch to the OpenWrt tree itself.
# Stops if a patch with the same name already exists or does not apply.
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
OW=${1:?usage: $0 <openwrt-tree>}
DEST=$OW/package/kernel/mac80211/patches/brcm

[ -f "$OW/package/kernel/mac80211/broadcom.mk" ] || {
	echo "$OW does not look like an OpenWrt tree" >&2
	exit 1
}

for p in "$HERE"/patches/mac80211/brcm/*.patch; do
	if [ -e "$DEST/$(basename "$p")" ]; then
		if cmp -s "$p" "$DEST/$(basename "$p")"; then
			echo "present:   $(basename "$p")"
			continue
		fi
		echo "$DEST/$(basename "$p") exists and differs; not overwriting" >&2
		exit 1
	fi
done

for p in "$HERE"/patches/openwrt/*.patch; do
	if patch -d "$OW" -p1 -R --dry-run -s -f < "$p" >/dev/null 2>&1; then
		echo "applied:   $(basename "$p") (already)"
	else
		patch -d "$OW" -p1 --dry-run -s < "$p"
		patch -d "$OW" -p1 -s < "$p"
		echo "applied:   $(basename "$p")"
	fi
done

for p in "$HERE"/patches/mac80211/brcm/*.patch; do
	[ -e "$DEST/$(basename "$p")" ] && continue
	cp "$p" "$DEST/"
	echo "installed: $(basename "$p")"
done
