"""Test our helpers."""

import os
from typing import Final

import pytest

from src.arweave_api import helpers

ENV_TEST: Final[str] = "TEST"

env_tests = [
    ("true", True),
    ("false", False),
    ("TRUE", True),
    ("1", True),
    ("0", False),
    ("DATA", False),
]


@pytest.fixture(scope="function", autouse=True)
def reset_env():
    """Ensure our environment variables are reset."""
    os.environ[ENV_TEST] = ""


@pytest.mark.parametrize("value, result", env_tests)
def test_get_env(value: str, result: bool):
    """Ensure that get_env works."""
    assert isinstance(result, bool), "test for result should be against a bool"
    assert helpers._get_env_bool(ENV_TEST) is False
    os.environ[ENV_TEST] = value
    assert helpers._get_env_bool(ENV_TEST) is result


env_tests_int = [
    ("1", 1),
    ("0", 0),
    ("-1", -1),
    ("None", 0),
    ("test", 0),
    ("False", 0),
]


@pytest.mark.parametrize("value, result", env_tests_int)
def test_get_env_int(value: str, result: bool):
    """Ensure that get_env works."""
    assert isinstance(result, int), "test for result should be against a bool"
    assert helpers._get_env_int(ENV_TEST) == 0
    os.environ[ENV_TEST] = value
    assert helpers._get_env_int(ENV_TEST) is result
