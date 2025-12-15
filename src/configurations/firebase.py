import json
import os
# from fastapi.security import HTTPBearer
from firebase_admin import credentials
import firebase_admin
import pyrebase

# import pathlib
# from dotenv import load_dotenv


# basedir = pathlib.Path(__file__).parents[1]
# load_dotenv( basedir / ".env")

# bearer_scheme = HTTPBearer(auto_error=False)

abs_path = os.path.dirname(os.path.realpath(__file__))

fb_admin_config_json = 'fb_admin_config.json'
fb_config_json = 'fb_config.json'


cred = credentials.Certificate(os.path.join(abs_path, fb_admin_config_json))
firebase = firebase_admin.initialize_app(cred)
pb = pyrebase.initialize_app(
    json.load(open(os.path.join(abs_path, fb_config_json))))
