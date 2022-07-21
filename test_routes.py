import requests
response = requests.get("http://127.0.0.1:8000/")
print(response)

# response.content() # Return the raw bytes of the data payload
# response.text() # Return a string representation of the data payload
# response.json() # This method is convenient when the API returns JSON
print(response.text)


files = {'file':('MyProfilePic.jpeg', open('MyProfilePic.jpeg', 'rb'))}
req = requests.post(url='http://127.0.0.1:8000/uploadfile/', files=files)

print(req.text)