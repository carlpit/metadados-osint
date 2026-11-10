"""Allow ``python -m metascan``."""

from __future__ import annotations

from metascan.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
