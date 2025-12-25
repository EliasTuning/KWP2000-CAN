"""
Convenience namespace package.

Allows importing project modules under the `kwp2000_can.*` prefix to avoid
conflicting with similarly named packages. All modules are forwarded to the
existing implementation packages.
"""

# Re-export selected subpackages for convenience
from interface import *  # noqa: F401,F403
from protocols import *  # noqa: F401,F403

__all__ = []

