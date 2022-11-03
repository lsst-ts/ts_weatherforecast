try:
    from .version import *
except ImportError:
    __version__ = "?"

from .csc import *
