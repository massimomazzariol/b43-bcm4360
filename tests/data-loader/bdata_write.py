#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Write a BCM4360 data package (ABI version 1) from a JSON description.

Test tooling for the b43 BCM4360 data loader (bcm4360_data_fw.c).  The
JSON gives the package identity and its sections; every value is taken
from the JSON as-is.

  {"kind": "chip" | "board", "chip_id": 17248, "phy_rev": 1,
   "radio_ver": 8297, "radio_rev": 4, "board_tag": "",
   "sections": [{"id": 257, "mandatory": true, "elem_bits": 16,
                 "values": [...]}]}

Optional per-section keys for negative tests: "offset_delta" (shift the
payload offset), "reserved" (non-zero reserved bytes).
"""
import json
import struct
import sys
import zlib

HDR_LEN, SECT_LEN, CRC_START = 32, 16, 24
KINDS = {"chip": 1, "board": 2}
FMT = {8: "B", 16: "H", 32: "I"}


def build(spec):
    sects = spec["sections"]
    n = len(sects)
    off = HDR_LEN + n * SECT_LEN
    table, payload = b"", b""
    for s in sects:
        off = (off + 3) & ~3
        data = struct.pack("<%d%s" % (len(s["values"]), FMT[s["elem_bits"]]),
                           *s["values"])
        pad = (off - HDR_LEN - n * SECT_LEN) - len(payload)
        payload += b"\0" * pad + data
        table += struct.pack("<HHB3sII", s["id"],
                             1 if s.get("mandatory", True) else 0,
                             s["elem_bits"], bytes(s.get("reserved", [0, 0, 0])),
                             off + s.get("offset_delta", 0), len(s["values"]))
        off += len(data)
    tag = spec.get("board_tag", "").encode()[:8].ljust(8, b"\0")
    body = table + payload
    total = HDR_LEN + len(body)
    hdr_head = struct.pack("<4sHHHBBHBBI", b"B43D", spec.get("abi", 1),
                           KINDS[spec["kind"]], spec["chip_id"], 11,
                           spec["phy_rev"], spec["radio_ver"], spec["radio_rev"],
                           n, spec.get("total_len", total))
    crc = zlib.crc32(tag + body) & 0xffffffff
    crc ^= spec.get("crc_xor", 0)
    return hdr_head + struct.pack("<I", crc) + tag + body


def main():
    spec = json.load(open(sys.argv[1]))
    open(sys.argv[2], "wb").write(build(spec))


if __name__ == "__main__":
    main()
