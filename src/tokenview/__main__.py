"""Allow `python -m tokenview`."""

from __future__ import annotations

import sys

from tokenview.cli import main

if __name__ == "__main__":
    sys.exit(main())
