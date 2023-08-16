"""Low-level Arweave API utility functions."""


def winston_to_ar(winston: str) -> str:
    """Convert Winstons to Ar.

    Winstons are the smallest possible unit of Ar.

    1 AR = 1000000000000 Winston (12 zeros) and 1 Winston = 0.000000000001 AR.
    The Arweave HTTP API will return all amounts as Winston strings,
    this is to allow for easy interoperability between environments that
    do not accommodate arbitrary-precision arithmetic.

    Ar is the more human-readable format.
    """
    length = len(winston)
    if length > 12:
        past_twelve = length - 12
        return f"{winston[0:past_twelve]}.{winston[-12:]}"
    lessthan_twelve = 12 - length
    less_than_format = "0" * lessthan_twelve
    return f"0.{less_than_format}{winston}"
