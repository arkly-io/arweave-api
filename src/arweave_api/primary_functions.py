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
from typing import Final, List, Tuple

import ar as arweave
import bagit
import humanize
import jose
import requests
from ar.transaction import Transaction
from ar.utils.transaction_uploader import get_uploader
from fastapi import File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse

try:
    import arweave_utilities
    from models import Tags
    from version import get_version
except ModuleNotFoundError:
    try:
        from src.arweave_api import arweave_utilities
        from src.arweave_api.models import Tags
        from src.arweave_api.version import get_version
    except ModuleNotFoundError:
        from arweave_api import arweave_utilities
        from arweave_api.models import Tags
        from arweave_api.version import get_version

logger = logging.getLogger(__name__)

# User agent string for Arkly.
ARKLY_AGENT = f"api.arkly.io/{get_version()}"

# NB. Legacy code, we need to replace with different error handling.
# Beginning by incrementally working through the issues.
ERR_WALLET: Final[str] = "error handling wallet"

# Error key.
ERR_KEY: Final[str] = "error"

# Length of a valid transaction ID.
TX_ID_LEN: Final[int] = 43

PACKAGING_AGENT_STRING = "Packaging-Agent"

REQ_TIMEOUT: Final[int] = 30


def _file_from_data(file_data):
    """Return a file-like BytesIO stream from Base64 encoded data."""
    data = base64.b64decode(file_data)
    return BytesIO(data)


async def create_temp_wallet(file: UploadFile) -> Tuple[arweave.Wallet, str]:
    """A function that created a wallet object to be used in various API
    calls.

    :param file: JWK file, defaults to File(...)
    :type file: JSON
    :return: Tuple[Wallet object, error str]
    :rtype: _type_
    """
    hold = await file.read()
    try:
        json_obj = json.loads(hold)
    except (json.JSONDecodeError, UnicodeDecodeError) as err:
        logger.error("wallet data is invalid, likely the wrong input format: %s", err)
        return None, f"{ERR_WALLET}: {err}"
    try:
        wallet_obj = arweave.Wallet.from_data(json_obj)
        return wallet_obj, None
    except (
        ValueError,
        TypeError,
        jose.exceptions.JWKError,
    ) as err:
        logger.error("error in Arweave Client API module: %s", err)
        return None, f"{ERR_WALLET}: {err}"


async def _get_wallet_address(wallet: UploadFile) -> dict:
    """Allows a user to retrieve a wallet address from a given Arweave
    key file.
    """
    wallet_obj, err = await create_temp_wallet(wallet)
    if err is not None:
        return {ERR_KEY: err}
    return {"wallet_address": wallet_obj.address}


async def _check_balance_post(wallet: UploadFile) -> dict:
    """Allows a user to check the balance of their wallet."""
    wallet_obj, err = await create_temp_wallet(wallet)
    if err is not None:
        return {ERR_KEY: err}
    arweave_ar = wallet_obj.balance
    winstons = arweave_utilities.ar_to_winston(arweave_ar)
    return {
        "wallet_address": wallet_obj.address,
        "ar": arweave_ar,
        "winstons": winstons,
    }


async def _check_last_transaction_post(wallet: UploadFile) -> dict:
    """Allows a user to check the transaction id of their last
    transaction.
    """
    gateway = arweave_utilities.retrieve_gateway()
    wallet_obj, err = await create_temp_wallet(wallet)
    if err is not None:
        return {ERR_KEY: err}
    last_transaction = requests.get(
        f"{gateway}/wallet/{wallet_obj.address}/last_tx",
        timeout=REQ_TIMEOUT,
    )
    return {
        "wallet_address": f"{wallet_obj.address}",
        "last_transaction_id": f"{gateway}/tx/{last_transaction.text}",
    }


