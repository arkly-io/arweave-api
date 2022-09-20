"""Arkly Arweave unit tests"""

import pytest

from arweave_utilities import winston_to_ar


@pytest.mark.parametrize(
    "winston_input, ar_expected",
    [
        # Arweave given examples.
        ("1000000000000", "1.000000000000"),
        ("1", "0.000000000001"),
        # Arweave client given example.
        ("938884", "0.000000938884"),
    ],
)
def test_winston_conversion(winston_input: str, ar_expected: str):
    """Test the conversion from Winston to AR in the API."""
    res = winston_to_ar(winston_input)
    assert res == ar_expected
