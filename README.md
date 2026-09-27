# BCM4360 receive support for b43 / OpenWrt

Experimental, receive-only BCM4360 support for the Linux **b43** driver on
OpenWrt, developed and validated on an **ASUS RT-AC68U**.

On the tested router the BCM4360 2.4 GHz radio comes up under b43,
registers with mac80211/cfg80211 and performs **passive 2.4 GHz scans**:
BSS advertisements are received on the correct channels and reported
with signal strength, and `iw` decodes their information elements.
The supported path is receive-only; transmission is disabled.

This is a personal engineering project.  It is not a complete BCM4360
driver and it is not intended for production use.

## Current status

| | |
|---|---|
| **Tested hardware** | ASUS RT-AC68U — BCM4360 (D11 core rev 42), AC-PHY rev 1, BCM2069 rev 4 radio, 2.4 GHz device (SPROM ID 0x43a1) |
| **Tested software** | OpenWrt 25.12.5, Linux 6.12.94, mac80211 backports 6.18.26, b43 microcode 784.2 |
| **Working** | module probe and attach · 2.4 GHz receive path · mac80211/cfg80211 integration · passive channel scanning (`iw dev <if> scan`) · BSS advertisement reception · per-frame channel and signal (dBm) reporting |
| **Intentionally disabled** | transmission · active scanning (all channels are NO_IR) · association and connectivity · AP, mesh and ad-hoc modes · 5 GHz · 40/80 MHz |
| **Not supported** | any board other than the RT-AC68U · other AC-PHY chips (e.g. BCM4352) · other radio revisions |

## Overview

Upstream b43 contains only a stub for AC-PHY devices (marked BROKEN).
This project adds, as OpenWrt mac80211 package patches:

- BCM2069 rev 4 radio support: power-up, reference/analog/VCO
  calibration and 2.4 GHz channel tuning;
- AC-PHY rev 1 receive path: carrier-search control, RX LPF, receive
  gain, clip and energy-detect settings, per-channel RX resampler;
- a BCM4360 D11 rev 42 receive DMA ring;
- receive-only device integration in b43/mac80211 with a board-profile
  gate, so that the receive path is initialised only on the tested hardware;
