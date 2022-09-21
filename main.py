"""Arweave API module.

This module is an Arweave FastAPI server that allows users to
communicate with Arweave, and put Arkly files on chain.
"""
import base64
import os
import os.path
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Final, List

import bagit
import requests
from fastapi import FastAPI, File, Form, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from middleware import _update_db
from primary_functions import (
    _check_balance,
    _check_last_transaction,
    _check_transaction_status,
    _create_transaction,
    _estimate_transaction_cost,
    _fetch_upload,
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


@app.get("/check_transaction_status/", tags=[TAG_ARWEAVE])
async def check_transaction_status(transaction_id: str):
    """Allows a user to check the transaction id of their last
    transaction.
    """
    return await _check_transaction_status(transaction_id)


@app.get("/estimate_transaction_cost/", tags=[TAG_ARWEAVE])
async def estimate_transaction_cost(size_in_bytes: str):
    """Allows a user to get an estimate of how much a transaction may
    cost.
    """
    return _estimate_transaction_cost(size_in_bytes)


@app.get("/fetch_upload/")
async def fetch_upload(transaction_id: str):
    """Allows a user to read their file upload from the Arweave
    blockchain.
    """
    return await _fetch_upload(transaction_id)


@app.post("/create_transaction/", tags=[TAG_ARWEAVE])
async def create_transaction(files: List[UploadFile] = File(...)):
    """Create an Arkly package and Arweave transaction."""
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
