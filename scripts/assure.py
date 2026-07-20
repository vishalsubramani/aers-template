#!/usr/bin/env python3
"""Entrypoint for the AERS assurance layer: `python3 scripts/assure.py --help`.

Additive to `scripts/aers.py`; reuses the engine read-only and never issues
VERIFIED. Kept out of the protected control-plane surface on purpose.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aers_assure.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
