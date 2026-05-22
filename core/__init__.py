"""
Core package cho JKAI v3 - Shared library
"""

from .logger import setup_logger
from .exceptions import *

__version__ = "6.0"
__all__ = ["setup_logger"]