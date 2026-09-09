"""Validate production configuration without connecting to external services."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ProductionConfig


if __name__ == '__main__':
    ProductionConfig.validate()
    print('Production configuration preflight: PASS')