async def _check_balance_get(wallet_address: str) -> dict:
    """Allows a user to check the balance of a given wallet address
    without loading a wallet into memory.
    """
    gateway = arweave_utilities.retrieve_gateway()
    balance_url = f"{gateway}/wallet/{wallet_address}/balance"
    logger.info("requesting balance at: %s", balance_url)
    resp = requests.get(
        balance_url,
        timeout=REQ_TIMEOUT,
    )
    if resp.status_code != 200:
        return {ERR_KEY: f"{resp.status_code} {resp.reason}"}
    winstons = int(resp.text)
    arweave_ar = arweave_utilities.winston_to_ar(resp.text)
    return {
        "wallet_address": wallet_address,
        "ar": arweave_ar,
        "winstons": winstons,
    }


async def _check_last_transaction_get(wallet_address: str) -> dict:
    """Allows a user to check the last transaction of a wallet without
    having to load a wallet into memory.
    """
    gateway = arweave_utilities.retrieve_gateway()
    tx_url = f"{gateway}/wallet/{wallet_address}/last_tx"
    logger.info("requesting last transaction at: %s", tx_url)
    last_transaction = requests.get(
        tx_url,
        timeout=REQ_TIMEOUT,
    )
    return {
        "wallet_address": f"{wallet_address}",
        "last_transaction_id": f"{gateway}/tx/{last_transaction.text}",
    }


