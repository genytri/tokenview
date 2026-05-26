"""tokenview — visibility into Claude Code token consumption."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("tokenview")
except PackageNotFoundError:
    # Importing from a checkout without an editable install: rare, but
    # surface a clearly-not-a-real-version sentinel rather than crashing.
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
