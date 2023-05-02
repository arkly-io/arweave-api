"""Arkly Arweave API integration tests"""

import base64
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
TESTING_BASE_URL: Final[str] = "http://127.0.0.1:8000"


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
            files = {"file": (str(WALLET_NAME), my_file)}
            req = requests.post(url=f"{TESTING_BASE_URL}/check_balance/", files=files)
            json_response = json.loads(req.text)
            assert isinstance(json_response["balance"], float)


def test_check_balance_form(mock_wallet: PosixPath):
    """Testing the check_balance endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_check_balance_form.yaml"))
    ):
        with open(str(mock_wallet), "rb") as my_wallet:
            encoded_wallet = base64.b64encode(my_wallet.read())
            data = {
                "wallet": encoded_wallet.decode("utf-8"),
            }
            req = requests.post(
                url=f"{TESTING_BASE_URL}/check_balance_form/", data=data
            )
            json_response = json.loads(req.text)
            assert isinstance(json_response["balance"], float)


def test_check_last_transaction(mock_wallet: PosixPath):
    """Testing the check_last_transaction endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_check_last_transaction.yaml"))
    ):
        with open(str(mock_wallet), "rb") as my_file:
            files = {"file": (str(WALLET_NAME), my_file)}
            req = requests.post(
                url=f"{TESTING_BASE_URL}/check_last_transaction/", files=files
            )
            json_response = json.loads(req.text)
            assert json_response["last_transaction_id"] != "Failure to get response..."


def test_estimate_transaction_cost():
    """Testing the estimate_transaction_cost endpoint"""

    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_estimate_transaction_cost.yaml"))
    ):
        data = {"size_in_bytes": "10000000000"}
        req = requests.get(
            url=f"{TESTING_BASE_URL}/estimate_transaction_cost/", params=data
        )
        # self.assertNotEqual(req.text, None)
        json_response = json.loads(req.text)
        assert (
            json_response["estimate_transaction_cost"]
            != "Parameter issue. Please enter a valid amount of bytes as an integer."
        )


def test_check_transaction_status():
    """Testing the estimate_transaction_cost endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_check_transaction_status.yaml"))
    ):
        data = {"transaction_id": "cZiaojZtzyL1ZB7GjbWLbj62S_9pxPDHu61HQvSYgD0"}
        req = requests.get(
            url=f"{TESTING_BASE_URL}/check_transaction_status/", params=data
        )
        json_response = json.loads(req.text)
        assert (
            json_response["transaction_status"]
            != "Parameter issue. Please enter a valid transaction id."
        )
        for item in ("block_height", "block_indep_hash", "number_of_confirmations"):
            assert item in json_response["transaction_status"]


def test_fetch_upload():
    """Testing the fetch_upload route"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_fetch_upload.yaml"))
    ):
        data = {"transaction_id": "cZiaojZtzyL1ZB7GjbWLbj62S_9pxPDHu61HQvSYgD0"}
        req = requests.get(url=f"{TESTING_BASE_URL}/fetch_upload/", params=data)
        assert req.text is not None
        assert req.headers.get("content-type") == "application/x-tar"


def test_create_transaction(arkly_test_file: PosixPath, mock_wallet: PosixPath):
    """Testing out the create_transaction endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_create_transaction.yaml"))
    ):
        with open(str(mock_wallet), "rb") as my_wallet:
            with open(str(arkly_test_file), "rb") as sample_file:
                files = [
                    ("files", my_wallet),
                    ("files", sample_file),
                ]
                req = requests.post(
                    url=f"{TESTING_BASE_URL}/create_transaction/", files=files
                )
                assert req.text is not None
                for item in (
                    "transaction_id",
                    "transaction_link",
                    "transaction_status",
                    "wallet_balance",
                ):
                    assert item in req.text


def test_create_transaction_form(arkly_test_file: PosixPath, mock_wallet: PosixPath):
    """Testing out the create_transaction endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_create_transaction_form.yaml"))
    ):
        with open(str(mock_wallet), "rb") as my_wallet:
            with open(str(arkly_test_file), "rb") as sample_file:
                arweave_files = []
                encoded_file_1 = base64.b64encode(sample_file.read())
                encoded_wallet = base64.b64encode(my_wallet.read())
                arweave_files.append(
                    {
                        "FileName": "test_file_one.txt",
                        "Base64File": encoded_file_1.decode("utf-8"),
                    }
                )

                # Reset file_stream to zero to read again.
                sample_file.seek(0)
                encoded_file_2 = base64.b64encode(sample_file.read())
                arweave_files.append(
                    {
                        "FileName": "test_file_two.txt",
                        "Base64File": encoded_file_2.decode("utf-8"),
                    }
                )
                data = {
                    "ArweaveKey": encoded_wallet.decode("utf-8"),
                    "ArweaveFiles": arweave_files,
                }
                req = requests.post(
                    url=f"{TESTING_BASE_URL}/create_transaction_form/",
                    json=data,
                )
                assert req.text is not None
                for item in (
                    "transaction_id",
                    "transaction_link",
                    "transaction_status",
                    "wallet_balance",
                ):
                    assert item in req.text


def test_validate_bag_valid_bag():
    """Ensure that validate arweave bag works as anticipated."""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_validate_arweave_bag_valid_bag.yaml"))
    ):
        data = {"transaction_id": "4vRsZM1JR491HJFPm_Nx08a7kp1_dJrc_sZC1X6afbg"}
        req = requests.get(url=f"{TESTING_BASE_URL}/validate_arweave_bag/", params=data)
        for item in ("transaction_url", "file_url", "valid", "bag_info"):
            assert item in req.text


def test_validate_bag_invalid_bag():
    """Ensure that validate arweave bag works as anticipated."""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_validate_arweave_bag_invalid_bag.yaml"))
    ):
        data = {"transaction_id": "8zItHEd6sUbK8fop6KquIu6jEyu49kLgiZ73O7xu2OE"}
        req = requests.get(url=f"{TESTING_BASE_URL}/validate_arweave_bag/", params=data)
        for item in ("transaction_url", "file_url", "valid"):
            assert item in req.text
        assert json.loads(req.text)["valid"] == "UNKNOWN"
