from fastapi.testclient import TestClient
import pytest

from main import app, api_prefix

#client = TestClient(app)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
      yield c

@pytest.fixture(scope="module")
def test_user():
    return {"username": "maildump220@gmail.com", "password": "maildump220"}

def test_read_main(client):
    response = client.get("{}".format(api_prefix))
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

# Test Login/Token

def test_login(client, test_user):
  response = client.post("{}/login".format(api_prefix), data=test_user)
  assert response.status_code == 200
  print(response.json)
  token = response.json()["token"]
  user = response.json()["user"]
  message = response.json()["message"]
  assert user is not None
  assert message is not None
  assert token is not None

def test_token(client, test_user):
   response = client.post("{}/token".format(api_prefix), data=test_user)
   assert response.status_code == 200
   assert response.json()["access_token"] is not None
   assert response.json()["refresh_token"] is not None
   assert response.json()["token_type"] == 'bearer'

# Test Profile

# Test Registraion