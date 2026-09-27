# Hardware data packages

The BCM4360 receive path needs hardware-specific data that is **not
distributed with this repository**: chip/radio data for the BCM4360 with
AC-PHY rev 1 and BCM2069 rev 4, and board data for the ASUS RT-AC68U.
This repository does not contain the data and does not provide a way to
generate it.

The driver loads the data at probe time with `request_firmware()` and
validates it completely before the device is touched.  This document
describes where the packages are expected, what happens without them
and the package format (the interface implemented by
`bcm4360_data_fw.c`, patch 905).

## Location

| Package | Path on the router |
|---|---|
| chip/radio | `/lib/firmware/b43/bcm4360-ac1-2069r4.bin` |
| board (ASUS RT-AC68U) | `/lib/firmware/b43/bcm4360-board-asus-rt-ac68u.bin` |

The board package name comes from the board profile in
`bcm4360_board.c`; the chip/radio package never contains board data and
vice versa.

## Behaviour

| Situation | Result |
|---|---|
| no board profile matches (device tree, SPROM ID, NVRAM) | the device is rejected (`-EOPNOTSUPP`); no data is loaded |
| a package is missing | `BCM4360: hardware data package ... not available (-2); device not initialized`; the device is rejected |
| a package is invalid (identity, size, CRC, layout, section shape) | `BCM4360: hardware data package ... rejected (<error>); device not initialized`; the device is rejected |
| both packages valid | the data sets are kept in memory until the module is unloaded |

The check runs from the bcma probe, before the PMU baseband PLL is
programmed, and again at attach.  There is no fallback to partial,
default or zero-filled data.  Other b43 devices are not affected.

## Format (ABI version 1)

All multi-byte fields are little-endian.

### Header (32 bytes)

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | magic `B43D` |
| 4 | 2 | ABI version = 1 |
| 6 | 2 | kind: 1 = chip/radio, 2 = board |
| 8 | 2 | chip ID (0x4360) |
| 10 | 1 | PHY type (11 = AC) |
| 11 | 1 | PHY revision (1) |
| 12 | 2 | radio ID (0x2069) |
| 14 | 1 | radio revision (4) |
| 15 | 1 | number of sections (1..32) |
| 16 | 4 | total length = file size |
| 20 | 4 | CRC-32 (IEEE 802.3, as `crc32_le(~0, ...) ^ ~0`) of bytes 24..end |
| 24 | 8 | board tag, NUL padded (board package: the profile's tag, `rt-ac68u`; chip/radio package: all zero) |

The identity fields must equal the board profile the package is loaded
for.

### Section table (16 bytes per section, directly after the header)

| Offset | Size | Field |
|---|---|---|
| 0 | 2 | section ID |
| 2 | 2 | flags: bit 0 = mandatory; other bits must be 0 |
| 4 | 1 | element size in bits: 8, 16 or 32 |
| 5 | 3 | reserved, 0 |
| 8 | 4 | payload offset from the start of the file, 4-byte aligned, after the section table |
| 12 | 4 | number of elements (> 0) |

Payloads must lie inside the file and must not overlap; section IDs must
be unique.  Unknown sections are ignored unless they are flagged
mandatory, in which case the package is rejected.

### Chip/radio sections (kind 1)

| ID | Name | Elements | Count | Content |
|---|---|---|---|---|
| 0x0101 | RFSEQ7 | 16 bit | variable (≤ 256) | records `{offset, count, data[count]}` written to AC-PHY table 7 after the RX LPF update (≤ 16 records) |
| 0x0102 | PREFREGS | 16 bit | even (≤ 128) | `{radio register, value}` pairs written at radio power-up |
| 0x0103 | CHAN_2G | 16 bit | 14 × 58 | one row per channel 1..14 in order; word 0 is the channel number, words 2..51 are written to the radio registers listed in `radio_2069.c`, words 52..57 are the RX SFO words |
| 0x0104 | FARROW_2G | 16 bit | 28 | `{deltaphase_lo, deltaphase_hi}` per channel 1..14 |
| 0x0105 | PHASETRACK | 32 bit | 22 | AC-PHY table 0x05, written once before the first channel set |
| 0x0106 | RX_GAIN_TABLES | 8 bit | 59 | `struct b43_bcm4360_rx_gain_tables` in declaration order: LNA1 gain/bits/limit (6 each), LNA2 gain/bits/limit (7 each), mixer gain/bits (10 each) |
| 0x0107 | RX_EVM | 8 bit | 6 | optional; AC-PHY table 4 entries at 0x01 (3) and 0x3d (3) |

All sections except RX_EVM are mandatory.

### Board sections (kind 2)

| ID | Name | Elements | Count | Content |
|---|---|---|---|---|
| 0x0201 | FEM_LUT | 8 bit | 32 × cores (3) | front-end control table (AC-PHY table 0x0a), one block per receive core |
| 0x0202 | RX_GAIN | 16 bit | 13 | eLNA gain (dB, ≤ 255), T/R switch loss (dB, ≤ 127), gain codes A[5], gain codes B[5] (init, high, mid, low, clip2), RF-sequencer init gain |

Both are mandatory.

## Tests

`tests/data-loader/run.sh` builds the loader from patch 905 on the host
and checks it with synthetic packages (a test identity that matches no
real device): the round trip of every section and each rejection case
listed above.
