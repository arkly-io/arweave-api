"""Arkly Arweave unit tests"""

import pytest

from src.arweave_api.arweave_utilities import ar_to_winston, winston_to_ar


@pytest.mark.parametrize(
    "winston_input, ar_expected",
    [
        # Arweave given examples.
        ("1000000000000", 1.0),
        ("1", 0.000000000001),
        # Arweave client given example.
        (938884, 0.000000938884),
        # Examples from arconverter.com.
        ("12000000000000", 12.0),
        ("3142000000000", 3.142),
        ("204123000000000000", 204123.0),
        ("13893997435210", 13.893997435210),
    ],
)
def test_winston_conversion(winston_input: str, ar_expected: str):
    """Test the conversion from Winston to AR in the API."""
    res = winston_to_ar(winston_input)
    assert res == ar_expected


@pytest.mark.parametrize(
    "ar_input, winston_expected",
    [
        # Arweave given examples.
        ("1.000000000000", 1000000000000),
        ("0.000000000001", 1),
        # Arweave client given example.
        ("0.000000938884", 938884),
        # Examples from arconverter.com.
        ("12.000000000000", 12000000000000),
        ("3.142", 3142000000000),
        ("204123", 204123000000000000),
        (0.000212017846, 212017846),
    ],
)
def test_ar_conversion(ar_input: str, winston_expected):
    """Test the conversion from Ar to Winstons in the API."""
    res = ar_to_winston(ar_input)
    assert res == winston_expected
