"""
Manage the images related to the questions. Images will be uploaded to Imgur and retrieve as embedded links within the text.
TODO:
    - Catch and and convert image from within xlsx (delegate to reader.py)
DONE- Build and compare image hash (prevent duplication)
DONE- Upload image to Imgur and retrieve corresponding link
    - Support embedding image into data/exam page
"""
import io, os
import json, pickle
import requests
import secrets 
import hashlib 
import base64

from imgurpython import ImgurClient 
from imgurpython.helpers.error import ImgurClientError 

import logging
logger = logging.getLogger(__name__)

from typing import Optional, Dict, List, Tuple, Any, Union, Callable

DEFAULT_CLIENT_ID = "1326a4fdc9087ea"
DEFAULT_CLIENT_SECRET = "cdad87e44a4ffdbe63341570973e4fced679eea9"
DEFAULT_CREDENTIAL_STORAGE = "test/credential.json"
DEFAULT_IMAGE_STORAGE = "test/image_storage.pkl"

# value will be populated by later action
DefaultClient = None
DefaultImageRegistry = None

# wrapper
def wrap_imgur_client_error(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except ImgurClientError as e:
        print("Received ImgurClientError: {}. Raise again.".format(e))
        raise e
### 
# Load data from disk section: could be loading credentials and image registry
###

def configure_credentials():
    client = ImgurClient(DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET)
    authorization_url = client.get_auth_url('pin')
    print("Go to {} and retrieve pin.".format(authorization_url))
    pin = input("Enter pin from link: ")
    credentials = client.authorize(pin, 'pin')
    client.set_user_auth(credentials['access_token'], credentials['refresh_token'])
    print("All credentials data received: {}".format(credentials))
    with io.open(DEFAULT_CREDENTIAL_STORAGE, "w", encoding="utf-8") as jf:
#        json.dump(jf, [DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET, credentials["access_token"], credentials["refresh_token"])
        full_data = dict(credentials)
        full_data["client_id"] = DEFAULT_CLIENT_ID
        full_data["client_secret"] = DEFAULT_CLIENT_SECRET
        json.dump(full_data, jf, indent=2)
    return client

def load_credentials():
    with io.open(DEFAULT_CREDENTIAL_STORAGE, "r", encoding="utf-8") as jf:
        credentials = json.load(jf)
    return ImgurClient(credentials["client_id"], credentials["client_secret"], credentials["access_token"], credentials['refresh_token'])

def configure_image_registry():
    return dict()

def load_image_registry():
    with io.open(DEFAULT_IMAGE_STORAGE, "rb") as isf:
        return pickle.load(isf)

def save_image_registry():
    with io.open(DEFAULT_IMAGE_STORAGE, "wb") as isf:
        return pickle.dump(DefaultImageRegistry, isf)

##
# Interaction section
##

def write_image_to_id(image: Union[str, bytes], id_string: str, extra_desc=None):
    # id should be an unique identifier
    # TODO this must check collision with all other images. A hash library is required for this
    config = {"album": None, "name": f"Image_{id_string}", "title": f"Image {id_string}", "description": f"Image {id_string}" + f" for problem {extra_desc}" if extra_desc else ""}
    # image will be converted to b64 
    # fml this doesnt work
#    with io.BytesIO() as buffer:
    temp_path = os.path.join("test", id_string + ".b64")
    with io.open(temp_path, "wb") as buffer:
        # write to this temporary buffer 
        if(isinstance(image, bytes)):
            buffer.write(image) # bytes are written directly
        else:
            b64 = base64.b64decode(image) # str-like are decoded
#    with io.open(temp_path, "rb") as buffer:
    image = DefaultClient.upload_from_path(temp_path, config=config, anon=False)
    # after writing; delete the temp file 
    os.remove(temp_path)
    # once image is uploaded; put inside the registry 
    DefaultImageRegistry[id_string] = image = {k: v for k, v in image.items() if k in ["link", "id", "deletehash"]}
    # save a copy 
    save_image_registry()
    return image

def check_and_write_image(image: Union[str, bytes]):
    if(DefaultClient is None):
        raise Exception("Image client is not available; action cannot be performed.")
    # hash the image, check if any collision happen in the registry 
    # image is enforced as bytes; str mode should not be used 
    if(not isinstance(image, bytes)):
        # convert it back to b64 format
        image = base64.b64decode(image)
    img_hash = hashlib.md5(image).hexdigest()
    if(img_hash in DefaultImageRegistry):
        # very very very likely a duplication.
        # TODO what to do if it's not? load image and check.
        # insane worry. try loading 2^1024 images and then we'll check collision 
        logger.info("Image existed, using registered at {}".format(img_hash))
        return DefaultImageRegistry[img_hash]
    else:
        logger.info("Image new, register with {}".format(img_hash))
        return write_image_to_id(image, img_hash)

# always reload the registry, regardless of command type 
if(os.path.isfile(DEFAULT_IMAGE_STORAGE)):
    DefaultImageRegistry = load_image_registry()
else:
    DefaultImageRegistry = configure_image_registry()

if __name__ == "__main__":
    # Setup; must be ran once to set the authorization properly
    if(False):
        # to test stuff without triggering other. set to False when satisfied
        print("Test mode")
        DefaultClient = load_credentials()
        print(dir(DefaultClient))
#        img_data = base64.b64encode(data)
#        print("Raw data:\n", data)
#        print("Hash:\n", hashlib.md5(data, usedforsecurity=False).hexdigest())
    elif(not os.path.isfile(DEFAULT_CREDENTIAL_STORAGE)):
        print("Registration mode - configure credentials, overriding whatever is available")
        DefaultClient = configure_credentials()
    else:
        print("Test mode: Use existing credential, upload T-80U image and print the links")
        DefaultClient = load_credentials()
        with io.open("test/sample_T-80U.jpeg", "rb") as tf:
            image_data = tf.read()
        image = check_and_write_image(image_data)
        #config = {"album": None, "name": "T-80U", "title": "T-80U (title)", "description": "Example T-80U image."}
        #print("Uploading...")
        #image = DefaultClient.upload_from_path("test/sample_T-80U.jpeg", config=config, anon=False)
        #print("Image uploaded at `{}`".format(image["link"]))
        #print("Kept image data: {}".format(image))
elif(os.path.isfile(DEFAULT_CREDENTIAL_STORAGE)):
    logger.info("Image in module mode - reuse set credentials and attempt access.")
    try:
        DefaultClient = load_credentials()
    except requests.exceptions.ConnectTimeout as e:
        logger.error("Image module not working (timeout). Import with images is disabled!")
        DefaultClient = None
else:
    raise FileNotFoundError("Must have `{}` available to load credentials in module mode.".format(DEFAULT_CREDENTIAL_STORAGE))

