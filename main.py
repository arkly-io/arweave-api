"""Arweave API module.

This module is an Arweave FastAPI server that allows users to
communicate with Arweave, and put Arkly files on chain.
"""
from typing import Final, List

from fastapi import FastAPI, File, Form, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from middleware import _update_db
from models import ArweaveTransaction
from primary_functions import (
    _check_balance,
    _check_balance_form,
    _check_last_transaction,
    _check_transaction_status,
    _create_transaction,
    _create_transaction_form,
    _estimate_transaction_cost,
    _fetch_upload,
    _validate_bag,
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
    {
        "name": TAG_ARKLY,
        "description": "Arkly functions on-top of Arweave",
    },
]

app = FastAPI(
    title="api.arkly.io",
    description=API_DESCRIPTION,
    version="2022.11.02.0001",
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


@app.post("/check_balance_form/", tags=[TAG_ARWEAVE])
async def check_balance_form(wallet: str = Form()):
    """Allows a user to check the balance of their wallet."""
    return await _check_balance_form(wallet)


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


@app.get("/fetch_upload/", tags=[TAG_ARWEAVE])
async def fetch_upload(transaction_id: str):
    """Allows a user to read their file upload from the Arweave
    blockchain.
    """
    return await _fetch_upload(transaction_id)


@app.post("/create_transaction/", tags=[TAG_ARKLY])
async def create_transaction(files: List[UploadFile] = File(...)):
    """Create an Arkly package and Arweave transaction."""
    return await _create_transaction(files)


@app.post("/create_transaction_form/", tags=[TAG_ARKLY])
async def create_transaction_form(transaction_json: ArweaveTransaction):
    """Create an Arkly package and Arweave transaction."""
    data_files = await _create_transaction_form(transaction_json)
    return await _create_transaction(data_files)


@app.get("/validate_arweave_bag/", tags=[TAG_ARKLY])
async def validate_bag(transaction_id: str, response: Response):
    """Given an Arweave transaction ID, Validate an Arkly link as a bag."""
    return await _validate_bag(transaction_id, response)
