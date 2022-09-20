"""Arweave API module.

This module is an Arweave FastAPI server that allows users to
communicate with Arweave, and put Arkly files on chain.
"""
import base64
import os
import os.path
import sys
import tarfile
import tempfile
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Final, List

import bagit
import requests
import ulid
from arweave.arweave_lib import Transaction
from arweave.transaction_uploader import get_uploader
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from arweave_utilities import winston_to_ar
from middleware import _update_db
from primary_functions import (
    _check_balance,
    _check_last_transaction,
    create_temp_wallet,
)

# Arkly-arweave API description.
API_DESCRIPTION: Final[str] = " "

# OpenAPI tags delineating the documentation.
TAG_ARWEAVE: Final[str] = "arweave"
TAG_ARKLY: Final[str] = "arkly"

# Metadata for each of the tags in the OpenAPI specification. To order
# their display on the page, order the tags in this block.
tags_metadata = [
    {
        "name": TAG_ARWEAVE,
        "description": "Manage Arweave transactions",
    },
]

app = FastAPI(
    title="api.arkly.io",
    description=API_DESCRIPTION,
    version="2022.08.17.0001",
    contact={
        "": "",
    },
    openapi_tags=tags_metadata,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def update_db(request: Request, call_next):
    """Middleware used to identify which endpoint is being used so that
    the database can be updated effectively.
    """
    return await _update_db(request, call_next)


@app.get("/", include_in_schema=False)
def redirect_root_to_docs():
    """Redirect a user calling the API root '/' to the API
    documentation.
    """
    return RedirectResponse(url="/docs")


@app.post("/check_balance/", tags=[TAG_ARWEAVE])
async def check_balance(file: UploadFile = File(...)):
    """Allows a user to check the balance of their wallet."""
    return await _check_balance(file)


@app.post("/check_last_transaction/", tags=[TAG_ARWEAVE])
async def check_last_transaction(file: UploadFile = File(...)):
    """Allows a user to check the transaction id of their last
    transaction.
    """
    return await _check_last_transaction(file)


@app.post("/check_transaction_status/", tags=[TAG_ARWEAVE])
async def check_transaction_status(transaction_id: str):
    """Allows a user to check the transaction id of their last transaction
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


@app.post("/estimate_transaction_cost/", tags=[TAG_ARWEAVE])
async def estimate_transaction_cost(size_in_bytes: str):
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


@app.get("/fetch_upload/")
def fetch_upload(transaction_id: str):
    """Allows a user to read their file upload from the Arweave blockchain
    :param file: JWK file, defaults to File(...)
    :type file: UploadFile, optional
    :return: The compressed file upload
    :rtype: File Object
    """
    url = "http://arweave.net/" + transaction_id
    try:

        # Create a temporary directory for our fetch data. Mkdtemp does this in
        # the most secure way possible.
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
        # raise HTTPException(
        #     status_code=404,
        #     detail=(
        #         "Failed to get file. "
        #         + err.reason
        #         + " Insure transaction id is valid, and try again."
        #     ),
        # )


async def bag_files(path: Path) -> None:
    """Use python Bagit to bag the files for Arkly-Arweave."""
    bagit.make_bag(path, {"Random Data": "arkly.io"})


async def package_content(files):
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
    """Creates a transaction on Arweave given the list of file objects."""
    for file in files:
        wallet = await create_temp_wallet(file)
        if wallet != "Error":
            files.remove(file)
            break
    if wallet != "Error":

        # Create a package from files array. Package content will create
        # this in a secure temporary directory.
        tar_file_name = await package_content(files)

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


@app.post("/create_transaction/", tags=[TAG_ARWEAVE])
async def create_transaction(files: List[UploadFile] = File(...)):
    """Create an Arkly package and Arweave transaction.

    We do so as follows:
        - Create a folder for the wallet user to place their uploads in
          as well as any additional folders and metadata required.
        - Create a bagit file from that folder.
        - Compresses and packages uploaded files into .tar.gz files.
        - Uploads the compressed tarball to Arweave for the current
          Arweave price.
    """
    return await _create_transaction(files)


def _get_arweave_urls_from_tx(transaction_id):
    """Return a transaction URL and Arweave URL from a given Arweave
    transaction ID.
    """
    return (
        f"https://viewblock.io/arweave/tx/{transaction_id}",
        f"https://arweave.net/{transaction_id}",
    )


@app.get("/validate_arweave_bag/", tags=[TAG_ARKLY])
async def validate_bag(transaction_id: str, response: Response):
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
        with tarfile.open(tmp_file_path) as arkly_gzip:
            arkly_gzip.extractall(tmp_dir)
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
    except tarfile.ReadError:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return {
            "transaction_url": transaction_url,
            "file_url": arweave_url,
            "valid": "UNKNOWN",
        }


def file_from_data(file_data):
    """Return a file-like BytesIO stream from Base64 encoded data."""
    data = base64.b64decode(file_data)
    return BytesIO(data)


@app.post("/check_balance_form/", tags=[TAG_ARWEAVE])
async def check_balance_form(wallet: str = Form()):
    """Allows a user to check the balance of their wallet."""
    bytes_wallet = file_from_data(wallet)
    uploaded_wallet = UploadFile(filename="", file=bytes_wallet, content_type="")
    return await _check_balance(uploaded_wallet)


class FileItem(BaseModel):
    """Structure to hold information about a file to be uploaded to
    Arweave.
    """

    FileName: str
    Base64File: str
    ContentType: str | None = "application/octet-stream"


class ArweaveTransaction(BaseModel):
    """Pedantic BaseModel class used to accept json input to make
    transactions.
    """

    ArweaveKey: str
    ArweaveFiles: List[FileItem]


# wallet: str = Form(), data: List[str] = Form(...)
@app.post("/create_transaction_form/", tags=[TAG_ARWEAVE])
async def create_transaction_form(transaction_json: ArweaveTransaction):
    """Create an Arkly package and Arweave transaction."""
    arweave_file_item_list = transaction_json.ArweaveFiles
    bytes_wallet = file_from_data(transaction_json.ArweaveKey)
    data_files = [
        UploadFile(filename="wallet.json", file=bytes_wallet, content_type="text/json"),
    ]
    # Iterate through FileItem objects
    for file_item in arweave_file_item_list:
        print(file_item)
        print(type(file_item))
        bytes_packet = file_from_data(file_item.Base64File)
        upload_obj = UploadFile(
            filename=file_item.FileName, file=bytes_packet, content_type="text/plain"
        )
        data_files.append(upload_obj)
    return await _create_transaction(data_files)
