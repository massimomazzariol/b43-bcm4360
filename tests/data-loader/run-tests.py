#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Host tests for the b43 BCM4360 data loader.

Generates synthetic data packages (test identity chip 0x0001 / radio
0x0001, patterned values; they match no real device), writes them with
bdata_write.py and loads them with the loadtest harness, which runs the
unmodified loader source.  Checks the round trip and every rejection
path.

usage: run-tests.py <loadtest binary>
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bdata_write  # noqa: E402

CHIP, PHY_REV, RADIO, RADIO_REV, CORES, TAG = 0x0001, 1, 0x0001, 4, 3, "testbrd"
CHIP_FILE = "b43/bcm4360-ac1-2069r4.bin"
BOARD_FILE = "b43/bcm4360-board-test.bin"


def chip_spec():
    rows = []
    for ch in range(1, 15):
        rows += [ch] + [(ch * 100 + w) & 0xffff for w in range(1, 58)]
    rfseq = [0x20, 3, 1, 2, 3, 0x90, 2, 4, 5]
    return {"kind": "chip", "chip_id": CHIP, "phy_rev": PHY_REV,
            "radio_ver": RADIO, "radio_rev": RADIO_REV, "sections": [
                {"id": 0x0105, "elem_bits": 32, "values": [0x10000 + i for i in range(22)]},
                {"id": 0x0101, "elem_bits": 16, "values": rfseq},
                {"id": 0x0102, "elem_bits": 16, "values": [0x100, 1, 0x101, 2]},
                {"id": 0x0103, "elem_bits": 16, "values": rows},
                {"id": 0x0104, "elem_bits": 16, "values": list(range(28))},
                {"id": 0x0106, "elem_bits": 8, "values": list(range(59))},
                {"id": 0x0107, "elem_bits": 8, "mandatory": False, "values": [9, 8, 7, 6, 5, 4]},
            ]}


def board_spec():
    return {"kind": "board", "chip_id": CHIP, "phy_rev": PHY_REV,
            "radio_ver": RADIO, "radio_rev": RADIO_REV, "board_tag": TAG,
            "sections": [
                {"id": 0x0201, "elem_bits": 8, "values": [i & 0xff for i in range(96)]},
                {"id": 0x0202, "elem_bits": 16, "values": [12, 20] + list(range(0x100, 0x10b))},
            ]}


def sect(spec, sid):
    return next(s for s in spec["sections"] if s["id"] == sid)


def run(loadtest, chip, board, raw_chip=None, raw_board=None):
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "b43"))
        for name, spec, raw in ((CHIP_FILE, chip, raw_chip), (BOARD_FILE, board, raw_board)):
            if spec is None and raw is None:
                continue
            data = raw if raw is not None else bdata_write.build(spec)
            open(os.path.join(d, name), "wb").write(data)
        p = subprocess.run([loadtest, d, hex(CHIP), str(PHY_REV), hex(RADIO),
                            str(RADIO_REV), str(CORES), BOARD_FILE, TAG],
                           capture_output=True, text=True)
        return p.stdout.strip()


