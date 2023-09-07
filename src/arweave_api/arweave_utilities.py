"""Low-level Arweave API utility functions."""


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
