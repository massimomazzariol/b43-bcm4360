# Validation

Two different things are validated, and they are reported separately:

- **A. Source build validation** - the published patch series builds
  without any hardware data.
- **B. Hardware functional validation** - with the required hardware
  data supplied locally, the driver receives on the tested router.

Network identities in all examples below are synthetic.  Raw logs are not
published.

## A. Source build validation

Performed on the release-candidate tree (2026-09-26).

| Check | Result |
|---|---|
| patches applied to backports 6.18.26 with the OpenWrt 25.12.5 mac80211 `build/`, `subsys/` and `brcm/` patches | 7/7 apply without fuzz or rejects |
| packaging patch applied to OpenWrt 25.12.5 `package/kernel/mac80211/broadcom.mk` | applies |
| `tools/apply-to-openwrt.sh` on an OpenWrt 25.12.5 package tree | installs 7 patches, applies the packaging patch; second run is a no-op |
| b43 compiled and linked in the OpenWrt 25.12.5 build environment (bcm53xx, GCC 14.3.0, Linux 6.12.94, backports config with `B43_PHY_AC=y`), `W=1` | 0 errors, 0 compiler warnings; `b43.ko` linked; the only modpost message is *missing MODULE_DESCRIPTION()*, which unmodified b43 produces as well |
| hardware data required for the build | none |
| `checkpatch.pl` on the series | 0 errors; remaining notes: `udelay` (hardware timing), one split string copied from existing b43 code, file-list change |
| `tests/data-loader/run.sh` (loader from patch 905, host build with AddressSanitizer/UBSan, synthetic packages) | 31/31 pass: round trip of all sections, and rejection of a missing package, bad CRC, wrong size, unknown ABI, wrong kind, wrong chip/radio identity, wrong board tag, truncated file, misaligned/out-of-range/overlapping/duplicate sections, non-zero reserved bytes, unknown mandatory section, missing or mis-shaped sections, channel rows out of order, malformed RF-sequencer records, out-of-range board values |

Not done: a complete OpenWrt image build from a fresh clone of
OpenWrt 25.12.5 with these patches (the compile check above used an
already configured OpenWrt 25.12.5 build environment).

## B. Hardware functional validation

The exact release-candidate implementation was tested on real hardware on
2026-09-27. The required hardware-data files were supplied locally through
the file-based loader and are not part of this repository.

Network identities and raw scan captures are not published.

### Test setup

| | |
|---|---|
| Board | ASUS RT-AC68U |
| Chip | BCM4360 rev 3, D11 core rev 42 |
| PHY / radio | AC-PHY rev 1 (analog rev 12), BCM2069 rev 4 |
| Software | OpenWrt 25.12.5, Linux 6.12.94, mac80211 backports 6.18.26 |
| b43 microcode | 784.2 |
| RC module SHA256 | `0deab632d5494b028b1f760e39150248c0f00c14d19f6475b9b9126a521660d5` |
| Module loading | manual `insmod` from a clean driver state |
| Hardware data | supplied locally through the file-based `request_firmware()` loader |
| Test mode | managed interface, passive scanning only |

Before loading the release-candidate module, `b43` was not loaded and no
wireless PHY was registered.

### Exact RC result

| Check | Result |
|---|---|
| release-candidate module load | PASS (`insmod` returned 0) |
| BCM4360 D11 core rev 42 detected | PASS |
| AC-PHY rev 1 detected | PASS |
| BCM2069 rev 4 detected | PASS |
| second BCM4360 / 5 GHz device | rejected with `-95` as intended |
| interface types | managed, monitor |
| 2.4 GHz channels | 14 |
| channels flagged NO_IR | 14 / 14 |
| 5 GHz channels exposed | 0 |
| direct passive scans | 5 / 5 successful |
| validation-helper passive scans | 5 / 5 successful |
| validation-helper channel matches | 50 / 50 BSS entries, 0 mismatches |
| validation-helper scan time | 1.74-1.90 s |
| direct scan time | 2.04-2.23 s |
| `tx_packets` before / after validation | 0 / 0 |
| microcode TX counter before / after validation | `0x0000` / `0x0000` |
| link state after validation | not connected |
| associated stations | 0 |
| validation-helper result | PASS |

The exact RC scan captures contained and were successfully decoded for the
following information-element classes where advertised by nearby access
points:

- SSID;
- RSN;
- WPA;
- HT capabilities and operation;
- VHT capabilities and operation;
- HE capabilities.

All BSS entries inspected by the validation helper were reported on the
channel advertised by their HT operation information.

### Sanitized validation-helper output

```text
phy: phy0  kernel: 6.12.94
dmesg: b43-phy0: Broadcom 4360 WLAN found (core revision 42)
dmesg: b43-phy0: Found PHY: Analog 12, Type 11 (AC), Revision 1
dmesg: b43-phy0: Found Radio: Manuf 0x17F, ID 0x2069, Revision 4, Version 0
interface modes: managed monitor
channels: 2.4 GHz=14 5 GHz=0 NO_IR=14
scan 1: rc=0 time=1.74s bss=10 match=10 mismatch=0
scan 2: rc=0 time=1.90s bss=10 match=10 mismatch=0
scan 3: rc=0 time=1.82s bss=10 match=10 mismatch=0
scan 4: rc=0 time=1.87s bss=10 match=10 mismatch=0
scan 5: rc=0 time=1.90s bss=10 match=10 mismatch=0
tx_packets: before=0 after=0
RESULT: PASS
```

No SSIDs or BSSIDs from the test environment are included above.

### Receive-only restrictions

The validated implementation is deliberately constrained:

- all exposed channels are NO_IR;
- active scanning is disabled;
- frames passed to the transmit path are dropped;
- no transmit DMA ring is created;
- the 5 GHz BCM4360 device is rejected;
- boards other than the validated RT-AC68U profile are rejected;
- the test interface remained unassociated;
- both observed transmit counters remained unchanged at zero throughout
  passive-scan validation.

### Known bring-up messages

The validated configuration emits known bring-up messages:

- the second, 5 GHz BCM4360 is deliberately rejected with error `-95`;
- BCM2069 rev 4 calibration may report completion-not-observed notices on
  the three radio cores;
- a known b43 warning backtrace is emitted during wireless-core
  initialisation because the existing b43 AC-PHY support does not provide
  the corresponding rate-table initialisation.

These messages did not prevent passive receive operation during the
validated run.