- a loader for the hardware data the receive path needs (see
  [Hardware data requirement](#hardware-data-requirement)).

## What works

On the tested RT-AC68U:

- `b43` loads, detects the BCM4360 (core rev 42), AC-PHY rev 1 and the
  BCM2069 rev 4 radio, and attaches the 2.4 GHz device; the router's
  second BCM4360 (the 5 GHz device, SPROM ID 0x43a2) is rejected;
- one wiphy is registered with station and monitor interface types and
  2.4 GHz channels 1–14, every channel flagged NO_IR (no initiated
  radiation);
- `iw dev <if> scan` completes a passive scan of all 14 channels in about
  2 seconds;
- BSS advertisements from real access points are received;
  mac80211/`iw` report SSID, security (RSN/WPA), HT, VHT and HE elements,
  signal level and frequency;
- every received BSS in the validation check was reported on the channel
  it advertises;
- transmit counters remained at zero before and after passive scanning.

Details and sanitized results: [docs/VALIDATION.md](docs/VALIDATION.md).

## What does not work

This is a receive-only driver by design:

- **no transmission**: frames handed to the driver for transmission are
  dropped, and no transmit DMA ring is created;
- **no active scanning**: all channels are NO_IR, so no probe requests
  are sent;
- **no association**, no network connectivity, no AP/mesh/ad-hoc mode;
- **no 5 GHz**, no 40/80 MHz channels;
- **one board only**: every other board and every other AC-PHY device is
  rejected before any PHY or radio access;
- receive sensitivity and throughput have not been characterised.

Known log messages on bring-up: a `b43_rate_memory_init` warning
backtrace (b43 has no AC-PHY rate table) and up to three "BCM2069 rev4
calibration completion not observed" notices.  Neither prevents
reception.

## Architecture

```
mac80211 / cfg80211
        │  passive scan, RX frames
b43 core (main.c, xmit.c) ── receive-only device: NO_IR channels,
        │                    station only, op_tx drops, RX IRQs only
        ├── dma.c            BCM4360 RX ring (2048 descriptors, 256 posted)
        ├── phy_ac.c         AC-PHY rev 1 receive path, channel switching
        │     ├── radio_2069.c   BCM2069 rev 4 power-up, calibration, tuning
        │     └── tables_phy_ac.c AC-PHY table access
        ├── bcm4360_board.c  board profiles (ASUS RT-AC68U only):
        │                    device tree, radio slot and NVRAM checks
        └── bcm4360_data_fw.c hardware data packages (request_firmware)
```

A BCM4360 device is initialised only if all of the following hold:

1. a board profile matches: device tree compatible `asus,rt-ac68u`, SPROM
   device ID 0x43a1, AC-PHY rev 1, BCM2069 rev 4, and NVRAM board data
   (crystal, front-end control, receive gains) equal to the profile;
2. both hardware data packages are present and pass validation.

Otherwise the device is rejected before the PMU, PHY or radio are
programmed.

## Building

The patches target **OpenWrt 25.12.5** (mac80211 package, backports
6.18.26) for the `bcm53xx` target.

```sh
git clone https://git.openwrt.org/openwrt/openwrt.git
cd openwrt && git checkout v25.12.5
/path/to/this/repo/tools/apply-to-openwrt.sh .
make menuconfig    # see below
make -j"$(nproc)"
```

`menuconfig`: target `Broadcom BCM47xx/53xx (ARM)`, device *ASUS
RT-AC68U*; `kmod-b43`; b43 firmware *784.2 from driver 6.30.163.46*;
enable *AC-PHY support*; add core revision `42` and PHY type `AC` to the
firmware squash lists (or disable squashing).  Full steps:
[docs/REPRODUCING.md](docs/REPRODUCING.md).

The loader can also be tested on a PC without OpenWrt:

```sh
tests/data-loader/run.sh
```

## Hardware data requirement

The receive path needs chip/radio and board-specific hardware data
(channel tuning rows, RF-sequencer entries, receive gain tables, the
board's front-end control table and similar).  **This data is not
distributed with this repository.**

The driver loads it at probe time from two data packages in the
firmware search path:

- `/lib/firmware/b43/bcm4360-ac1-2069r4.bin` (chip/radio)
- `/lib/firmware/b43/bcm4360-board-asus-rt-ac68u.bin` (board)

Without them the device is not initialised and the kernel log says so;
the rest of the system is unaffected.  The package format is documented
in [docs/HARDWARE-DATA.md](docs/HARDWARE-DATA.md).  Cloning this
repository alone does not provide a working radio.

## Validation

Two separate things are validated:

- **Source build**: the patch series applies to OpenWrt 25.12.5 and the
  b43 module compiles and links in the OpenWrt 25.12.5 build environment
  without any hardware data; the data loader passes its host test suite.
- **Hardware**: the exact release-candidate implementation, using its
  file-based hardware-data loader, was tested on the RT-AC68U from a
  clean driver state.  The driver probed successfully and completed passive
  2.4 GHz scans with no observed transmission.

See [docs/VALIDATION.md](docs/VALIDATION.md).

## Repository structure

```
patches/mac80211/brcm/  OpenWrt mac80211 package patches (820, 900-905)
patches/openwrt/        OpenWrt packaging patch (B43_PHY_AC menu option)
tools/                  apply-to-openwrt.sh, passive-scan-check.sh
tests/data-loader/      host tests for the hardware data loader
docs/                   REPRODUCING, VALIDATION, HARDWARE-DATA, LICENSING
LICENSES/               license texts
```

Patch 820 is a backport of an upstream Linux b43 fix (firmware key index
bounds check).

## Upstream and prior work

- **Linux b43** — the driver this work extends, by Martin Langer,
  Stefano Brivio, Michael Büsch, Gábor Stefanik, Rafał Miłecki and the
  other b43 contributors; the existing AC-PHY stub is by Rafał Miłecki.
  b43 is built on the bcm-specs documentation
  (bcm-specs.sipsolutions.net).
- **OpenWrt** — build system, mac80211 packaging and the b43 firmware
  packaging.
- **Alessio Ferri, b43-ac-wip** — earlier experimental AC-PHY work for
  b43.  It was used as a technical reference; no code from it is
  included here.

None of these projects endorses this work.

## License

GPL-2.0-only, with the exception of files and patches whose SPDX tags
say GPL-2.0-or-later (inherited from Linux b43 or chosen for new driver
files).  Each patch is distributed under the license of the file it
modifies.  See [LICENSE](LICENSE) and [docs/LICENSING.md](docs/LICENSING.md).
