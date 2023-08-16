"""Arkly Arweave primary function calls.

These function calls are wrapped by the Arweave FastAPI endpoint calls.
The FastAPI calls are used as entry points only to provide a place for
formatted documentation.

The current Arweave API client is found at:

    * https://github.com/MikeHibbert/arweave-python-client

The Arweave API client is particularly helpful for working with Arweave
when the Arweave wallet is required.

In some cases the Arweave API client is overridden with pure Arweave API
calls, especially "reading" where handling of wallets isn't required and
we can limit exposure of this information.
"""
import base64
import json
import logging
import os
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Final, List

import arweave
import bagit
import humanize
import requests
from arweave.arweave_lib import Transaction, arql
from arweave.transaction_uploader import get_uploader
from fastapi import File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse

try:
    from arweave_utilities import winston_to_ar
    from models import Tags
    from version import get_version
except ModuleNotFoundError:
    try:
        from src.arweave_api.arweave_utilities import winston_to_ar
        from src.arweave_api.models import Tags
        from src.arweave_api.version import get_version
    except ModuleNotFoundError:
        from arweave_api.arweave_utilities import winston_to_ar
        from arweave_api.models import Tags
        from arweave_api.version import get_version

logger = logging.getLogger(__name__)

ARWEAVE_API_BASEURL: Final[str] = "https://arweave.net"
ARWEAVE_VIEW_BASEURL: Final[str] = "https://arweave.app"

ARKLY_AGENT = "arkly.io"

# NB. Legacy code, we need to replace with different error handling.
# Beginning by incrementally working through the issues.
ERR_WALLET: Final[str] = "error handling wallet"


def _file_from_data(file_data):
    """Return a file-like BytesIO stream from Base64 encoded data."""
    data = base64.b64decode(file_data)
    return BytesIO(data)


async def create_temp_wallet(file: UploadFile) -> arweave.Wallet:
    """A function that created a wallet object to be used in various API
    calls.

    :param file: JWK file, defaults to File(...)
    :type file: JSON
    :return: Wallet object
    :rtype: _type_
    """
    hold = await file.read()
    try:
        json_obj = json.loads(hold)
    except UnicodeDecodeError as err:
        logger.error("wallet data is invalid, likely the wrong input format: %s", err)
        return ERR_WALLET
    try:
        wallet = arweave.Wallet.from_data(json_obj)
    except Exception as err:  # pylint: disable=W0718
        # There are a range of Exceptions we need to try to catch here
        # (I think), e.g. jose.exceptions.JWKError if the JSON is completely
        # invalid but we need to bottom these out. Eventually we do not want
        # to catch a bare-exception.
        logger.error("error in Arweave Client API module: %s", err)
    if wallet is None:
        logger.error("wallet object not made. Try another wallet, or try again.")
        return ERR_WALLET
    return wallet


async def _check_balance(wallet: UploadFile) -> dict:
    """Allows a user to check the balance of their wallet.

    :param file: JWK file, defaults to File(...)
    :type file: JSON
    :return: The balance of your wallet as a JSON object
    :rtype: JSON object
    """
    jwk_file = wallet
    wallet = await create_temp_wallet(jwk_file)
    if wallet != ERR_WALLET:
        balance = wallet.balance
        return {"balance": balance}
    return {"balance": "Error on wallet load."}


async def _check_last_transaction(wallet: UploadFile) -> dict:
    """Allows a user to check the transaction id of their last
    transaction.

    :param file: JWK file, defaults to File(...)
    :type file: UploadFile, optional
    :return: The transaction id as a JSON object
    :rtype: JSON object
    """
    wallet = await create_temp_wallet(wallet)
    if wallet != ERR_WALLET:
        last_transaction = requests.get(
            f"{ARWEAVE_API_BASEURL}/wallet/{wallet.address}/last_tx"
        )
        return {
            "wallet_address": f"{wallet.address}",
            "last_transaction_id": f"{ARWEAVE_VIEW_BASEURL}/tx/{last_transaction.text}",
        }
    return {"last_transaction_id": "Failure to get response..."}


