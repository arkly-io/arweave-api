""" Arkly Arweave API Unit tests
To lint use:
tox -e linting
"""

import json
from pathlib import Path
from typing import Final

import requests
import vcr

# response = requests.get("http://127.0.0.1:8000/")

# Location to record VCR cassettes to replay API requests/responses.
VCR_FIXTURES_PATH: Final[Path] = Path("tests/fixtures/vcrpy/")

# Wallet name will need to exist when VCR cassettes are re-recorded.
WALLET_NAME: Final[Path] = Path("myWallet.json")


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


def test_check_balance():
    """Testing the check_balance endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_check_balance.yaml"))
    ):
        with open(str(WALLET_NAME), "rb") as my_file:
            files = {"file": (str(WALLET_NAME), my_file)}
            req = requests.post(url="https://api.arkly.io/check_balance/", files=files)
            # self.assertNotEqual(req.text, None)
            json_response = json.loads(req.text)
            if "balance" in json_response.keys():
                assert isinstance(json_response["balance"], float)
            # assert json_response == "balance" and assert
            else:
                assert False


def test_check_last_transaction():
    """Testing the check_last_transaction endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_check_last_transaction.yaml"))
    ):
        with open(str(WALLET_NAME), "rb") as my_file:
            files = {"file": (str(WALLET_NAME), my_file)}
            req = requests.post(
                url="https://api.arkly.io/check_last_transaction/", files=files
            )
            # self.assertNotEqual(req.text, None)
            json_response = json.loads(req.text)
            assert json_response["last_transaction_id"] != "Failure to get response..."


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


def test_create_transaction():
    """Testing out the create_transaction endpoint"""
    arweave_vcr = vcr.VCR(before_record_request=_scrub_wallet_data())
    with arweave_vcr.use_cassette(
        str(VCR_FIXTURES_PATH / Path("test_create_transaction.yaml"))
    ):
        with open(str(WALLET_NAME), "rb") as my_wallet:
            with open("files/text-sample-1.pdf", "rb") as sample_file:
                files = [
                    ("files", my_wallet),
                    ("files", sample_file),
                ]
                req = requests.post(
                    url="https://api.arkly.io/create_transaction/", files=files
                )
                # self.assertNotEqual(req.text, None)
                assert req.text is not None


# def unit_tests():
#     assert create_transaction() != None
#     assert fetch_upload() != None
#     assert check_last_transaction() != None
#     assert check_balance() != None

# if __name__ == "__main__":
#     unit_tests()