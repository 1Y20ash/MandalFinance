"""Validate production configuration without connecting to external services."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import validate_production_environment


if __name__ == '__main__':
    validate_production_environment(os.environ)
    print('Production configuration preflight: PASS')
