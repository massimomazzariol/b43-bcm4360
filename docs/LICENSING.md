# Licensing

This repository contains patches to Linux b43 (as shipped in the OpenWrt
mac80211/backports package), a patch to OpenWrt, original tooling and
tests, and documentation.  Different parts carry different licenses; the
SPDX tag of each file is authoritative.

## Summary

- **Project's own work: GPL-2.0-or-later.**  New driver files, tools,
  tests, documentation and patch headers written for this project.  "Or
  later" keeps them usable in GPL-3.0 projects too.
- **Driver code**: each file created or modified by the patches keeps
  the license of the file it belongs to — GPL-2.0-or-later or
  GPL-2.0-only (`GPL-2.0` in older SPDX notation) as tagged.  The b43
  module as a whole is distributed under GPL-2.0 (the module declares
  `MODULE_LICENSE("GPL")`).
- **OpenWrt packaging patch**: GPL-2.0-only, the license of OpenWrt.
- **Tools and tests**: GPL-2.0-or-later.
- **No third-party code** other than Linux b43 and OpenWrt is included.
  No hardware data and no firmware are included.

License texts: [../LICENSES/](../LICENSES/).

## Why GPL-2.0

The driver patches modify and extend Linux b43, which is licensed
GPL-2.0-or-later (C files) and GPL-2.0-only (headers, Kconfig, Makefile),
and are built inside OpenWrt, which is GPL-2.0-only.  GPL-2.0-only is the
license under which all of these combine, so it is the repository
default.  Files inherited from b43 keep their original tags; nothing is
relicensed.  GPL-3.0 is not used anywhere: it is not compatible with the
GPL-2.0-only parts of b43 and OpenWrt.

## Matrix

Origin: **Linux b43** = file from Linux `drivers/net/wireless/broadcom/b43/`
as shipped in backports 6.18.26; **new** = file created by this project.

### Driver patches (`patches/mac80211/brcm/`)

| Patch | File(s) in b43 | Origin | License (SPDX) | Attribution required | Notes |
|---|---|---|---|---|---|
| 820 | `xmit.c` | Linux b43, upstream fix | GPL-2.0-or-later | Tristan Madani (author), upstream Linux commit 1f4f78bf8549 | backport, unchanged |
| 900 | `radio_2069.c`, `radio_2069.h` | new | GPL-2.0-or-later | Massimo Mazzariol | |
| 901 | `tables_phy_ac.c` | new | GPL-2.0-or-later | Massimo Mazzariol | |
| 901 | `tables_phy_ac.h` | new | GPL-2.0-or-later | Massimo Mazzariol | |
| 902 | `phy_ac.c` | Linux b43, modified | GPL-2.0-or-later | Rafał Miłecki (original), Massimo Mazzariol (additions) | both copyright notices kept |
| 902 | `phy_ac.h` | Linux b43, modified | GPL-2.0 (only) | b43 authors | |
| 902 | `bcm4360.h` | new | GPL-2.0-or-later | Massimo Mazzariol | |
| 902 | `Kconfig` | Linux b43, modified | GPL-2.0-only | b43 authors | |
| 902 | `Makefile` | Linux b43, modified | GPL-2.0 (only) | b43 authors | |
| 903 | `dma.c` | Linux b43, modified | GPL-2.0-or-later | Michael Buesch, David S. Miller, Pekka Pietikainen (notices kept) | |
| 903 | `dma.h` | Linux b43, modified | GPL-2.0 (only) | b43 authors | |
| 904 | `main.c` | Linux b43, modified | GPL-2.0-or-later | Martin Langer, Stefano Brivio, Michael Buesch, Danny van Dyk, Andreas Jaggi, Rafał Miłecki (notices kept) | |
| 904 | `xmit.c` | Linux b43, modified | GPL-2.0-or-later | Martin Langer, Stefano Brivio, Michael Buesch, Danny van Dyk, Andreas Jaggi (notices kept) | |
| 904 | `b43.h` | Linux b43, modified | GPL-2.0 (only) | b43 authors | |
| 904 | `bcm4360_board.c` | new | GPL-2.0-or-later | Massimo Mazzariol | |
| 905 | `bcm4360_data_fw.c` | new | GPL-2.0-or-later | Massimo Mazzariol | |

A patch file is distributed under the license of the file it modifies;
its context lines are upstream b43 code under that file's license.

### OpenWrt (`patches/openwrt/`)

| File | Origin | License | Attribution required | Notes |
|---|---|---|---|---|
| `0001-mac80211-add-B43_PHY_AC-config-option.patch` | modifies OpenWrt `package/kernel/mac80211/broadcom.mk` | GPL-2.0-only | OpenWrt project | new menu option only |

### Tools and tests

| Path | Origin | License | Notes |
|---|---|---|---|
| `tools/apply-to-openwrt.sh` | new | GPL-2.0-or-later | |
| `tools/passive-scan-check.sh` | new | GPL-2.0-or-later | runs on the router |
| `tests/data-loader/*` | new | GPL-2.0-or-later | builds `bcm4360_data_fw.c` from patch 905 with user-space stand-ins for kernel APIs (`shim/`); generates synthetic test data only |

### Documentation

| Path | Origin | License |
|---|---|---|
| `README.md`, `docs/*.md` | new | GPL-2.0-or-later |
| `LICENSES/*` | FSF license texts | verbatim, unmodified |

## Image assets

Image-specific copyright, attribution and licensing information is
documented in [images/README.md](images/README.md).

Original project photographs and the validation screenshot are project
documentation assets.

The external ASUS RT-AC68U photograph is a derivative of a Wikimedia
Commons image licensed under CC BY-SA 2.0. That image retains its
Creative Commons license and is not relicensed under the GPL.

## Not included

- **Hardware data** (chip/radio and board data packages): not part of
  this repository; see [HARDWARE-DATA.md](HARDWARE-DATA.md).
- **b43 microcode**: provided by OpenWrt's b43 firmware packaging at
  build time; not part of this repository.
- **Code from other experimental AC-PHY projects**: none.  Alessio
  Ferri's b43-ac-wip (GPL-3.0) is acknowledged as prior work and was
  used only as a technical reference.
