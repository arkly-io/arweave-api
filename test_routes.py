"""A module to test API routes
"""
import requests

response = requests.get("http://127.0.0.1:8000/")

# response.content() # Return the raw bytes of the data payload
# response.text() # Return a string representation of the data payload
# response.json() # This method is convenient when the API returns JSON

# SMALL DISCOVERY MADE HERE
# For some reason (will be figured out later) the file must be closed after connection to the endpoint.
# If another request would like to be sent, then the file must be re-opened.

# Trying out check balance endpoint
with open("myWallet.json", "rb") as my_file:
    files = {"file": ("myWallet.json", my_file)}
    req = requests.post(url="http://127.0.0.1:8000/check_balance/", files=files)
    print("UPLOAD RESPONSE:")
    print(req.text)

# Testing out last transaction endpoint
with open("myWallet.json", "rb") as my_file:
    files = {"file": ("myWallet.json", my_file)}
    req = requests.post(
        url="http://127.0.0.1:8000/check_last_transaction/", files=files
    )
    print("UPLOAD RESPONSE:")
    print(req.text)

# Testing out file upload endpoint
# with open("myWallet.json", "rb") as my_wallet:
#     with open("files/text-sample-1.pdf", "rb") as sample_file:
#         files = [
#             ("files", my_wallet),
#             ("files", sample_file),
#         ]
#         req = requests.post(
#             url="http://127.0.0.1:8000/create_transaction/", files=files
#         )
#         print("UPLOAD RESPONSE:")
#         print(req.text)