async def _check_transaction_status(transaction_id: int) -> dict:
    """Allows a user to check the transaction id of their last
    transaction.

    :param file: JWK file, defaults to File(...)
    :type file: UploadFile, optional
    :return: The transaction id as a JSON object
    :rtype: JSON object
    """
    if len(transaction_id) == 43:
        transaction_status = requests.get(
            f"{ARWEAVE_API_BASEURL}/tx/{transaction_id}/status"
        )
        return {"transaction_status": json.loads(transaction_status.text)}
    return {
        "transaction_status": "Parameter issue. Please enter a valid transaction id."
    }


async def _estimate_transaction_cost(size_in_bytes: str) -> dict:
    """Allows a user to get an estimate of how much a transaction may
    cost.

        Example cURL for this request:

            `curl -s https://arweave.net/price/1000/ | jq`

    :param size_in_bytes: A string which is an integer that represents
        the number of bytes to be uploaded
    :type size_in_bytes: str
    :return: The estimated cost of the transaction
    :rtype: JSON object
    """
    if size_in_bytes.isdigit():
        cost_estimate = requests.get(f"{ARWEAVE_API_BASEURL}/price/{size_in_bytes}/")
        winston_str = winston_to_ar(cost_estimate.text)
        return {"estimate_transaction_cost": winston_str}
    return {
        "estimate_transaction_cost": "Parameter issue. Please enter a valid amount of bytes as an integer."
    }


def decode_base64_tag_fields(tags: list[str]) -> list[str]:
    """Decode the tag fields from Base64 and return them in plain-text."""
    new_tags = []
    for item in tags:
        new_item = {}
        # new_name and new_value can potentially error with incorrect
        # padding. We can fix this by adding the maximum amount of
        # padding '==' and Python will truncate any excess.
        #
        # https://stackoverflow.com/a/49459036/21120938
        #
        new_name = f"{item.get('name', '')}==".encode()
        new_value = f"{item.get('value', '')}==".encode()
        new_item["name"] = base64.b64decode(new_name)
        new_item["value"] = base64.b64decode(new_value)
        new_tags.append(new_item)
    return new_tags


async def _fetch_tx_metadata(transaction_id: str) -> dict:
    """Fetch tags for a transaction from Arweave given a transaction ID.

    The Arweave API client isn't used in this call as we don't want to
    ask the user to supply their Wallet in the API request. Fetching Tx
    details is purely a GET request.

    An example cURL request for the API call we mimic here is:

        * `curl -s https://arweave.net/tx/UQGNPIyhs2YFA569oSe-u-QPCn6q-w0IO9kGRnmq_Ak | jq`

    Details returned from the Tx metadata are:

        * "owner"
        * "id"
        * "tags"

    More information is available, described here: https://docs.arweave.org/developers/server/http-api#transaction-format

    For example:

        ```
            {
            "format": 2,
            "id": "BNttzDav3jHVnNiV7nYbQv-GY0HQ-4XXsdkE5K9ylHQ",
            "last_tx": "jUcuEDZQy2fC6T3fHnGfYsw0D0Zl4NfuaXfwBOLiQtA",
            "owner": "posmE...psEok",
            "tags": [],
            "target": "",
            "quantity": "0",
            "data_root": "PGh0b...RtbD4",
            "data": "",
            "data_size": "1234235",
            "reward": "124145681682",
            "signature": "HZRG_...jRGB-M"
            }
        ```

    As the structure needs pre-processing to decode Base64 fields we simply
    return a subset of this for ease of use. It can be expanded in future as
    required.
    """
    request_url = f"{ARWEAVE_API_BASEURL}/tx/{transaction_id}"
    resp = requests.get(request_url, timeout=30)
    data = {}
    try:
        data = json.loads(resp.text)
    except json.JSONDecodeError as err:
        data[
            "error"
        ] = f"problem retrieving metadata please check Tx ID or try again shortly: '{err}'"
        return data
    # Humanize data size output for Arkly's end-users.
    data["data_size_bytes"] = data["data_size"]
    data["data_size_natural_size"] = humanize.naturalsize(data["data_size"])
    data.pop("data_size")

    # Decode Base64 enncoded tags returned from Arweave and replace
    # in the return structure.
    decoded_tags = decode_base64_tag_fields(data["tags"])
    data["tags"] = decoded_tags

    # Humanize reward output for Arkly's end-users.
    data["reward_winston"] = data["reward"]
    data["reward_ar"] = winston_to_ar(data["reward"])
    data.pop("reward")
    return data


