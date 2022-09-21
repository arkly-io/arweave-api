"""Arkly Arweave primary function calls.

These function calls are wrapped by the Arweave FastAPI endpoint calls.
The FastAPI calls are used as entry points only to provide a place for
formatted documentation.
"""

import json
import sys
import tempfile
import urllib
from pathlib import Path

import arweave
import requests
from fastapi import HTTPException
from fastapi.responses import FileResponse


async def create_temp_wallet(file):
    """A function that created a wallet object to be used in various API calls

    :param file: JWK file, defaults to File(...)
    :type file: JSON
    :return: Wallet object
    :rtype: _type_
    """
    hold = await file.read()
    json_obj = json.loads(hold)
    wallet = arweave.Wallet.from_data(json_obj)
    if wallet is None:
        print("Wallet object not made. Try another wallet, or try again.")
        return "Error"
    return wallet


async def _check_balance(file):
    """Allows a user to check the balance of their wallet.

    :param file: JWK file, defaults to File(...)
    :type file: JSON
    :return: The balance of your wallet as a JSON object
    :rtype: JSON object
    """
    jwk_file = file
    wallet = await create_temp_wallet(jwk_file)
    if wallet != "Error":
        balance = wallet.balance
        return {"balance": balance}
    return {"balance": "Error on wallet load."}


async def _check_last_transaction(file):
    """Allows a user to check the transaction id of their last transaction

    :param file: JWK file, defaults to File(...)
    :type file: UploadFile, optional
    :return: The transaction id as a JSON object
    :rtype: JSON object
    """
    wallet = await create_temp_wallet(file)
    if wallet != "Error":
        last_transaction = requests.get(
            f"https://arweave.net/wallet/{wallet.address}/last_tx"
        )
        return {"last_transaction_id": last_transaction.text}
    return {"last_transaction_id": "Failure to get response..."}


async def _check_transaction_status(transaction_id: int):
    """Allows a user to check the transaction id of their last
    transaction.

    :param file: JWK file, defaults to File(...)
    :type file: UploadFile, optional
    :return: The transaction id as a JSON object
    :rtype: JSON object
    """
    if len(transaction_id) == 43:
        transaction_status = requests.get(
            f"https://arweave.net/tx/{transaction_id}/status"
        )
        return {"transaction_status": f"{transaction_status.text}"}
    return {
        "transaction_status": "Parameter issue. Please enter a valid transaction id."
    }


async def _estimate_transaction_cost(size_in_bytes: str):
    """Allows a user to get an estimate of how much a transaction may
    cost.

    :param size_in_bytes: A string which is an integer that represents
        the number of bytes to be uploaded.
    :type size_in_bytes: str
    :return: The estimated cost of the transaction
    :rtype: JSON object
    """
    if size_in_bytes.isdigit():
        cost_estimate = requests.get(f"https://arweave.net/price/{size_in_bytes}/")
        length = len(cost_estimate.text)
        if length > 12:
            past_twelve = length - 12
            winston_str = (
                f"{cost_estimate.text[0:past_twelve]}.{cost_estimate.text[-12:]}"
            )
        else:
            lessthan_twelve = 12 - length
            less_than_format = "0" * lessthan_twelve
            winston_str = f"0.{less_than_format}{cost_estimate.text}"
            print(winston_str)
        return {"estimate_transaction_cost": winston_str}
    return {
        "estimate_transaction_cost": "Parameter issue. Please enter a valid amount of bytes as an integer."
    }


async def _fetch_upload(transaction_id: str):
    """Allows a user to read their file upload from the Arweave
    blockchain.

    :param file: JWK file, defaults to File(...)
    :type file: UploadFile, optional
    :return: The compressed file upload
    :rtype: File Object
    """
    url = "http://arweave.net/" + transaction_id
    try:
        # Create a temporary directory for our fetch data. mkdtemp does
        # this in the most secure way possible.
        tmp_dir = tempfile.mkdtemp()
        fetch_dir = tmp_dir / Path(f"{transaction_id}.tar.gz")
        print(f"Fetch writing to {fetch_dir}", file=sys.stderr)
        with urllib.request.urlopen(url) as response, open(
            str(fetch_dir), "wb"
        ) as out_file:
            file_header = response.read()
            out_file.write(file_header)
            return FileResponse(str(fetch_dir))
    except urllib.request.HTTPError as err:
        raise HTTPException from err