def main():
    lt = sys.argv[1]
    ok = run(lt, chip_spec(), board_spec())
    checks = [
        ("round trip", "rfseq7 id=7 offset=0x0090 width=16 count=2: 0004 0005" in ok
         and "chan_2g[13]: 000e" in ok and "rx_evm_lo: 09 08 07" in ok
         and "elna_gain_db 12 trloss_db 20" in ok and "init id=5" in ok),
    ]

    def expect(name, result, want):
        checks.append((f"{name}: {result!r}", result == want))

    def chip_mod(fn):
        c = chip_spec()
        fn(c)
        return c

    def board_mod(fn):
        b = board_spec()
        fn(b)
        return b

    E = {"ENOENT": "error -2", "EINVAL": "error -22", "ENODEV": "error -19",
         "EBADMSG": "error -74", "EOPNOTSUPP": "error -95", "EBUSY": "error -16"}
    expect("chip package missing", run(lt, None, board_spec()), E["ENOENT"])
    expect("board package missing", run(lt, chip_spec(), None), E["ENOENT"])
    expect("bad CRC", run(lt, chip_mod(lambda c: c.update(crc_xor=1)), board_spec()), E["EBADMSG"])
    expect("total_len mismatch", run(lt, chip_mod(lambda c: c.update(total_len=12)), board_spec()), E["EBADMSG"])
    expect("unknown ABI version", run(lt, chip_mod(lambda c: c.update(abi=2)), board_spec()), E["EINVAL"])
    expect("wrong kind (board file as chip)", run(lt, board_spec(), board_spec()), E["EINVAL"])
    expect("wrong chip identity", run(lt, chip_mod(lambda c: c.update(chip_id=0x4360)), board_spec()), E["ENODEV"])
    expect("wrong radio revision", run(lt, chip_mod(lambda c: c.update(radio_rev=3)), board_spec()), E["ENODEV"])
    expect("wrong board tag", run(lt, chip_spec(), board_mod(lambda b: b.update(board_tag="other"))), E["ENODEV"])
    expect("truncated file", run(lt, None, board_spec(), raw_chip=bdata_write.build(chip_spec())[:40]), E["EBADMSG"])
    expect("short file", run(lt, None, board_spec(), raw_chip=b"B43D"), E["EINVAL"])
    expect("misaligned section", run(lt, chip_mod(lambda c: sect(c, 0x0104).update(offset_delta=2)), board_spec()), E["EINVAL"])
    expect("section beyond end", run(lt, chip_mod(lambda c: sect(c, 0x0107).update(offset_delta=4096)), board_spec()), E["EINVAL"])
    expect("overlapping sections", run(lt, chip_mod(lambda c: sect(c, 0x0104).update(offset_delta=-4)), board_spec()), E["EINVAL"])
    expect("reserved bytes set", run(lt, chip_mod(lambda c: sect(c, 0x0102).update(reserved=[1, 0, 0])), board_spec()), E["EINVAL"])
    expect("duplicate section", run(lt, chip_mod(lambda c: c["sections"].append(copy.deepcopy(sect(c, 0x0104)))), board_spec()), E["EINVAL"])
    expect("unknown mandatory section", run(lt, chip_mod(lambda c: c["sections"].append({"id": 0x01f0, "elem_bits": 16, "values": [1]})), board_spec()), E["EOPNOTSUPP"])
    ext = run(lt, chip_mod(lambda c: c["sections"].append({"id": 0x01f0, "mandatory": False, "elem_bits": 16, "values": [1]})), board_spec())
    checks.append(("unknown optional section ignored", ext == ok))
    expect("mandatory section missing", run(lt, chip_mod(lambda c: c["sections"].remove(sect(c, 0x0106))), board_spec()), E["ENOENT"])
    expect("wrong section shape", run(lt, chip_mod(lambda c: sect(c, 0x0104)["values"].pop()), board_spec()), E["ENOENT"])
    expect("wrong element size", run(lt, chip_mod(lambda c: sect(c, 0x0105).update(elem_bits=16, values=[v & 0xffff for v in sect(c, 0x0105)["values"]])), board_spec()), E["ENOENT"])
    expect("channel rows out of order", run(lt, chip_mod(lambda c: sect(c, 0x0103)["values"].__setitem__(58, 5)), board_spec()), E["EINVAL"])
    expect("RF-sequencer record overrun", run(lt, chip_mod(lambda c: sect(c, 0x0101)["values"].__setitem__(1, 40)), board_spec()), E["EINVAL"])
    expect("RF-sequencer empty record", run(lt, chip_mod(lambda c: sect(c, 0x0101)["values"].__setitem__(1, 0)), board_spec()), E["EINVAL"])
    expect("odd radio-default count", run(lt, chip_mod(lambda c: sect(c, 0x0102)["values"].pop()), board_spec()), E["ENOENT"])
    expect("RX EVM wrong shape", run(lt, chip_mod(lambda c: sect(c, 0x0107)["values"].pop()), board_spec()), E["EINVAL"])
    no_evm = run(lt, chip_mod(lambda c: c["sections"].remove(sect(c, 0x0107))), board_spec())
    checks.append(("RX EVM optional", "rx_evm none" in no_evm and "error" not in no_evm))
    expect("FEM table core count", run(lt, chip_spec(), board_mod(lambda b: sect(b, 0x0201)["values"].pop())), E["ENOENT"])
    expect("eLNA gain out of range", run(lt, chip_spec(), board_mod(lambda b: sect(b, 0x0202)["values"].__setitem__(0, 300))), E["EINVAL"])
    expect("board RX gain missing", run(lt, chip_spec(), board_mod(lambda b: b["sections"].pop())), E["ENOENT"])

    failed = 0
    for name, good in checks:
        print(("PASS  " if good else "FAIL  ") + name)
        failed += not good
    print(f"{len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
