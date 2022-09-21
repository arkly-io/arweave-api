"""
This module is an Arweave FastAPI that allows users to communicate to Arweave, and put files on chain.
"""

import os
import os.path
import tarfile
import tempfile
from pathlib import Path
from typing import Final, List

import bagit
import requests
from fastapi import FastAPI, File, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

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
API_DESCRIPTION: Final[
    str
] = " "

# OpenAPI tags delineating the documentation.
TAG_ARWEAVE: Final[str] = "arweave"
TAG_ARKLY: Final[str] = "arkly"

# Metadata for each of the tags in the OpenAPI specification. To order
# their display on the page, order the tags in this block.
tags_metadata = [
    {
        "name": TAG_ARWEAVE,
        "description": "Manage Arweave transactions",
        "externalDocs": {
            "description": "Arkly-Arweave documentation",
            "url": "https://docs.arkly.io",
        },
    },
]

app = FastAPI(
    title="api.arkly.io",
    description=API_DESCRIPTION,
    version="2022.08.17.0001",
    contact={
        "url": "https://arkly.io",
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
    return await _estimate_transaction_cost(size_in_bytes)


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
