import json
import urllib
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path="dev.env")
signing_key = os.getenv("SECRET_KEY")
algo = os.getenv("ALGO")

abs_path = os.path.dirname(os.path.realpath(__file__))
config_path = os.path.join(abs_path, "db_config.json")

if not os.path.exists(config_path):
    raise FileNotFoundError(f"Configuration file not found: {config_path}")

try:
    db_config = json.load(open(config_path))
except json.JSONDecodeError as e:
    raise ValueError(f"Invalid JSON in {config_path}: {e}")

default_config = db_config.get("default")
if not default_config:
    raise KeyError("'default' key not found in db_config.json")

default_db_connection = urllib.parse.quote_plus(default_config.get("connection", ""))
if not default_db_connection:
    raise ValueError("Database connection string not configured")

db_conn = f"mssql+aioodbc:///?odbc_connect={urllib.parse.quote_plus(default_db_connection)}"