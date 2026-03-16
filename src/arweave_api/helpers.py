"""Application helpers."""

import os
from typing import Final

NOPUBLISH: Final[str] = "NOPUBLISH"
DEBUG: Final[str] = "DEBUG"
FSLIMIT: Final[str] = "MAX_FILESIZE_BYTES"


def _get_env_bool(value: str) -> bool:
    """Get our environment variables reliably."""
    return (
        os.getenv(value, "false").lower() == "true"
        or os.getenv(value, "false").lower() == "1"
    )


def _get_env_int(value: str) -> int:
    """Get reliable integer environment variables."""
    return int(os.getenv(value, 0))


def get_nopublish():
    """Get nopublish from the environment if it is set."""
    return _get_env_bool(NOPUBLISH)


def get_debug():
    """Get debug from the environment if it is set."""
    return _get_env_bool(DEBUG)


def get_f_limit():
    """Get filesize limit from the environment."""
    return _get_env_int(FSLIMIT)