async def _fetch_upload(transaction_id: str) -> FileResponse:
    """Allows a user to read their file upload from the Arweave
    blockchain.

    :param file: JWK file, defaults to File(...)
    :type file: UploadFile, optional
    :return: The compressed file upload
    :rtype: File Object
    """
    url = f"{ARWEAVE_API_BASEURL}/{transaction_id}"
    try:
        # Create a temporary directory for our fetch data. mkdtemp does
        # this in the most secure way possible.
        tmp_dir = tempfile.mkdtemp()
        fetch_dir = tmp_dir / Path(f"{transaction_id}.tar.gz")
        logger.info("Fetch writing to %s", fetch_dir)
        response = requests.get(url)
        with open(str(fetch_dir), "wb") as content:
            content.write(response.content)
        return FileResponse(str(fetch_dir))
    except requests.exceptions.ConnectionError as err:
        raise HTTPException from err


async def bag_files(path: Path, tag_list=None) -> None:
    """Use python Bagit to bag the files for Arkly-Arweave."""
    if not tag_list:
        bagit.make_bag(path, {"packaging-agent": ARKLY_AGENT})
        return

    bag_info = {}
    for tag in tag_list:
        bag_info[f"{tag.name}".replace(" ", "-")] = tag.value
    bag_info["packaging-agent"] = ARKLY_AGENT
    logger.info("writing package with bag-info: %d", bag_info)
    bagit.make_bag(path, bag_info)
    return


async def _package_content(
    files: List[UploadFile] = File(...), package_name: str = None, tag_list: list = None
) -> dict:
    """Package the files submitted to the create_transaction endpoint."""
    # Create a folder for the user's wallet.
    tmp_dir = tempfile.mkdtemp()
    file_path = Path(tmp_dir, package_name)
    file_path.mkdir()

    logger.info("Location to write object to: %s", file_path)

    for file in files:
        read_file = await file.read()
        output_file = Path(file_path, file.filename)
        output_file.write_bytes(read_file)

    # Bag these files.
    await bag_files(file_path, tag_list)

    # Create compressed .tar.gz file
    tar_file_name = file_path.with_suffix(".tar.gz")
    with tarfile.open(tar_file_name, "w:gz") as tar:
        tar.add(file_path, arcname=os.path.basename(file_path))

    version_api: Final[str] = "v0"
    tar_file_name = tar_file_name.rename(
        f"{tar_file_name}".replace(".tar.gz", f"_{version_api}.tar.gz")
    )
    return tar_file_name


