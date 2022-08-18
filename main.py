"""
This module is an Arweave FastAPI that allows users to communicate to Arweave, and put files on chain.
"""
import json
import os
import os.path
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Final, List

import arweave
import bagit
import ulid
from arweave.arweave_lib import Transaction
from arweave.transaction_uploader import get_uploader
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware


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


app = FastAPI()


# origins = [
#     "http://localhost",
#     "http://localhost:3000",
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root api call. Will be customized later...


@app.get("/")
def read_root():
    """Base API endpoint
    :return: A JSON Object
    :rtype: JSON Obj
    """
    return {"Hello": "Welcome to the Arkly Arweave API!"}


@app.post("/check_balance/")
async def check_balance(file: UploadFile = File(...)):
    """Allows a user to check the balance of their wallet
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


@app.post("/check_last_transaction/")
async def check_last_transaction(file: UploadFile = File(...)):
    """Allows a user to check the transaction id of their last transaction
    :param file: JWK file, defaults to File(...)
    :type file: UploadFile, optional
    :return: The transaction id as a JSON object
    :rtype: JSON object
    """
    wallet = await create_temp_wallet(file)
    if wallet != "Error":
        # print(wallet)
        last_transaction = wallet.get_last_transaction_id()
        return {"last_transaction_id": last_transaction}
    return {"last_transaction_id": "Failure to get response..."}


async def bag_files(path: Path) -> None:
    """Use python Bagit to bag the files for Arkly-Arweave."""
    bagit.make_bag(path, {"Random Data": "arkly.io"})


async def package_content(files):
    """Package the files submitted to the create_transaction endpoint."""
    # Create a folder for the user's wallet.
    tmp_dir = tempfile.mkdtemp()
    tmp_name = tmp_dir

    package_ulid = str(ulid.new())
    file_path = Path(tmp_name, package_ulid)
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


@app.post("/create_transaction/")
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

    for file in files:
        wallet = await create_temp_wallet(file)
        if wallet != "Error":
            files.remove(file)
            break
    if wallet != "Error":
        # wallet.address
        # Try to create a folder for their wallet
        # All file uploads for transactions will be held under the users
        # Profile.
        try:
            os.mkdir(wallet.address)
        except FileExistsError:
            pass

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
