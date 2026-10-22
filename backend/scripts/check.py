from __future__ import annotations

import sys

def main() -> int:
    print("ok", sys.version)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())