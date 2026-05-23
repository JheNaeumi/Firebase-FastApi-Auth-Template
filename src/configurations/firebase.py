import json
import os
from firebase_admin import credentials
import firebase_admin
import pyrebase

abs_path = os.path.dirname(os.path.realpath(__file__))

fb_admin_config_json = "fb_admin_config.json"
fb_config_json = "fb_config.json"

admin_config_path = os.path.join(abs_path, fb_admin_config_json)
client_config_path = os.path.join(abs_path, fb_config_json)

if not os.path.exists(admin_config_path):
    raise FileNotFoundError(f"Firebase admin config not found: {admin_config_path}")
if not os.path.exists(client_config_path):
    raise FileNotFoundError(f"Firebase client config not found: {client_config_path}")

cred = credentials.Certificate(admin_config_path)
firebase = firebase_admin.initialize_app(cred)
pb = pyrebase.initialize_app(json.load(open(client_config_path)))