async def _check_transaction_status(transaction_id: str) -> dict:
    """Allows a user to check the transaction id of their last
    transaction.

    :param file: JWK file, defaults to File(...)
    :type file: UploadFile, optional
    :return: The transaction id as a JSON object
    :rtype: JSON object
    """
    gateway = arweave_utilities.retrieve_gateway()
    transaction_status = requests.get(
        f"{gateway}/tx/{transaction_id}/status",
        timeout=REQ_TIMEOUT,
    )
    try:
        resp = json.loads(transaction_status.text)
        if ERR_KEY in resp.keys() and len(resp.keys()) == 1:
            return resp
        return resp
    except json.JSONDecodeError:
        return {
            ERR_KEY: f"{transaction_status.status_code} {transaction_status.reason}"
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
    gateway = arweave_utilities.retrieve_gateway()
    cost_estimate = requests.get(
        f"{gateway}/price/{size_in_bytes}/",
        timeout=REQ_TIMEOUT,
    )
    if cost_estimate.status_code != 200:
        try:
            return json.loads(cost_estimate.text)
        except json.JSONDecodeError:
            return {ERR_KEY: f"{cost_estimate.status_code} {cost_estimate.reason}"}
    winstons = arweave_utilities.winston_to_ar(cost_estimate.text)
    return {"estimated_transaction_cost": winstons}


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
    gateway = arweave_utilities.retrieve_gateway()
    request_url = f"{gateway}/tx/{transaction_id}"
    resp = requests.get(
        request_url,
        timeout=REQ_TIMEOUT,
    )
    data = {}
    try:
        data = json.loads(resp.text)
    except json.JSONDecodeError as err:
        return {ERR_KEY: f"{resp.status_code} {resp.reason} ({err})"}
    if ERR_KEY in data.keys() and len(data.keys()) == 1:
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
    data["reward_winston"] = int(data["reward"])
    data["reward_ar"] = arweave_utilities.winston_to_ar(data["reward"])
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
    gateway = arweave_utilities.retrieve_gateway()
    url = f"{gateway}/{transaction_id}"
    try:
        # Create a temporary directory for our fetch data. mkdtemp does
        # this in the most secure way possible.
        tmp_dir = tempfile.mkdtemp()
        fetch_dir = tmp_dir / Path(f"{transaction_id}.tar.gz")
        logger.info("Fetch writing to %s", fetch_dir)
        response = requests.get(
            url,
            timeout=REQ_TIMEOUT,
        )
        if response.status_code != 200:
            return {ERR_KEY: f"{response.status_code} {response.reason}"}
        with open(str(fetch_dir), "wb") as content:
            content.write(response.content)
        return FileResponse(str(fetch_dir))
    except requests.exceptions.ConnectionError as err:
        raise HTTPException from err


async def bag_files(path: Path, tag_list=None) -> None:
    """Use python Bagit to bag the files for Arkly-Arweave."""
    if not tag_list:
        bagit.make_bag(path, {PACKAGING_AGENT_STRING: ARKLY_AGENT})
        return
    bag_info = {}
    for tag in tag_list:
        bag_info[f"{tag.name}".replace(" ", "-")] = tag.value
    bag_info[PACKAGING_AGENT_STRING] = ARKLY_AGENT
    logger.info("writing package with bag-info: %s", bag_info)
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
    nopublish=False,
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
    wallet_obj, err = await create_temp_wallet(wallet)
    if err is not None:
        return {ERR_KEY: err}
    if wallet_obj.balance <= 0:
        return {ERR_KEY: f"wallet balance is: {wallet_obj.balance}"}
    if not files:
        return {ERR_KEY: "no files selected for upload"}

    tag_list = []
    try:
        # Process user-defined tags.
        tag_list = tags.tags
    except AttributeError:
        logger.info("no user-defined tags provided by caller")

    # Create a package from files array. Package content will create
    # this in a secure temporary directory.
    tar_file_name = await _package_content(files, package_file_name, tag_list)

    logger.info("adding version to package: %s", tar_file_name)
    logger.info("new path exists: %s", tar_file_name.is_file())
    logger.info("wallet balance before upload: %s", wallet_obj.balance)
    gateway = arweave_utilities.retrieve_gateway()
    with open(tar_file_name, "rb", buffering=0) as file_handler:
        new_transaction = Transaction(
            wallet_obj, file_handler=file_handler, file_path=tar_file_name
        )
        # Set the gateway to our custom endpoint.
        new_transaction.api_url = gateway
        # Default tags for the tar/gzip file that we create.
        new_transaction.add_tag("Content-Type", "application/gzip")
        for tag in tag_list:
            logger.info("Adding tag: %s: %s", tag.name, tag.value)
            new_transaction.add_tag(tag.name, tag.value)

        new_transaction.sign()
        uploader = get_uploader(new_transaction, file_handler)
        if nopublish:
            logger.info("not publishing to arkly")
            return {"transaction_idd": "NOPUBLISH env var is set"}
        while not uploader.is_complete:
            uploader.upload_chunk()

    logger.info("Finished uploading to Arkly!")
    tx_status = new_transaction.get_status()
    logger.info("Transaction status: %s", tx_status)
    logger.info("Transaction ID: %s", new_transaction.id)
    logger.info("New wallet balance: %s", wallet_obj.balance)
    gateway = arweave_utilities.retrieve_gateway()
    return {
        "transaction_id": f"{new_transaction.id}",
        "transaction_link": f"{gateway}/tx/{new_transaction.id}",
        "transaction_status": f"{tx_status}",
        "wallet_balance": f"{wallet_obj.balance}",
    }


def _get_arweave_urls_from_tx(transaction_id: str) -> dict:
    """Return a transaction URL and Arweave URL from a given Arweave
    transaction ID.
    """
    gateway = arweave_utilities.retrieve_gateway()
    return (
        f"{gateway}/tx/{transaction_id}",
        f"{gateway}/{transaction_id}",
    )


async def _validate_bag(transaction_id: str, response: Response) -> dict:
    """Given an Arweave transaction ID, Validate an Arkly link as a bag."""

    # Setup retrieval of the data from the given transaction.
    transaction_url, arweave_url = _get_arweave_urls_from_tx(transaction_id)
    arweave_response = requests.get(
        arweave_url,
        allow_redirects=True,
        timeout=REQ_TIMEOUT,
    )

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


async def _get_version_info() -> dict:
    """Return information about the versions used by this API."""
    return {"api": get_version(), "agent": ARKLY_AGENT, "bagit": bagit.VERSION}
