"""
This module is an Arweave FastAPI that allows users to communicate to Arweave, and put files on chain.
"""
import json
import os
import os.path
import tarfile
from datetime import datetime
from typing import List

import arweave
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


async def package_content(wallet, files):
    """Package the files submitted to the create_transaction endpoint."""
    date_time = str(datetime.now())
    file_path = str(wallet.address) + "/" + date_time
    os.mkdir(file_path)
    for file in files:
        read_file = await file.read()
        output_file = open(file_path + "/" + file.filename, "wb")
        output_file.write(read_file)

    # Create compressed .tar.gz file
    tar_file_name = file_path + ".tar.gz"
    with tarfile.open(tar_file_name, "w:gz") as tar:
        tar.add(file_path, arcname=os.path.basename(file_path))

    return tar_file_name


# TO DO:
# transfer small fee from users wallet to an orgnization wallet to collect payment from API
# Delete user created files??? Maybe we want to store them for backup purposes... not sure.
@app.post("/create_transaction/")
async def create_transaction(files: List[UploadFile] = File(...)):
    """Creates a folder for the wallet user to place Their uploads in.
    Compresses and packages uploaded files into .tar.bz2 files and uploads the compressed tarball to Arweave for a small fee.
    Fee will be known once the transaction has been applied on Arweave.

    :param files: JWK file (Required) and files to be uploaded, defaults to File(...)
    :type files: List[UploadFile]
    :return: The transaction id as a JSON object
    :rtype: JSON object
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

        tar_file_name = await package_content(wallet, files)

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
        status = new_transaction.get_status()
        print(status)
        print(new_transaction.id)
        print(wallet.balance)

        return {"transaction_id": new_transaction.id}

    return {"transaction_id": "Error creating transaction."}
