#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
#
# Router-side check of the receive-only BCM4360 device (busybox sh).
#
# Run after the b43 module has been loaded.  Verifies the registered
# wiphy (station/monitor only, 2.4 GHz only, every channel NO_IR), runs
# passive scans on a managed interface and reports, per scan, the result
# code, duration and number of BSS entries, the frequencies they were
# received on, whether each BSS was received on the primary channel it
# advertises (HT Operation element) and the TX packet counter.
#
# No SSID or BSSID is printed.
#
# Environment: PHY (default: first phy), IF (default: bcmscan),
#              SCANS (default: 5), IW (default: iw)
set -u
IW=${IW:-iw}
IF=${IF:-bcmscan}
SCANS=${SCANS:-5}
PHY=${PHY:-$(ls /sys/class/ieee80211 2>/dev/null | head -n 1)}
fail=0

say() { echo "$*"; }
bad() { echo "FAIL: $*"; fail=1; }

[ -n "$PHY" ] || { echo "FAIL: no wireless phy registered"; exit 1; }
say "phy: $PHY  kernel: $(uname -r)"
dmesg | grep -E 'b43-phy[0-9]+: (Broadcom 4360|Found PHY|Found Radio)' | sed 's/^\[[^]]*\] /dmesg: /'

info=$($IW phy "$PHY" info)
modes=$(echo "$info" | sed -n '/Supported interface modes:/,/^\t[A-Z]/p' | grep '\* ' | sed 's/.*\* //' | tr '\n' ' ')
say "interface modes: $modes"
for m in $modes; do
	case "$m" in managed|monitor) ;; *) bad "unexpected interface mode $m" ;; esac
done

chans=$($IW phy "$PHY" channels)
n2=$(echo "$chans" | grep -c ' 24[0-9][0-9]\(\.0\)\? MHz')
n5=$(echo "$chans" | grep -c ' 5[0-9][0-9][0-9]\(\.0\)\? MHz')
nir=$(echo "$chans" | grep -c 'No IR')
say "channels: 2.4 GHz=$n2 5 GHz=$n5 NO_IR=$nir"
[ "$n5" -eq 0 ] || bad "5 GHz channels exposed"
[ "$n2" -gt 0 ] && [ "$nir" -eq "$n2" ] || bad "not every 2.4 GHz channel is NO_IR"

if ! [ -e "/sys/class/net/$IF" ]; then
	$IW phy "$PHY" interface add "$IF" type managed || { bad "cannot create $IF"; exit 1; }
fi
ip link set "$IF" up || { bad "cannot bring $IF up"; exit 1; }
tx0=$(cat "/sys/class/net/$IF/statistics/tx_packets")

out=/tmp/passive-scan-check.$$
i=1
while [ "$i" -le "$SCANS" ]; do
	t0=$(cut -d' ' -f1 /proc/uptime)
	$IW dev "$IF" scan > "$out" 2>&1
	rc=$?
	t1=$(cut -d' ' -f1 /proc/uptime)
	# Per BSS: received frequency and advertised HT primary channel.
	summary=$(awk '
		function ch(f) { return f == 2484 ? 14 : (f - 2407) / 5 }
		function flush() {
			if (!seen) return
			n++; freqs[f]++
			if (p == "") nop++
			else if (p == ch(f)) ok++
			else mis++
		}
		/^BSS / { flush(); seen = 1; f = ""; p = "" }
		/^\tfreq:/ { f = $2 + 0 }
		/primary channel:/ { p = $NF + 0 }
		END {
			flush()
			printf "bss=%d match=%d mismatch=%d no_ht_op=%d freqs=", n, ok, mis, nop
			for (k in freqs) printf "%s:%d,", k, freqs[k]
		}' "$out")
	dur=$(awk -v a="$t0" -v b="$t1" 'BEGIN { printf "%.2f", b - a }')
	say "scan $i: rc=$rc time=${dur}s $summary"
	[ "$rc" -eq 0 ] || bad "scan $i failed"
	case "$summary" in *mismatch=0*) ;; *) bad "scan $i: BSS received off its advertised channel" ;; esac
	i=$((i + 1))
done
rm -f "$out"

tx1=$(cat "/sys/class/net/$IF/statistics/tx_packets")
say "tx_packets: before=$tx0 after=$tx1"
[ "$tx0" -eq "$tx1" ] || bad "tx_packets changed"

[ "$fail" -eq 0 ] && say "RESULT: PASS" || say "RESULT: FAIL"
exit "$fail"
