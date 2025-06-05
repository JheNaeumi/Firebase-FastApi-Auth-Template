


import base64
from datetime import datetime
from os import path
import os
import re



def root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resources():
    return path.join(root(), "resources")


def dir_path_profile():
    return path.join(resources(), "profileimages")


async def save_image(directory: str, file_name: str, file: any, is_base64: bool = False):
    if not path.exists(directory):
        os.makedirs(directory)
    file_path = path.join(directory, file_name)
    if is_base64:
        image_bytes = file.encode("ascii")
        string_bytes = base64.b64decode(image_bytes)
        image_result = open(file_path, 'wb')
        image_result.write(string_bytes)
        image_result.close()
    else:
        image_result = open(file_path, 'wb')
        image_result.write(file)
        image_result.close()

def serialize_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def validate_email(email):
    """
    Validates email address format.
    
    Args:
        email (str): Email address to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))

def validate_password(password):
    """
    Validates password according to security requirements.
    
    Args:
        password (str): Password to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if len(password) < 8:
        return False
    
    if not re.search(r"[A-Z]", password):
        return False
    
    if not re.search(r"[a-z]", password):
        return False
    
    if not re.search(r"\d", password):
        return False
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    
    return True