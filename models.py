"""FastAPI models used in the Arweave API."""
from typing import List

from pydantic import BaseModel


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
