""" Arkly Arweave API Unit tests
To lint use:
tox -e linting
"""
import unittest

import requests

response = requests.get("http://127.0.0.1:8000/")


class TestArweaveApi(unittest.TestCase):
    """Various unit tests for the arweave API

    :param unittest: The unittest library used to create test cases
    :type unittest: _type_
    """

    def test_check_balance(self):
        """Testing the check_balance endpoint"""
        with open("myWallet.json", "rb") as my_file:
            files = {"file": ("myWallet.json", my_file)}
            req = requests.post(url="http://127.0.0.1:8000/check_balance/", files=files)
            self.assertNotEqual(req.text, None)

    def test_check_last_transaction(self):
        """Testing the check_last_transaction endpoint"""
        with open("myWallet.json", "rb") as my_file:
            files = {"file": ("myWallet.json", my_file)}
            req = requests.post(
                url="http://127.0.0.1:8000/check_last_transaction/", files=files
            )
            self.assertNotEqual(req.text, None)

    def test_fetch_upload(self):
        """Testing the fetch_upload route"""
        data = {"transaction_id": "cZiaojZtzyL1ZB7GjbWLbj62S_9pxPDHu61HQvSYgD0"}
        req = requests.get(url="http://127.0.0.1:8000/fetch_upload/", params=data)
        print(req.content)
        self.assertNotEqual(req.content, None)

    def test_create_transaction(self):
        """Testing out the create_transaction endpoint"""
        with open("myWallet.json", "rb") as my_wallet:
            with open("files/text-sample-1.pdf", "rb") as sample_file:
                files = [
                    ("files", my_wallet),
                    ("files", sample_file),
                ]
                req = requests.post(
                    url="http://127.0.0.1:8000/create_transaction/", files=files
                )
                self.assertNotEqual(req.text, None)


if __name__ == "__main__":
    unittest.main()
