"""Arkly Arweave primary function calls.

These function calls are wrapped by the Arweave FastAPI endpoint calls.
The FastAPI calls are used as entry points only to provide a place for
formatted documentation.
"""

import json

import arweave
import requests

from arweave_utilities import winston_to_ar


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
        the number of bytes to be uploaded
    :type size_in_bytes: str
    :return: The estimated cost of the transaction
    :rtype: JSON object
    """
    if size_in_bytes.isdigit():
        cost_estimate = requests.get(f"https://arweave.net/price/{size_in_bytes}/")
        winston_str = winston_to_ar(cost_estimate)
        return {"estimate_transaction_cost": winston_str}
    return {
        "estimate_transaction_cost": "Parameter issue. Please enter a valid amount of bytes as an integer."
    }