async def _create_transaction(
    wallet: UploadFile,
    files: List[UploadFile] = File(...),
    package_file_name: str = None,
    tags: Tags = None,
) -> dict:
    """Create an Arkly package and Arweave transaction.

    We do so as follows:
        - Create a folder for the wallet user to place their uploads in
          as well as any additional folders and metadata required.
        - Create a bagit file from that folder.
        - Compresses and packages uploaded files into .tar.gz files.
        - Uploads the compressed tarball to Arweave for the current
          Arweave price.
    """
    wallet = await create_temp_wallet(wallet)
    if wallet == ERR_WALLET:
        return {"transaction_id": "Error creating transaction."}
    if wallet.balance <= 0:
        return {"transaction_id": f"Error: wallet balance is: {wallet.balance}"}
    if not files:
        return {"transaction_id": "Error: no files selected for upload"}

    tag_list = []
    try:
        # Process user-defined tags.
        tag_list = tags.tags
    except AttributeError:
        logger.info("no user-defined tags provided by caller")

    # Create a package from files array. Package content will create
    # this in a secure temporary directory.
    tar_file_name = await _package_content(files, package_file_name, tag_list)

    logger.info("Adding version to package: %s", tar_file_name)
    logger.info("New path exists: %s", tar_file_name.is_file())
    logger.info("Wallet balance before upload: %s", wallet.balance)

    with open(tar_file_name, "rb", buffering=0) as file_handler:
        new_transaction = Transaction(
            wallet, file_handler=file_handler, file_path=tar_file_name
        )
        # Default tags for the tar/gzip file that we create.
        new_transaction.add_tag("Content-Type", "application/gzip")

        for tag in tag_list:
            logger.info("Adding tag: %s: %s", tag.name, tag.value)
            new_transaction.add_tag(tag.name, tag.value)

        new_transaction.sign()
        uploader = get_uploader(new_transaction, file_handler)
        while not uploader.is_complete:
            uploader.upload_chunk()

    logger.info("Finished uploading to Arkly!")
    tx_status = new_transaction.get_status()
    logger.info("Transaction status: %s", tx_status)
    logger.info("Transaction ID: %s", new_transaction.id)
    logger.info("New wallet balance: %s", wallet.balance)
    return {
        "transaction_id": f"{new_transaction.id}",
        "transaction_link": f"{ARWEAVE_VIEW_BASEURL}/tx/{new_transaction.id}",
        "transaction_status": f"{tx_status}",
        "wallet_balance": f"{wallet.balance}",
    }


def _get_arweave_urls_from_tx(transaction_id: str) -> dict:
    """Return a transaction URL and Arweave URL from a given Arweave
    transaction ID.
    """
    return (
        f"{ARWEAVE_VIEW_BASEURL}/tx/{transaction_id}",
        f"{ARWEAVE_API_BASEURL}/{transaction_id}",
    )


async def _validate_bag(transaction_id: str, response: Response) -> dict:
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
        bag_name = os.listdir(tmp_dir)[0]
        bag_file = Path(tmp_dir) / bag_name
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
            "bag_name": bag_name,
        }
    except bagit.BagError:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return {
            "transaction_url": transaction_url,
            "file_url": arweave_url,
            "valid": "UNKNOWN",
        }


async def _all_transactions(wallet_addr: str):
    """Retrieve all transactions from a given wallet and return a human
    friendly link to enable users to view the transaction.
    """
    query = {"op": "equals", "expr1": "from", "expr2": f"{wallet_addr}"}
    tx_ids = arql(None, query)
    if not tx_ids:
        return {
            "wallet_address": f"{wallet_addr}",
            "total_transactions": len(tx_ids),
            "arweave_transactions": tx_ids,
        }
    tx_uris = [f"{ARWEAVE_VIEW_BASEURL}/tx/{tx}" for tx in tx_ids]
    return {
        "wallet_address": f"{wallet_addr}",
        "total_transactions": len(tx_uris),
        "arweave_transactions": tx_uris,
    }


async def _retrieve_by_tag_pair(name: str, value: str) -> dict:
    """Retrieve all transactions with a given tag-pair."""
    query = {"op": "equals", "expr1": f"{name}", "expr2": f"{value}"}
    tx_ids = arql(None, query)
    if not tx_ids:
        return {
            "total_transactions": 0,
            "arweave_transactions": [],
        }
    tx_uris = [f"{ARWEAVE_VIEW_BASEURL}/tx/{tx}" for tx in tx_ids]
    return {
        "tag_pair": {"name": f"{name}", "value": f"{value}"},
        "arweave_transactions": tx_uris,
    }


async def _get_version_info() -> dict:
    """Return information about the versions used by this API."""
    return {"api": get_version(), "bagit": bagit.VERSION}
