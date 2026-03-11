"""Application helpers."""

import os
from typing import Final

NOPUBLISH: Final[str] = "NOPUBLISH"
DEBUG: Final[str] = "DEBUG"


def _get_env_bool(value: str) -> bool:
    """Get our environment variables reliably."""
    return (
        os.getenv(value, "false").lower() == "true"
        or os.getenv(value, "false").lower() == "1"
    )


def get_nopublish():
    """Get nopublish from the environment if it is set."""
    return _get_env_bool(NOPUBLISH)


def get_debug():
    """Get debug from the environment if it is set."""
    return _get_env_bool(DEBUG)
