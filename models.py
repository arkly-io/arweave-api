"""FastAPI models used in the Arweave API."""
import json
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


class Tag(BaseModel):
    """Describes the structure of a single tag for upload to Arweave. A
    tag is simply a HTTP header and consists of a name and value.

    E.g. Name = `Content-type`, value = `application/gzip`
        becomes `"Content-type: application/gzip"`.
    """

    name: str
    value: str


# The Tags data type provides a way to provide an extensible list of
# data values, in this case, header tags for Airweave, where native
# HTTP handling makes this difficult as the form (from the FastAPI docs:
# is encoded as `application/x-www-form-urlencoded`.
#
# See also:
#
#  * https://github.com/tiangolo/fastapi/issues/2257#issuecomment-727036089
#  * https://stackoverflow.com/a/70640522/21120938
#  * https://docs.pydantic.dev/1.10/usage/types/#classes-with-__get_validators__
#
class Tags(BaseModel):
    """Tags is an extensible data-type that allows users to provide
    zero-to-many tags to supply to Airweave.

    To provide a value, provide a JSON object that looks something like
    as follows:

    ```json
    {
        "tags": [
            {
            "name": "tag_name_1",
            "value": "tag_value_1"
            },
            {
            "name": "tag_name_2",
            "value": "tag_value_2"
            },
            {
            "name": "tag_name_3",
            "value": "tag_value_3"
            }
        ]
    }
    ```

    """

    # Default values are provided to help users understand how to use
    # this data type.
    #
    # To create a Tag object you can do the following:
    #   Tag(**json.loads('{"name": "tag_name_1", "value": "tag_value_1"}')),
    #
    tags: list[Tag] = []

    @classmethod
    def __get_validators__(cls):
        # pylint: disable=C0202
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        """Parse the input parameters and return a Tags instance."""
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value
