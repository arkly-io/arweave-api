"""Arkly Arweave primary function calls.

These function calls are wrapped by the Arweave FastAPI endpoint calls.
The FastAPI calls are used as entry points only to provide a place for
formatted documentation.
"""

import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Final, List

import arweave
import bagit
import requests
import ulid
from arweave.arweave_lib import Transaction
from arweave.transaction_uploader import get_uploader
from fastapi import File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse

from arweave_utilities import winston_to_ar


async def create_temp_wallet(file):
    """A function that created a wallet object to be used in various API
    calls.

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
    """Allows a user to check the transaction id of their last
    transaction.

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
        response = requests.get(url)
        with open(str(fetch_dir), "wb") as content:
            content.write(response.content)
        return FileResponse(str(fetch_dir))
    except requests.exceptions.ConnectionError as err:
        raise HTTPException from err


async def bag_files(path: Path) -> None:
    """Use python Bagit to bag the files for Arkly-Arweave."""
    bagit.make_bag(path, {"Random Data": "arkly.io"})


async def _package_content(files):
    """Package the files submitted to the create_transaction endpoint."""
    # Create a folder for the user's wallet.
    tmp_dir = tempfile.mkdtemp()
    package_ulid = str(ulid.new())
    file_path = Path(tmp_dir, package_ulid)
    file_path.mkdir()

    print("Location to write object to:", file_path, file=sys.stderr)

    for file in files:
        read_file = await file.read()
        output_file = Path(file_path, file.filename)
        output_file.write_bytes(read_file)

    # Create a metadata path for the bag.
    metadata_path = file_path / Path(f".{package_ulid}")
    metadata_path.mkdir(parents=True)
    metadata = metadata_path / Path(package_ulid).with_suffix(".md")

    # Write some mock metadata for demo. Move this to a separate built
    # for purpose function later.
    metadata.write_text('{"dc:creator": "api.arkly.io"}')

    # Bag these files.
    await bag_files(file_path)

    # Create compressed .tar.gz file
    tar_file_name = file_path.with_suffix(".tar.gz")
    with tarfile.open(tar_file_name, "w:gz") as tar:
        tar.add(file_path, arcname=os.path.basename(file_path))

    version_api: Final[str] = "v0"
    tar_file_name = tar_file_name.rename(
        f"{tar_file_name}".replace(".tar.gz", f"_{version_api}.tar.gz")
    )
    return tar_file_name


async def _create_transaction(files: List[UploadFile] = File(...)):
    """Create an Arkly package and Arweave transaction.

    We do so as follows:
        - Create a folder for the wallet user to place their uploads in
          as well as any additional folders and metadata required.
        - Create a bagit file from that folder.
        - Compresses and packages uploaded files into .tar.gz files.
        - Uploads the compressed tarball to Arweave for the current
          Arweave price.
    """
    for file in files:
        wallet = await create_temp_wallet(file)
        if wallet != "Error":
            files.remove(file)
            break
    if wallet != "Error":

        # Create a package from files array. Package content will create
        # this in a secure temporary directory.
        tar_file_name = await _package_content(files)

        print("Adding version to package:", tar_file_name, file=sys.stderr)
        print("New path exists:", tar_file_name.is_file(), file=sys.stderr)
        print("Wallet balance before upload:", wallet.balance, file=sys.stderr)

        print(wallet.balance)

        with open(tar_file_name, "rb", buffering=0) as file_handler:
            new_transaction = Transaction(
                wallet, file_handler=file_handler, file_path=tar_file_name
            )
            new_transaction.add_tag("Content-Type", "application/gzip")
            new_transaction.sign()
            uploader = get_uploader(new_transaction, file_handler)
            while not uploader.is_complete:
                uploader.upload_chunk()

        print("Finished!")
        tx_status = new_transaction.get_status()
        print(tx_status, file=sys.stderr)
        print(new_transaction.id, file=sys.stderr)
        print(wallet.balance, file=sys.stderr)
        return {
            "transaction_id": f"{new_transaction.id}",
            "transaction_link": f"https://viewblock.io/arweave/tx/{new_transaction.id}",
            "transaction_status": f"{tx_status}",
            "wallet_balance": f"{wallet.balance}",
        }
    return {"transaction_id": "Error creating transaction."}


def _get_arweave_urls_from_tx(transaction_id):
    """Return a transaction URL and Arweave URL from a given Arweave
    transaction ID.
    """
    return (
        f"https://viewblock.io/arweave/tx/{transaction_id}",
        f"https://arweave.net/{transaction_id}",
    )


async def _validate_bag(transaction_id: str, response: Response):
    """Given an Arweave transaction ID, Validate an Arkly link as a bag."""

    # Setup retrieval of the data from the given transaction.
    transaction_url, arweave_url = _get_arweave_urls_from_tx(transaction_id)
    arweave_response = requests.get(arweave_url, allow_redirects=True)

    # Create temp file to extract the contents from Arweave to.
    tmp_file_handle, tmp_file_path = tempfile.mkstemp()
    with open(tmp_file_handle, "wb") as write_tar_gz:
        write_tar_gz.write(arweave_response.content)

    tmp_dir = tempfile.mkdtemp()
    try:
        arkly_gzip = tarfile.open(tmp_file_path)
        arkly_gzip.extractall(tmp_dir)
    except tarfile.ReadError:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return {
            "transaction_url": transaction_url,
            "file_url": arweave_url,
            "valid": "UNKNOWN",
        }

    try:
        bag_ulid = os.listdir(tmp_dir)[0]
        bag_file = Path(tmp_dir) / bag_ulid
    except IndexError:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            "transaction_url": transaction_url,
            "file_url": arweave_url,
            "valid": "UNKNOWN",
        }

    # Create bag object and validate, and return information from it.
    try:
        arkly_bag = bagit.Bag(str(bag_file))
        return {
            "transaction_url": transaction_url,
            "file_url": arweave_url,
            "valid": f"{arkly_bag.validate()}",
            "bag_info": arkly_bag.info,
            "bag_ulid": bag_ulid,
        }
    except bagit.BagError:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return {
            "transaction_url": transaction_url,
            "file_url": arweave_url,
            "valid": "UNKNOWN",
        }
