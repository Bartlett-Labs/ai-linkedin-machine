#!/usr/bin/env python3
"""
Enable running the image optimizer as a module:
    python -m image_optimizer <args>
"""

from .cli import main
import sys

if __name__ == '__main__':
    sys.exit(main())
