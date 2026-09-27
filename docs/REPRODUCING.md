# Reproducing

How to build the driver from this repository and run the receive test on
an ASUS RT-AC68U.  The build needs nothing beyond OpenWrt and this
repository; running the radio additionally needs the hardware data
packages, which are not distributed (see
[HARDWARE-DATA.md](HARDWARE-DATA.md)).

## Supported baseline

| Component | Version |
|---|---|
| OpenWrt | 25.12.5 (git tag `v25.12.5`) |
| Target | `bcm53xx` / `generic`, device ASUS RT-AC68U |
| Kernel | Linux 6.12.94 (as shipped by OpenWrt 25.12.5) |
| mac80211 | backports 6.18.26 (OpenWrt package `mac80211`) |
| b43 microcode | 784.2, from the OpenWrt b43 firmware option *6.30.163.46* |

The patches are OpenWrt mac80211 package patches; they are not tested
against other OpenWrt releases or against a mainline kernel tree.

## Required tools

- the OpenWrt build prerequisites for 25.12 (see the OpenWrt
  documentation for your distribution);
- `git`, `patch`, a POSIX shell;
- for the host tests only: a C compiler with AddressSanitizer/UBSan
  support (gcc or clang) and `python3`.

## 1. Apply the patches

```sh
git clone https://git.openwrt.org/openwrt/openwrt.git
cd openwrt
git checkout v25.12.5
/path/to/this/repo/tools/apply-to-openwrt.sh .
```

`apply-to-openwrt.sh` copies `patches/mac80211/brcm/*.patch` into
`package/kernel/mac80211/patches/brcm/` and applies
`patches/openwrt/0001-mac80211-add-B43_PHY_AC-config-option.patch` to
`package/kernel/mac80211/broadcom.mk`.  OpenWrt applies the mac80211
patches to backports itself when it builds the package, after its own
`build/`, `subsys/` and `brcm/` patches (810-815 are OpenWrt's own b43
patches; 820 and 900-905 come from this repository).

## 2. Configure

`make menuconfig`, or add to `.config` and run `make defconfig`:

```
CONFIG_TARGET_bcm53xx=y
CONFIG_TARGET_bcm53xx_generic=y
CONFIG_TARGET_bcm53xx_generic_DEVICE_asus_rt-ac68u=y
CONFIG_PACKAGE_kmod-b43=y
CONFIG_B43_FW_6_30=y
CONFIG_B43_FW_SQUASH_COREREVS="5,6,7,8,9,10,11,13,15,16,28,29,30,42"
CONFIG_B43_FW_SQUASH_PHYTYPES="G,N,LP,HT,AC"
CONFIG_PACKAGE_B43_PHY_AC=y
```

The BCM4360 is D11 core revision 42 with an AC-PHY, so the firmware
squash lists must include `42` and `AC` (or squashing must be
disabled); otherwise `b43/ucode42.fw` is not installed.

## 3. Build

```sh
make -j"$(nproc)"
```

The image in `bin/targets/bcm53xx/generic/` contains `kmod-b43` with
this driver and the b43 microcode.  To rebuild only the driver after a
change: `make package/kernel/mac80211/{clean,compile} V=s`.

No hardware data is needed for any of these steps.

## 4. Host tests (optional)

```sh
/path/to/this/repo/tests/data-loader/run.sh
```

Builds the data loader from patch 905 on the host and checks it with
synthetic packages.  Expected result: `31/31 passed`.

## 5. Install and run on the router

1. Install the image built above.
2. Put the two hardware data packages into `/lib/firmware/b43/`
   (file names in [HARDWARE-DATA.md](HARDWARE-DATA.md)).
3. Load the driver (the `kmod-b43` package also loads it at boot):

   ```sh
   modprobe b43
   dmesg | grep -E 'b43|bcma'
   ```

   Expected: `Broadcom 4360 WLAN found (core revision 42)`, AC-PHY
   revision 1, radio 0x2069 revision 4 for `b43-phy0`, and
   `probe with driver b43 failed with error -95` for the second
   (5 GHz) BCM4360.

4. Run the check (copy `tools/passive-scan-check.sh` to the router):

   ```sh
   sh passive-scan-check.sh
   ```

   It verifies the registered wiphy (managed/monitor only, 14 NO_IR
   channels, no 5 GHz), runs five passive scans and prints, per scan, the
   duration, the number of BSS, their frequencies and whether each BSS was
   received on the primary channel it advertises, plus the TX packet
   counter.  It prints no SSIDs or BSSIDs.  Expected: `RESULT: PASS`.

   Individual scans can be run with `iw dev bcmscan scan`.

## Without the hardware data

With the patches installed but without the data packages, `modprobe b43`
succeeds and other b43 devices work as before; the BCM4360 2.4 GHz device
is not initialised.  Expected log (message text from the loader source;
this path is covered by the host tests, not yet by a hardware run of
this build):

```
b43 bcma1:1: BCM4360: hardware data package b43/bcm4360-ac1-2069r4.bin not available (-2); device not initialized
```

and its probe fails with error -2.  Nothing is programmed on the device
(the PMU PLL setup is skipped as well).

## Known messages

- `WARNING: ... b43_rate_memory_init` with a backtrace when the interface
  comes up: b43 has no rate table for the AC-PHY.  Harmless for
  reception.
- `BCM2069 rev4 calibration completion not observed on core N after 10
  polls; continuing`: up to three per bring-up.
