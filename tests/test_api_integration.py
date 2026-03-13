"""Arkly Arweave API integration tests"""

import json
from pathlib import Path, PosixPath
from typing import Final

import pytest
import requests
import vcr

# Location to record VCR cassettes to replay API requests/responses.
VCR_FIXTURES_PATH: Final[Path] = Path("tests/fixtures/vcrpy/")

# Wallet name will need to exist when VCR cassettes are re-recorded.
WALLET_NAME: Final[Path] = Path("myWallet.json")

# If desired this can be changed to the remote server, but it should
# normally always be Localhost.
TESTING_BASE_URL: Final[str] = "http://0.0.0.0:8000"

# Timeout as used in the main codebase.
REQ_TIMEOUT: Final[int] = 30


@pytest.fixture(name="mock_wallet")
def create_wallet(tmp_path: PosixPath) -> PosixPath:
    """Create a mock wallet for running this code remotely, i.e. on a
    continuous integration server where interaction with Arweave or
    vcrpy is neither wanted or desired.
    A wallet is still required for re-recording unit tests locally and
    so if it exists, the wallet itself is passed as a fixture to the
    tests.
    """
    wallet = Path(WALLET_NAME)
    if wallet.exists():
        return wallet
    file_name = tmp_path / "myWallet.json"
    file_name.write_text("sample-wallet-data")
    return file_name


@pytest.fixture(name="arkly_test_file")
def create_arkly_test_file(tmp_path: PosixPath) -> PosixPath:
    """Generate mock test data for running this code remotely and for
    storage in our test packages.
    """
    test_data_filename: Final[str] = "test-data.txt"
    test_file = tmp_path / test_data_filename
    test_file.write_text("Arkly test data")
    return test_file


def _scrub_wallet_data(replace=True):
    """Ensure that wallet data is removed from vcrpy requests."""

    def before_record_request(request):
        if not replace:
            # View the raw request data for debugging purposes. Will only
            # work when the cassette is re-recorded.
            return request
        request.body = "substitute: my_wallet.json -- form-data"
        return request

    return before_record_request


def test_check_balance(mock_wallet: PosixPath):
    """Testing the check_balance endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_check_balance.yaml"))
    ):
        with open(str(mock_wallet), "rb") as my_file:
            files = {"wallet": (str(WALLET_NAME), my_file)}
            resp = requests.post(
                url=f"{TESTING_BASE_URL}/check_wallet_balance/",
                files=files,
                timeout=REQ_TIMEOUT,
            )
            json_response = json.loads(resp.text)
            assert isinstance(json_response["ar"], float)


def test_check_last_transaction(mock_wallet: PosixPath):
    """Testing the check_last_transaction endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_check_last_transaction.yaml"))
    ):
        with open(str(mock_wallet), "rb") as my_file:
            files = {"wallet": (str(WALLET_NAME), my_file)}
            resp = requests.post(
                url=f"{TESTING_BASE_URL}/check_wallet_last_transaction/",
                files=files,
                timeout=REQ_TIMEOUT,
            )
            assert resp.status_code == 200
            json_response = json.loads(resp.text)
            assert json_response["last_transaction_id"] != "Failure to get response..."
            for item in [
                "wallet_address",
                "last_transaction_id",
            ]:
                assert item in json_response.keys()


def test_estimate_transaction_cost():
    """Testing the estimate_transaction_cost endpoint"""

    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_estimate_transaction_cost.yaml"))
    ):
        data = {"size_in_bytes": "10000000000"}
        resp = requests.get(
            url=f"{TESTING_BASE_URL}/estimate_transaction_cost/",
            params=data,
            timeout=REQ_TIMEOUT,
        )
        json_response = json.loads(resp.text)
        assert isinstance(json_response["estimated_transaction_cost"], float)


def test_check_transaction_status():
    """Testing the estimate_transaction_cost endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_check_transaction_status.yaml"))
    ):
        tx_id = "cZiaojZtzyL1ZB7GjbWLbj62S_9pxPDHu61HQvSYgD0"
        resp = requests.get(
            url=f"{TESTING_BASE_URL}/check_transaction_status/?transaction_id={tx_id}",
            timeout=REQ_TIMEOUT,
        )
        json_response = json.loads(resp.text)
        # Modify variable aspects of the response. If they don't exist
        # will throw an error, correctly.
        json_response["block_height"] = 0
        json_response["number_of_confirmations"] = 0
        assert json_response == {
            "block_height": 0,
            "block_indep_hash": "dY4cRXBnrH3bhqEZnhqpveywsx5kFqrinysBcXc1OO2wx7Ys74_6rS2P2yRvdI7s",
            "number_of_confirmations": 0,
        }


def test_fetch_transaction():
    """Testing the fetch_upload route"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_fetch_transaction.yaml"))
    ):
        tx_id = "cZiaojZtzyL1ZB7GjbWLbj62S_9pxPDHu61HQvSYgD0"
        resp = requests.get(
            url=f"{TESTING_BASE_URL}/fetch_transaction/?transaction_id={tx_id}",
            timeout=REQ_TIMEOUT,
        )
        assert resp.text is not None
        assert resp.headers.get("content-type") == "application/x-tar"


def test_create_transaction(arkly_test_file: PosixPath, mock_wallet: PosixPath):
    """Testing out the create_transaction endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_create_transaction.yaml"))
    ):
        with open(str(mock_wallet), "rb") as my_wallet:
            with open(str(arkly_test_file), "rb") as sample_file:
                files = [
                    ("wallet", my_wallet),
                    ("files", sample_file),
                    {"tags", ""},
                ]
                resp = requests.post(
                    url=f"{TESTING_BASE_URL}/create_transaction/?package_file_name=test_upload",
                    files=files,
                    timeout=REQ_TIMEOUT,
                )
                assert resp.status_code == 200
                assert resp.text is not None
                for item in (
                    "transaction_id",
                    "transaction_link",
                    "transaction_status",
                    "wallet_balance",
                ):
                    assert item in resp.text


def test_validate_bag_valid_bag():
    """Ensure that validate arweave bag works as anticipated."""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_validate_arweave_bag_valid_bag.yaml"))
    ):
        data = {"transaction_id": "4vRsZM1JR491HJFPm_Nx08a7kp1_dJrc_sZC1X6afbg"}
        resp = requests.get(
            url=f"{TESTING_BASE_URL}/validate_arkly_bag/",
            params=data,
            timeout=REQ_TIMEOUT,
        )
        for item in ("transaction_url", "file_url", "valid", "bag_info"):
            assert item in resp.text


def test_validate_bag_invalid_bag():
    """Ensure that validate arweave bag works as anticipated."""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_validate_arweave_bag_invalid_bag.yaml"))
    ):
        data = {"transaction_id": "8zItHEd6sUbK8fop6KquIu6jEyu49kLgiZ73O7xu2OE"}
        resp = requests.get(
            url=f"{TESTING_BASE_URL}/validate_arkly_bag/",
            params=data,
            timeout=REQ_TIMEOUT,
        )
        for item in ("transaction_url", "file_url", "valid"):
            assert item in resp.text
        assert json.loads(resp.text)["valid"] == "UNKNOWN"
