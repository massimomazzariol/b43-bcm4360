#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Write the files a patch creates (--- /dev/null hunks) into a directory.

usage: new-files-from-patch.py <outdir> <patch>...
Only new files are written; the path components after b/ are dropped,
so drivers/net/wireless/broadcom/b43/foo.c becomes <outdir>/foo.c.
"""
import os
import re
import sys


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for patch in sys.argv[2:]:
        lines = open(patch).read().split("\n")
        i = 0
        while i < len(lines):
            if lines[i] == "--- /dev/null" and lines[i + 1].startswith("+++ b/"):
                name = os.path.basename(lines[i + 1][6:])
                m = re.match(r"@@ -0,0 \+1(?:,(\d+))? @@", lines[i + 2])
                n = int(m.group(1) or 1)
                body = [l[1:] for l in lines[i + 3:i + 3 + n]]
                assert all(l.startswith("+") for l in lines[i + 3:i + 3 + n]), name
                open(os.path.join(out, name), "w").write("\n".join(body) + "\n")
                i += 3 + n
            else:
                i += 1


if __name__ == "__main__":
    main()
