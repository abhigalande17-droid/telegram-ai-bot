import requests
from bs4 import BeautifulSoup
# Define the URL to download the image from
url = "https://example.com/image.jpg"
# Send a GET request to the URL
response = requests.get(url)
# Check if the request was successful
if response.status_code == 200:
    # Parse the response body
    soup = BeautifulSoup(response.text, "html.parser"))
    # Check if the image was successfully downloaded
    if soup.find("img")):
        # Download the image from the URL
        response = requests.get(url)
        # Parse the response body
        soup = BeautifulSoup(response.text, "html.parser"))
        # Check if the image was successfully downloaded
        if soup.find("img")):
            # Download the image from the URL
            response = requests.get(url)
            # Parse the response body
            soup = BeautifulSoup(response.text, "html.parser"))
            # Check if the image was successfully downloaded
            if soup.find("img")):
                # Download the image from the URL
                response = requests.get(url)
                # Parse the response body
                soup = BeautifulSoup(response.text, "html.parser"))
                #