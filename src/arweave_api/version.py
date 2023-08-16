"""Provide information about the Arkly Arweave Version"""

from importlib.metadata import PackageNotFoundError, version


def get_version():
    """Returns a version string to the caller."""
    semver = "0000.00.00.0000"
    __version__ = f"{semver}-dev"
    try:
        __version__ = version("arweave-api")
    except PackageNotFoundError:
        # package is not installed
        pass
    return __version__
