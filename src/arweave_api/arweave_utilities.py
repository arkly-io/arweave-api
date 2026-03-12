"""Low-level Arweave API utility functions."""

import copy
import logging
import random
from typing import Final

import requests

logger = logging.getLogger(__name__)


# Gateways on ar network with some indication of health/liveliness:
# https://gateways.ar.io/#/gateways
ARWEAVE_API_BASEURL: Final[str] = {
    "https://ar-io.dev": 8,
    "https://permagate.io": 5,
    "https://arweave.ar": 10,
    "https://zigza.xyz": 6,
}


def winston_to_ar(winston: str) -> float:
    """Convert Winstons to Ar.

    Winstons are the smallest possible unit of Ar.

    1 AR = 1000000000000 Winston (12 zeros) and 1 Winston = 0.000000000001 AR.
    The Arweave HTTP API will return all amounts as Winston strings,
    this is to allow for easy interoperability between environments that
    do not accommodate arbitrary-precision arithmetic.

    Ar is the more human-readable format.
    """
    winston = f"{winston}"  # ensure that the supplied value is a string.
    length = len(winston)
    if length > 12:
        past_twelve = length - 12
        return float(f"{winston[0:past_twelve]}.{winston[-12:]}")
    less_than_twelve = 12 - length
    less_than_format = "0" * less_than_twelve
    return float(f"0.{less_than_format}{winston}")


def ar_to_winston(arweave_ar: float) -> int:
    """Convert Ar to Winstons."""
    return int(float(arweave_ar) * 1000000000000.0)


def weighted_list(values: dict) -> list:
    """Return a weighted list."""
    new_list = []
    for key, value in values.items():
        new_list = new_list + [key] * value
    return new_list


def retrieve_gateway(gateways: dict = None) -> str:
    """Return a gateway to use to upload packages."""
    if gateways is None:
        gateways = ARWEAVE_API_BASEURL
    # Reassign the list as a deep copy so that it is indepotent.
    gateways = copy.deepcopy(gateways)
    weighted_choices = weighted_list(gateways)
    gateway = random.choice(weighted_choices)
    try:
        resp = requests.head(gateway, timeout=10)
    except requests.exceptions.ConnectionError as err:
        logger.error("error requesting url: %s (%s)", gateway, err)
        gateways.pop(gateway)
        return retrieve_gateway(gateways)
    if resp.status_code != 200:
        gateways.pop(gateway)
        return retrieve_gateway(gateways)
    return gateway
