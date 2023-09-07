"""Arweave API module.

This module is an Arweave FastAPI server that allows users to
communicate with Arweave, and put Arkly files on chain.
"""
from typing import Final, List

from fastapi import FastAPI, File, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

try:
    import primary_functions
    from middleware import _update_db
    from models import Tags
    from version import get_version
except ModuleNotFoundError:
    try:
        from src.arweave_api import primary_functions
        from src.arweave_api.middleware import _update_db
        from src.arweave_api.models import Tags
        from src.arweave_api.version import get_version
    except ModuleNotFoundError:
        from arweave_api import primary_functions
        from arweave_api.middleware import _update_db
        from arweave_api.models import Tags
        from arweave_api.version import get_version

# Arkly-arweave API description.
API_DESCRIPTION: Final[str] = " "

# OpenAPI tags delineating the documentation.
TAG_ARWEAVE: Final[str] = "arweave"
TAG_ARWEAVE_WALLET: Final[str] = "arweave wallet"
TAG_ARWEAVE_SEARCH: Final[str] = "arweave search"
TAG_ARKLY: Final[str] = "arkly"
TAG_MAINTAIN: Final[str] = "maintenance"

# Metadata for each of the tags in the OpenAPI specification. To order
# their display on the page, order the tags in this block.
tags_metadata = [
    {
        "name": TAG_ARWEAVE,
        "description": "Manage Arweave transactions",
    },
    {
        "name": TAG_ARWEAVE_WALLET,
        "description": "Manage Arweave wallets",
    },
    {
        "name": TAG_ARWEAVE_SEARCH,
        "description": "Search for Arweave transactions",
    },
    {
        "name": TAG_ARKLY,
        "description": "Arkly functions on-top of Arweave",
    },
]

app = FastAPI(
    title="api.arkly.io",
    description=API_DESCRIPTION,
    version=get_version(),
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


@app.post("/retrieve_wallet_address/", tags=[TAG_ARWEAVE_WALLET])
async def retrieve_wallet_address_from_keyfile(wallet: UploadFile):
    """Retrieve a wallet address from an Arweave wallet keyfile."""
    return await primary_functions._get_wallet_address(wallet)


@app.post("/check_wallet_balance/", tags=[TAG_ARWEAVE_WALLET])
async def check_wallet_balance_with_keyfile(wallet: UploadFile):
    """Allows a user to check the balance of their wallet."""
    return await primary_functions._check_balance_post(wallet)


@app.post("/check_wallet_last_transaction/", tags=[TAG_ARWEAVE_WALLET])
async def check_wallet_last_transaction_with_keyfile(wallet: UploadFile):
    """Allows a user to check the transaction ID of their last
    transaction.
    """
    return await primary_functions._check_last_transaction_post(wallet)


@app.get("/check_wallet_balance/", tags=[TAG_ARWEAVE_WALLET])
async def check_wallet_balance(wallet_address: str):
    """Allows a user to check the balance of a given wallet address.

    Balance is reported in Ar with a Winstons field also provided
    to the caller.

    Example wallet address: `6KymaAPWd3JNyMT0B7EPYij4TWxehhMrzRD8qifCSLs`
    """
    return await primary_functions._check_balance_get(wallet_address)


@app.get("/check_wallet_last_transaction/", tags=[TAG_ARWEAVE_WALLET])
async def check_wallet_last_transaction(wallet_address: str):
    """Allows a user to check the transaction ID of their last
    transaction.

    Example wallet address: `6KymaAPWd3JNyMT0B7EPYij4TWxehhMrzRD8qifCSLs`
    """
    return await primary_functions._check_last_transaction_get(wallet_address)


@app.get("/estimate_transaction_cost/", tags=[TAG_ARWEAVE])
async def estimate_transaction_cost(size_in_bytes: str):
    """Allows a user to get an estimate of how much a transaction may
    cost.
    """
    return await primary_functions._estimate_transaction_cost(size_in_bytes)


@app.get("/check_transaction_status/", tags=[TAG_ARWEAVE])
async def check_transaction_status(transaction_id: str):
    """Allows a user to check the transaction id of their last
    transaction.

    Example Tx: `rYa3ILXqWi_V52xPoG70y2EupPsTtu4MsMmz6DI4fy4`
    """
    return await primary_functions._check_transaction_status(transaction_id)


@app.get("/fetch_transaction/", tags=[TAG_ARWEAVE])
async def fetch_transaction(transaction_id: str):
    """Allows a user to read their transaction files from the Arweave
    blockchain.

    Example Tx: `rYa3ILXqWi_V52xPoG70y2EupPsTtu4MsMmz6DI4fy4`
    """
    return await primary_functions._fetch_upload(transaction_id)


@app.get("/fetch_transaction_metadata/", tags=[TAG_ARWEAVE])
async def fetch_transaction_metadata(transaction_id: str):
    """Fetch metadata from a given transaction ID to provide further
    information about the uploaded package.

    Example Tx: `rYa3ILXqWi_V52xPoG70y2EupPsTtu4MsMmz6DI4fy4`
    """
    return await primary_functions._fetch_tx_metadata(transaction_id)


@app.get("/all_wallet_transactions/", tags=[TAG_ARWEAVE_SEARCH])
async def get_all_wallet_transactions(wallet_addr: str):
    """Allows a user to see a list of all transactions with a given
    wallet.

    Example wallet: `6KymaAPWd3JNyMT0B7EPYij4TWxehhMrzRD8qifCSLs`
    """
    return await primary_functions._all_transactions(wallet_addr)


@app.get("/transactions_by_tag_pair/", tags=[TAG_ARWEAVE_SEARCH])
async def get_transactions_by_tag_pair(name: str, value: str):
    """Allows a user to retrieve transactions by tag-pair.

    Example tag key: `x-tag`
    Example tag value: `arkly hello world!`
    """
    return await primary_functions._retrieve_by_tag_pair(name, value)


@app.post("/create_transaction/", tags=[TAG_ARKLY])
async def create_transaction(
    wallet: UploadFile,
    package_file_name: str,
    files: List[UploadFile] = File(...),
    tags: Tags | None = None,
):
    """Create an Arkly package and Arweave transaction."""
    return await primary_functions._create_transaction(
        wallet, files, package_file_name, tags
    )


@app.get("/validate_arkly_bag/", tags=[TAG_ARKLY])
async def validate_bag(transaction_id: str, response: Response):
    """Given an Arweave transaction ID, Validate an Arkly link as a bag.

    Example Tx: `rYa3ILXqWi_V52xPoG70y2EupPsTtu4MsMmz6DI4fy4`
    """
    return await primary_functions._validate_bag(transaction_id, response)


@app.get("/get_version/", tags=[TAG_MAINTAIN])
async def get_version_info():
    """Return API version information to the caller."""
    return await primary_functions._get_version_info()
