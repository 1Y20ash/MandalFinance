"""Validate production configuration without connecting to external services."""

import os

from app.config import validate_production_environment


if __name__ == '__main__':
    validate_production_environment(os.environ)
    print('Production configuration preflight: PASS')
