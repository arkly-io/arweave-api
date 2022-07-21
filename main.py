from typing import Union

from fastapi import FastAPI, File, UploadFile

import arweave


# wallet_file_path = "/some/folder/on/your/system"
# wallet = arweave.Wallet(wallet_file_path)

# balance =  wallet.balance

# last_transaction = wallet.get_last_transaction_id()


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile):
    return {"filename": file.filename}

@app.get("/balance")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
