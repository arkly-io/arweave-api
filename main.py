import os
import arweave
import json
from typing import Union, List
from fastapi import FastAPI, File, UploadFile

from arweave.arweave_lib import Wallet, Transaction
from arweave.transaction_uploader import get_uploader

from datetime import datetime
import tarfile
import os.path

from fastapi.middleware.cors import CORSMiddleware


# A function that created a wallet object to be used in various API calls
# Parameter(s): JWK file
# Returns: Wallet object
async def create_temp_wallet(file):
    try:
        hold = await file.read()
        jsonObj = json.loads(hold)
        wallet = arweave.Wallet.from_data(jsonObj)
        return wallet
    except:
        print("Wallet object not made. Try another wallet, or try again.")
        return "Error"


app = FastAPI()


origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root api call. Will be customized later...
@app.get("/")
def read_root():
    return {"Hello": "Welcome to the Arkly Arweave API!"}

# Allows a user to check the balance of their wallet
# Parameter(s): JWK file
# Returns: The balance as a JSON object
@app.post("/check_balance/")
async def check_balance(file: UploadFile = File(...)):
    JWKFile = file
    wallet = await create_temp_wallet(JWKFile)
    if (wallet!="Error"):
        balance = wallet.balance
        return {"balance": balance}
    else:
        return {"balance": "Error on wallet load."}

# Allows a user to check the transaction id of their last transaction
# Parameter(s): JWK file
# Returns: The transaction id as a JSON object
@app.post("/check_last_transaction/")
async def check_last_transaction(file: UploadFile = File(...)):
    wallet = await create_temp_wallet(file)
    if (wallet!="Error"):
        # print(wallet)
        last_transaction = wallet.get_last_transaction_id()
        return {"last_transaction_id": last_transaction}
    else:
        print(wallet)
        return {"last_transaction_id": "Failure to get response..."}


# Creates a folder for the wallet user to place
# Their uploads in. Compresses and packages uploaded files into .tar.bz2 files
# And uploads the compressed tarball to Arweave for a small fee.
# Fee will be known once the transaction has been applied on Arweave.
# Parameter(s): JWK file, Files to be uploaded
# Returns: The transaction id as a JSON object

# TO DO:
# transfer small fee from users wallet to an orgnization wallet to collect payment from API
# Delete user created files??? Maybe we want to store them for backup purposes... not sure.
@app.post("/create_transaction/")
async def create_transaction(files: List[UploadFile] = File(...)):
    for file in files:
        wallet = await create_temp_wallet(file)
        if (wallet!="Error"):
            files.remove(file)
            break
    if (wallet!="Error"):
        last_transaction = wallet.get_last_transaction_id()
        # wallet.address
        # Try to create a folder for their wallet
        # All file uploads for transactions will be held under the users
        # Profile.
        try:
            os.mkdir(wallet.address)
        except:
            pass

        dateTime = str(datetime.now())
        filePath = str(wallet.address) + "/" + dateTime
        os.mkdir(filePath)
        for file in files:
            readFile = await file.read()
            outputFile = open(filePath + "/" + file.filename, "wb")
            outputFile.write(readFile)
        
        # Create compressed .tar.bz2 file
        tarFileName = filePath + ".tar.bz2"
        with tarfile.open(tarFileName, 'w:bz2') as tar:
            tar.add(filePath, arcname=os.path.basename(filePath))
        
        print(wallet.balance)

        with open(tarFileName, "rb", buffering=0) as file_handler:
            tx = Transaction(wallet, file_handler=file_handler, file_path=tarFileName)
            tx.add_tag('Content-Type', 'application/x-bzip2 bz2')
            tx.sign()
            uploader = get_uploader(tx, file_handler)
            while not uploader.is_complete:
                uploader.upload_chunk()
            
        print("Finished!")
        status = tx.get_status()
        print(status)
        print(tx.id)
        print(wallet.balance)

       
        return {"transaction_id": tx.id}
    else:
        print(wallet)
        return {"transaction_id": "Error creating transaction."}


