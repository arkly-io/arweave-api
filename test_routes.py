import requests
response = requests.get("http://127.0.0.1:8000/")

# response.content() # Return the raw bytes of the data payload
# response.text() # Return a string representation of the data payload
# response.json() # This method is convenient when the API returns JSON

# SMALL DISCOVERY MADE HERE
# For some reason (will be figured out later) the file must be closed after connection to the endpoint.
# If another request would like to be sent, then the file must be re-opened.

myFile = open('myWallet.json', 'rb')
files = {'file':('myWallet.json', myFile)}
req = requests.post(url='http://127.0.0.1:8000/check_balance/', files=files)
print("UPLOAD RESPONSE:")
print(req.text)
myFile.close()

myFile = open('myWallet.json', 'rb')
files = {'file':('myWallet.json', myFile)}
req = requests.post(url='http://127.0.0.1:8000/last_transaction/', files=files)
print("UPLOAD RESPONSE:")
print(req.text)
myFile.close()


headers = {
    'accept': 'application/json',
    'Content-Type': 'multipart/form-data',
}

files = [('files', open('myWallet.json', 'rb')), ('files', open('files/text-sample-1.pdf', 'rb'))]
req = requests.post(url='http://127.0.0.1:8000/create_transaction/', files=files)
print("UPLOAD RESPONSE:")
print(req.text)

