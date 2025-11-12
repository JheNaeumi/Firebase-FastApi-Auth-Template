import json
import urllib
import os

#absolute path
abs_path = os.path.dirname(os.path.realpath(__file__))
db_config = json.load(open(os.path.join(abs_path, 'db_config.json')))

default_config = db_config['default']

default_db_connection = urllib.parse.quote_plus(default_config['connection'])

db_conn = "mssql+aioodbc:///?odbc_connect={PARAMS}".format(
    PARAMS=urllib.parse.quote_plus(default_db_connection))
print(default_db_connection)