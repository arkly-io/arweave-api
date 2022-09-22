""" Arkly Arweave API Unit tests
To lint use:
tox -e linting
"""

import base64
import json
from pathlib import Path
from typing import Final

import pytest
import requests
import vcr

# response = requests.get("http://127.0.0.1:8000/")

# Location to record VCR cassettes to replay API requests/responses.
VCR_FIXTURES_PATH: Final[Path] = Path("tests/fixtures/vcrpy/")

# Wallet name will need to exist when VCR cassettes are re-recorded.
WALLET_NAME: Final[Path] = Path("myWallet.json")


@pytest.fixture(name="mock_wallet")
def create_wallet(tmp_path):
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


@pytest.fixture(name="mock_test_data")
def create_mock_test_data(tmp_path):
    """Create mock test data for running this code remotely, i.e. on a
    continuous integration server where interaction with Arweave or
    vcrpy is neither wanted or desired.
    """
    file_name = tmp_path / "test_data.txt"
    file_name.write_text("sample-test-data")
    return file_name


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


def test_check_balance(mock_wallet):
    """Testing the check_balance endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_check_balance.yaml"))
    ):
        with open(str(mock_wallet), "rb") as my_file:
            files = {"file": (str(WALLET_NAME), my_file)}
            req = requests.post(url="https://api.arkly.io/check_balance/", files=files)
            # self.assertNotEqual(req.text, None)
            json_response = json.loads(req.text)
            if "balance" in json_response.keys():
                assert isinstance(json_response["balance"], float)
            # assert json_response == "balance" and assert
            else:
                assert False


def test_check_last_transaction(mock_wallet):
    """Testing the check_last_transaction endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_check_last_transaction.yaml"))
    ):
        with open(str(mock_wallet), "rb") as my_file:
            files = {"file": (str(WALLET_NAME), my_file)}
            req = requests.post(
                url="https://api.arkly.io/check_last_transaction/", files=files
            )
            # self.assertNotEqual(req.text, None)
            json_response = json.loads(req.text)
            assert json_response["last_transaction_id"] != "Failure to get response..."


def test_estimate_transaction_cost():
    """Testing the estimate_transaction_cost endpoint"""

    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_estimate_transaction_cost.yaml"))
    ):
        data = {"size_in_bytes": "10000000000"}
        req = requests.post(
            url="https://api.arkly.io/estimate_transaction_cost/", params=data
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
        req = requests.post(
            url="https://api.arkly.io/check_transaction_status/", params=data
        )
        # self.assertNotEqual(req.text, None)
        json_response = json.loads(req.text)
        assert (
            json_response["transaction_status"]
            != "Parameter issue. Please enter a valid transaction id."
        )


def test_fetch_upload():
    """Testing the fetch_upload route"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_fetch_upload.yaml"))
    ):
        data = {"transaction_id": "cZiaojZtzyL1ZB7GjbWLbj62S_9pxPDHu61HQvSYgD0"}
        req = requests.get(url="https://api.arkly.io/fetch_upload/", params=data)
        print(req.content)
        # self.assertNotEqual(req.content, None)
        assert req.text is not None


def test_create_transaction(mock_wallet, mock_test_data):
    """Testing out the create_transaction endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_create_transaction.yaml"))
    ):
        with open(str(mock_wallet), "rb") as my_wallet:
            with open(str(mock_test_data), "rb") as sample_file:
                files = [
                    ("files", my_wallet),
                    ("files", sample_file),
                ]
                req = requests.post(
                    url="https://api.arkly.io/create_transaction/", files=files
                )
                # self.assertNotEqual(req.text, None)
                assert req.text is not None


def test_create_transaction_form(mock_wallet, mock_test_data):
    """Testing out the create_transaction endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_create_transaction_form.yaml"))
    ):
        with open(mock_wallet, "rb") as my_wallet:
            with open(str(mock_test_data), "rb") as sample_file:
                # Using our mock file object we'll duplicate it when we
                # submit it to Arweave, and create a second file name so
                # that we simulate two objects being placed on-weave.
                file_data = base64.b64encode(sample_file.read())
                base64_list = [
                    base64.b64encode(my_wallet.read()),
                    file_data,
                    file_data,
                ]
                name_list = [
                    "text-sample-1.txt",
                    "text-sample-2.txt",
                ]
                data = {"base_64_list": base64_list, "filename_list": name_list}
                req = requests.post(
                    url="https://api.arkly.io/create_transaction_form/", data=data
                )
                assert req.text is not None


# def unit_tests():
#     assert create_transaction() != None
#     assert fetch_upload() != None
#     assert check_last_transaction() != None
#     assert check_balance() != None

# if __name__ == "__main__":
#     unit_tests()
