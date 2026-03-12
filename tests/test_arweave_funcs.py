"""Test arweave functions."""

from dataclasses import dataclass

import pytest

from src.arweave_api import arweave_utilities


def test_weighted():
    """Test the weighted list."""

    weighted_dict = {
        "a": 5,
        "b": 1,
        "c": 2,
    }

    weighted_list = arweave_utilities.weighted_list(weighted_dict)
    assert weighted_list == ["a", "a", "a", "a", "a", "b", "c", "c"]


@dataclass
class Response:
    """Response mock."""

    status_code: int


gateway_tests = [
    (["http://abc", "http://def"], [Response(400), Response(200)], "http://def"),
    (["http://def", "http://hig"], [Response(500), Response(200)], "http://hig"),
    (["http://def", "http://hig"], [Response(200), Response(200)], "http://def"),
]


@pytest.mark.parametrize("choices, responses, result", gateway_tests)
def test_random_gateway(mocker, choices, responses, result):
    """Test the random retrieval of an Arweave gateway."""

    weighted_dict = {
        "http://abc": 5,
        "http://def": 1,
        "http://hig": 2,
    }

    mocker.patch("random.choice", side_effect=choices)
    mocker.patch("requests.head", side_effect=responses)
    b = arweave_utilities.retrieve_gateway(weighted_dict)
    assert b == result
    assert weighted_dict == {
        "http://abc": 5,
        "http://def": 1,
        "http://hig": 2,
    }
